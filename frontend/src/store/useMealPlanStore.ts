import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { streamMealPlan } from '../utils/api'
import type { MealDish, ShoppingGroup } from '../utils/api'

// 一次配餐的完整记录（持久化到 localStorage，关闭/刷新都不丢）
export interface MealPlanRecord {
  id: string
  request: string
  nutrition_brief: string
  menu: MealDish[]
  retrieved: string[]
  shopping_list: ShoppingGroup[]
  createdAt: number
}

// 当前正在查看/运行的规划视图（不持久化：刷新后由历史恢复，运行态不可能跨刷新存活）
export interface MealPlanView {
  request: string
  status: 'running' | 'done' | 'error'
  cached: boolean
  nutrition_brief: string
  menu: MealDish[]
  retrieved: string[]
  shopping_list: ShoppingGroup[]
  error: string | null
  recordId: string | null // 完成后对应的历史记录 id
}

const MAX_HISTORY = 30

// 进行中请求的 AbortController 放模块级：规划生命周期与组件挂载彻底解耦，
// 这样关闭 Modal 不会打断后台规划，跑完照样写进历史。
let activeController: AbortController | null = null

function uuid(): string {
  return crypto.randomUUID()
}

interface MealPlanState {
  history: MealPlanRecord[]
  current: MealPlanView | null
  startRun: (request: string) => Promise<void> // 后台流式规划，完成自动入历史
  cancelRun: () => void                         // 显式取消进行中的规划
  clearCurrent: () => void                      // 新建：清空视图（不打断后台已在跑的）
  showRecord: (id: string) => void              // 从历史载入一条到视图
  deleteRecord: (id: string) => void
  clearHistory: () => void
}

export const useMealPlanStore = create<MealPlanState>()(
  persist(
    (set, get) => ({
      history: [],
      current: null,

      startRun: async (request) => {
        const req = request.trim()
        if (!req) return

        // 同一时刻只跑一个：开新的就取消上一个仍在跑的
        activeController?.abort()
        const controller = new AbortController()
        activeController = controller

        set({
          current: {
            request: req,
            status: 'running',
            cached: false,
            nutrition_brief: '',
            menu: [],
            retrieved: [],
            shopping_list: [],
            error: null,
            recordId: null,
          },
        })

        // 只更新仍指向本次运行的 current（避免被新一轮覆盖）
        const patch = (p: Partial<MealPlanView>) =>
          set((s) => (s.current && s.current.request === req && s.current.status === 'running'
            ? { current: { ...s.current, ...p } }
            : {}))

        try {
          for await (const ev of streamMealPlan(req, controller.signal)) {
            if (ev.type === 'cached') patch({ cached: true })
            else if (ev.type === 'nutrition') patch({ nutrition_brief: (ev.content as string) || '' })
            else if (ev.type === 'menu') patch({ menu: (ev.content as MealDish[]) || [], retrieved: ev.retrieved || [] })
            else if (ev.type === 'shopping') patch({ shopping_list: (ev.content as ShoppingGroup[]) || [] })
            else if (ev.type === 'done' && ev.result) {
              const id = uuid()
              const rec: MealPlanRecord = {
                id,
                request: ev.result.request,
                nutrition_brief: ev.result.nutrition_brief,
                menu: ev.result.menu,
                retrieved: ev.result.retrieved,
                shopping_list: ev.result.shopping_list,
                createdAt: Date.now(),
              }
              // 关键：历史无条件写入（即便此刻 Modal 已关、current 已被清空，也能在历史里找到）
              set((s) => ({
                history: [rec, ...s.history.filter((h) => h.request !== rec.request)].slice(0, MAX_HISTORY),
                current:
                  s.current && s.current.request === req
                    ? {
                        ...s.current,
                        status: 'done',
                        cached: ev.result!._cached,
                        recordId: id,
                        nutrition_brief: rec.nutrition_brief,
                        menu: rec.menu,
                        retrieved: rec.retrieved,
                        shopping_list: rec.shopping_list,
                      }
                    : s.current,
              }))
            }
          }
          // 流结束但没收到 done（极少）→ 收尾，避免一直转圈
          set((s) => (s.current && s.current.request === req && s.current.status === 'running'
            ? { current: { ...s.current, status: 'done' } }
            : {}))
        } catch (e) {
          if (e instanceof DOMException && e.name === 'AbortError') {
            // 被取消：清掉仍在 running 的视图（done 的不动）
            set((s) => (s.current && s.current.request === req && s.current.status === 'running'
              ? { current: null }
              : {}))
          } else {
            const msg = e instanceof Error ? e.message : '规划失败'
            set((s) => (s.current && s.current.request === req
              ? { current: { ...s.current, status: 'error', error: msg } }
              : {}))
          }
        } finally {
          if (activeController === controller) activeController = null
        }
      },

      cancelRun: () => {
        activeController?.abort()
        activeController = null
        set((s) => (s.current && s.current.status === 'running' ? { current: null } : {}))
      },

      // 新建：仅清空视图。若有后台规划在跑，不打断它（它跑完仍会进历史）
      clearCurrent: () => set({ current: null }),

      showRecord: (id) => {
        const rec = get().history.find((h) => h.id === id)
        if (!rec) return
        set({
          current: {
            request: rec.request,
            status: 'done',
            cached: false,
            nutrition_brief: rec.nutrition_brief,
            menu: rec.menu,
            retrieved: rec.retrieved,
            shopping_list: rec.shopping_list,
            error: null,
            recordId: rec.id,
          },
        })
      },

      deleteRecord: (id) =>
        set((s) => ({
          history: s.history.filter((h) => h.id !== id),
          current: s.current?.recordId === id ? null : s.current,
        })),

      clearHistory: () => set({ history: [] }),
    }),
    {
      name: 'ai-chef-mealplan',
      // 只持久化历史；current（运行态/视图）不入 localStorage
      partialize: (s) => ({ history: s.history }),
    }
  )
)
