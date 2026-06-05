import { useMemo } from 'react'
import { CalendarDays, ShoppingCart } from 'lucide-react'
import type { MealPlan, RecipeData } from '../../types/chat'
import { useUIStore } from '../../store/useUIStore'

interface MealPlanCardProps {
  plan: MealPlan
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
            <div className="space-y-1.5">
              {(day.meals || []).map((meal, mi) => (
                <div key={mi} className="flex items-baseline gap-2 text-sm">
                  <span style={{ color: 'var(--text-primary)' }}>🍽 {meal.name}</span>
                  {meal.brief && (
                    <span className="truncate" style={{ color: 'var(--text-secondary)' }}>
                      — {meal.brief}
                    </span>
                  )}
                </div>
              ))}
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
