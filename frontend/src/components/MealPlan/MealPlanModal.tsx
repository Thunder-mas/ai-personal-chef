import { useEffect, useState } from 'react'
import { X, Copy, Check, Plus, Trash2 } from 'lucide-react'
import { useUIStore } from '../../store/useUIStore'
import { useMealPlanStore } from '../../store/useMealPlanStore'
import type { ShoppingGroup } from '../../utils/api'

type StageStatus = 'pending' | 'active' | 'done'

const SUGGESTIONS = [
  '增肌 · 高蛋白午餐',
  '减脂 · 清淡晚餐',
  '三高人群 · 一日三餐',
  '快手 · 家常下饭菜',
]

function shoppingToText(groups: ShoppingGroup[]): string {
  return groups
    .map(
      (g) =>
        `【${g.category}】\n` +
        g.items.map((i) => `  - ${i.name}${i.amount ? ' ' + i.amount : ''}`).join('\n')
    )
    .join('\n\n')
}

function truncate(s: string, n = 14): string {
  return s.length > n ? s.slice(0, n) + '…' : s
}

// 小圆圈 loading（不依赖图标库，规避图标导出差异）
function Spinner() {
  return (
    <span
      className="inline-block w-3.5 h-3.5 rounded-full border-2 animate-spin"
      style={{ borderColor: 'var(--border-color)', borderTopColor: 'var(--accent)' }}
    />
  )
}

function StageHeader({
  emoji,
  title,
  subtitle,
  status,
}: {
  emoji: string
  title: string
  subtitle: string
  status: StageStatus
}) {
  return (
    <div className="flex items-center gap-2.5">
      <span
        className="flex items-center justify-center w-8 h-8 rounded-full text-lg shrink-0"
        style={{
          backgroundColor: status === 'pending' ? 'var(--bg-secondary)' : 'var(--accent-alpha)',
          opacity: status === 'pending' ? 0.5 : 1,
        }}
      >
        {emoji}
      </span>
      <div className="min-w-0">
        <div className="text-sm font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
          {title}
          {status === 'active' && <Spinner />}
          {status === 'done' && <Check size={14} style={{ color: 'var(--accent)' }} />}
        </div>
        <div className="text-xs truncate" style={{ color: 'var(--text-secondary)' }}>
          {subtitle}
        </div>
      </div>
    </div>
  )
}

export function MealPlanModal() {
  const close = useUIStore((s) => s.setMealPlanOpen)
  const history = useMealPlanStore((s) => s.history)
  const current = useMealPlanStore((s) => s.current)
  const startRun = useMealPlanStore((s) => s.startRun)
  const cancelRun = useMealPlanStore((s) => s.cancelRun)
  const clearCurrent = useMealPlanStore((s) => s.clearCurrent)
  const showRecord = useMealPlanStore((s) => s.showRecord)
  const deleteRecord = useMealPlanStore((s) => s.deleteRecord)

  const [request, setRequest] = useState('')
  const [copied, setCopied] = useState(false)

  // 打开 Modal 时：有运行/结果就回到它；否则回到最近一次历史（手滑关闭、后台跑完都能找回）
  useEffect(() => {
    if (current) {
      setRequest(current.request)
    } else if (history.length > 0) {
      showRecord(history[0].id)
      setRequest(history[0].request)
    }
    // 仅挂载时执行一次
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const running = current?.status === 'running'
  const started = !!current

  const nutrition = current?.nutrition_brief ?? ''
  const nutritionDone = current?.nutritionDone ?? false
  const menu = current?.menu ?? []
  const retrieved = current?.retrieved ?? []
  const shopping = current?.shopping_list ?? []
  const cached = current?.cached ?? false
  const error = current?.status === 'error' ? current.error : null

  // 三个 Agent 的状态由 current 的产出推导。
  // 营养师用 nutritionDone（而非文本是否非空）区分"流式中/已完成"：
  // token 流式时文本已非空但未定稿，此时应继续转圈，定稿后才打勾。
  const nutritionStatus: StageStatus = nutritionDone ? 'done' : running ? 'active' : 'pending'
  const menuStatus: StageStatus = menu.length ? 'done' : running && nutritionDone ? 'active' : 'pending'
  const shoppingStatus: StageStatus = shopping.length ? 'done' : running && menu.length ? 'active' : 'pending'

  const run = () => {
    if (!request.trim() || running) return
    startRun(request) // 后台运行：之后关闭 Modal 也会继续，跑完进历史
  }

  const handleNew = () => {
    clearCurrent()
    setRequest('')
  }

  const handleShowRecord = (id: string, req: string) => {
    showRecord(id)
    setRequest(req)
  }

  // 关闭：不打断后台规划（这是“后台规划”的关键），只收起 Modal
  const handleClose = () => close(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shoppingToText(shopping))
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // 剪贴板不可用时静默失败
    }
  }

  const handleDeleteRecord = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    deleteRecord(id)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={handleClose}>
      <div
        className="w-full max-w-2xl max-h-[85vh] flex flex-col rounded-2xl overflow-hidden"
        style={{ backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-4 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border-color)' }}>
          <div>
            <h3 className="flex items-center gap-2 text-base font-bold" style={{ color: 'var(--text-primary)' }}>
              <span>✨</span> 智能配餐 · 多 Agent 协作
            </h3>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
              营养师 → 主厨 → 采购，三个 Agent 接力为你定制一餐
            </p>
          </div>
          <button
            onClick={handleClose}
            className="p-1 rounded-lg transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)' }}
            onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-secondary)' }}
            aria-label="关闭"
          >
            <X size={18} />
          </button>
        </div>

        {/* 输入区 */}
        <div className="px-5 py-3" style={{ borderBottom: '1px solid var(--border-color)' }}>
          <div className="flex gap-2">
            <input
              value={request}
              onChange={(e) => setRequest(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') run() }}
              placeholder="说说你的需求，如：帮我安排一顿增肌高蛋白午餐"
              className="flex-1 px-3 py-2 rounded-lg text-sm outline-none"
              style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)' }}
            />
            {running ? (
              <button
                onClick={cancelRun}
                className="px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap"
                style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--accent-red)', border: '1px solid var(--border-color)' }}
              >
                取消规划
              </button>
            ) : (
              <button
                onClick={run}
                disabled={!request.trim()}
                className="px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap"
                style={{
                  backgroundColor: !request.trim() ? 'var(--bg-secondary)' : 'var(--accent)',
                  color: !request.trim() ? 'var(--text-secondary)' : '#fff',
                  cursor: !request.trim() ? 'not-allowed' : 'pointer',
                }}
              >
                开始规划
              </button>
            )}
          </div>
          {running && (
            <p className="text-xs mt-2 flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
              <Spinner /> 规划中… 可直接关闭，完成后会自动出现在下方「历史」里
            </p>
          )}
          {!started && (
            <div className="flex flex-wrap gap-2 mt-2.5">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => setRequest(s)}
                  className="px-2.5 py-1 rounded-full text-xs transition-all"
                  style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }}
                >
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 历史栏（持久化，手滑关闭 / 后台跑完都能找回） */}
        {history.length > 0 && (
          <div className="px-5 py-2 flex items-center gap-2 overflow-x-auto" style={{ borderBottom: '1px solid var(--border-color)' }}>
            <span className="text-xs shrink-0" style={{ color: 'var(--text-secondary)' }}>历史</span>
            <button
              onClick={handleNew}
              className="flex items-center gap-1 px-2 py-1 rounded-full text-xs shrink-0 transition-all"
              style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)', border: '1px solid var(--border-color)' }}
              title="新建一份"
            >
              <Plus size={12} /> 新建
            </button>
            {history.map((h) => {
              const active = current?.recordId === h.id
              return (
                <div
                  key={h.id}
                  className="group flex items-center gap-1 pl-2.5 pr-1 py-1 rounded-full text-xs shrink-0 cursor-pointer transition-all"
                  style={{
                    backgroundColor: active ? 'var(--accent)' : 'var(--bg-secondary)',
                    color: active ? '#fff' : 'var(--text-secondary)',
                    border: `1px solid ${active ? 'var(--accent)' : 'var(--border-color)'}`,
                  }}
                  onClick={() => handleShowRecord(h.id, h.request)}
                  title={h.request}
                >
                  <span>{truncate(h.request)}</span>
                  <button
                    onClick={(e) => handleDeleteRecord(h.id, e)}
                    className="p-0.5 rounded-full opacity-50 hover:opacity-100"
                    style={{ color: active ? '#fff' : 'var(--text-secondary)' }}
                    aria-label="删除这条历史"
                  >
                    <Trash2 size={11} />
                  </button>
                </div>
              )
            })}
          </div>
        )}

        {/* 结果区 */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {!started && (
            <div className="text-center py-10">
              <div className="text-4xl mb-3">🧑‍⚕️ 👨‍🍳 🛒</div>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                输入需求或点上面的标签，让三个 Agent 帮你配餐
              </p>
              {history.length > 0 && (
                <p className="text-xs mt-1.5" style={{ color: 'var(--text-secondary)', opacity: 0.7 }}>
                  也可以点上方「历史」回看之前的规划
                </p>
              )}
            </div>
          )}

          {error && (
            <div className="px-3 py-2 rounded-lg text-sm" style={{ backgroundColor: 'var(--accent-alpha)', color: 'var(--accent-red)' }}>
              出错了：{error}
            </div>
          )}

          {started && (
            <>
              {cached && (
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs" style={{ backgroundColor: 'var(--accent-alpha)', color: 'var(--accent)' }}>
                  ⚡ 命中缓存，瞬时返回
                </div>
              )}

              {/* 营养师 */}
              <div className="rounded-xl p-3.5" style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                <StageHeader emoji="🧑‍⚕️" title="营养师" subtitle="定营养约束与忌口" status={nutritionStatus} />
                {nutrition && (
                  <pre className="mt-2.5 text-sm whitespace-pre-wrap font-sans leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                    {nutrition}
                  </pre>
                )}
              </div>

              {/* 主厨 */}
              <div className="rounded-xl p-3.5" style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                <StageHeader emoji="👨‍🍳" title="主厨" subtitle="参考本地菜谱设计菜单" status={menuStatus} />
                {menu.length > 0 && (
                  <div className="mt-2.5 space-y-2.5">
                    {menu.map((d, i) => (
                      <div key={i} className="rounded-lg p-2.5" style={{ backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}>
                        <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>🍽️ {d.name}</div>
                        {d.reason && (
                          <div className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{d.reason}</div>
                        )}
                        {d.ingredients && d.ingredients.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {d.ingredients.map((ing, j) => (
                              <span key={j} className="px-2 py-0.5 rounded-full text-xs" style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
                                {ing.name}{ing.amount ? ` · ${ing.amount}` : ''}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                    {retrieved.length > 0 && (
                      <div className="text-xs pt-0.5" style={{ color: 'var(--text-secondary)', opacity: 0.8 }}>
                        📚 参考本地菜谱：{retrieved.join('、')}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* 采购 */}
              <div className="rounded-xl p-3.5" style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
                <div className="flex items-center justify-between">
                  <StageHeader emoji="🛒" title="采购" subtitle="去重合并 + 分类购物清单" status={shoppingStatus} />
                  {shopping.length > 0 && (
                    <button
                      onClick={handleCopy}
                      className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-all shrink-0"
                      style={{ backgroundColor: 'var(--accent)', color: '#fff' }}
                    >
                      {copied ? <Check size={13} /> : <Copy size={13} />}
                      {copied ? '已复制' : '复制清单'}
                    </button>
                  )}
                </div>
                {shopping.length > 0 && (
                  <div className="mt-2.5 space-y-2.5">
                    {shopping.map((g, i) => (
                      <div key={i}>
                        <div className="text-xs font-semibold mb-1.5" style={{ color: 'var(--accent)' }}>{g.category}</div>
                        <div className="flex flex-wrap gap-1.5">
                          {g.items.map((it, j) => (
                            <span key={j} className="px-2 py-1 rounded-lg text-xs" style={{ backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)', border: '1px solid var(--border-color)' }}>
                              {it.name}{it.amount ? ` ${it.amount}` : ''}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
