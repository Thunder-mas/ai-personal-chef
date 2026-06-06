import { useMemo } from 'react'
import { CalendarDays, ShoppingCart } from 'lucide-react'
import type { MealPlan, PlannedMeal, RecipeData } from '../../types/chat'
import { useUIStore } from '../../store/useUIStore'

const SLOTS_3 = ['早餐', '午餐', '晚餐']

// 餐次：优先用 slot；没给但正好三餐时，按顺序补早/午/晚，保证一定标明
function resolveSlot(meal: PlannedMeal, index: number, total: number): string | undefined {
  if (meal.slot) return meal.slot
  if (total === 3) return SLOTS_3[index]
  return undefined
}

interface MealPlanCardProps {
  plan: MealPlan
}

// 餐次 → 图标
function slotEmoji(slot: string): string {
  if (slot.includes('早')) return '🌅'
  if (slot.includes('午')) return '☀️'
  if (slot.includes('晚')) return '🌙'
  return '🍽'
}

// 把周计划里的每道菜转成 RecipeData，供购物清单聚合（只需 name + ingredients）
function planToRecipes(plan: MealPlan): RecipeData[] {
  const recipes: RecipeData[] = []
  for (const day of plan.days || []) {
    for (const meal of day.meals || []) {
      recipes.push({
        name: meal.name,
        description: meal.brief ?? '',
        difficulty: '简单',
        cookingTime: '',
        servings: 1,
        ingredients: meal.ingredients ?? [],
        steps: [],
      })
    }
  }
  return recipes
}

export function MealPlanCard({ plan }: MealPlanCardProps) {
  const openShoppingList = useUIStore((s) => s.openShoppingList)
  const planRecipes = useMemo(() => planToRecipes(plan), [plan])

  return (
    <div
      className="rounded-2xl border overflow-hidden my-4"
      style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
    >
      {/* 头部 */}
      <div className="px-5 pt-5 pb-3 flex items-center gap-2">
        <CalendarDays size={18} style={{ color: 'var(--accent)' }} />
        <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
          {plan.title || '本周食谱'}
        </h3>
      </div>

      {/* 按天列出 */}
      <div className="px-5 pb-2" style={{ borderTop: '1px solid var(--border-color)' }}>
        {(plan.days || []).map((day, di) => (
          <div
            key={di}
            className="py-3"
            style={{ borderBottom: di < plan.days.length - 1 ? '1px solid var(--border-color)' : 'none' }}
          >
            <div className="text-sm font-semibold mb-2" style={{ color: 'var(--accent)' }}>
              {day.day}
            </div>
            <div className="space-y-2">
              {(day.meals || []).map((meal, mi) => {
                const slot = resolveSlot(meal, mi, (day.meals || []).length)
                return (
                  <div key={mi} className="flex gap-2 text-sm">
                    <span
                      className="flex-shrink-0 w-14 text-center px-2 py-0.5 rounded text-xs font-medium self-start"
                      style={{ backgroundColor: 'var(--bg-primary)', color: 'var(--text-secondary)' }}
                    >
                      {slot ? `${slotEmoji(slot)} ${slot}` : '🍽'}
                    </span>
                    <div className="min-w-0">
                      <div style={{ color: 'var(--text-primary)' }}>{meal.name}</div>
                      {meal.brief && (
                        <div className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                          {meal.brief}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* 生成购物清单 */}
      <div className="px-5 py-3" style={{ borderTop: '1px solid var(--border-color)' }}>
        <button
          onClick={() => openShoppingList(planRecipes)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all"
          style={{ backgroundColor: 'var(--accent)', color: '#fff' }}
        >
          <ShoppingCart size={16} />
          生成购物清单
        </button>
      </div>
    </div>
  )
}
