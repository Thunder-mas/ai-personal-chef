import type { RecipeData } from '../types/chat'

export interface ShoppingItem {
  name: string
  amount: string        // 合并后的用量展示，如 "300g + 2个"
  emoji?: string
  fromRecipes: string[] // 哪些菜谱需要这个食材
}

// 把 "300g" / "2个" / "1.5 勺" 解析成 { num, unit }；纯文字（适量/少许）返回 null
function parseAmount(raw: string): { num: number; unit: string } | null {
  const m = raw.trim().match(/^([\d.]+)\s*(.*)$/)
  if (!m) return null
  const num = parseFloat(m[1])
  if (Number.isNaN(num)) return null
  return { num, unit: m[2].trim() }
}

function formatNum(n: number): string {
  return Number.isInteger(n) ? String(n) : String(Math.round(n * 100) / 100)
}

/**
 * 把多个菜谱的食材聚合成购物清单：
 * - 同名食材合并
 * - 同单位的用量相加（"2个" + "1个" → "3个"）
 * - 单位不同则并列（"300g" + "2个" → "300g + 2个"）
 * - 纯文字用量（适量/少许）去重保留
 */
export function mergeIngredients(recipes: RecipeData[]): ShoppingItem[] {
  interface Entry {
    name: string
    emoji?: string
    units: Map<string, number>
    textAmounts: Set<string>
    fromRecipes: Set<string>
  }
  const map = new Map<string, Entry>()

  for (const recipe of recipes) {
    for (const ing of recipe.ingredients || []) {
      if (!ing?.name) continue
      const key = ing.name.trim()
      if (!key) continue
      let entry = map.get(key)
      if (!entry) {
        entry = { name: key, emoji: ing.emoji, units: new Map(), textAmounts: new Set(), fromRecipes: new Set() }
        map.set(key, entry)
      }
      if (ing.emoji && !entry.emoji) entry.emoji = ing.emoji
      entry.fromRecipes.add(recipe.name)

      const amt = (ing.amount || '').trim()
      if (!amt) continue
      const parsed = parseAmount(amt)
      if (parsed) {
        entry.units.set(parsed.unit, (entry.units.get(parsed.unit) || 0) + parsed.num)
      } else {
        entry.textAmounts.add(amt)
      }
    }
  }

  const items: ShoppingItem[] = []
  for (const entry of map.values()) {
    const parts: string[] = []
    for (const [unit, num] of entry.units) {
      parts.push(unit ? `${formatNum(num)}${unit}` : formatNum(num))
    }
    for (const t of entry.textAmounts) parts.push(t)
    items.push({
      name: entry.name,
      amount: parts.join(' + '),
      emoji: entry.emoji,
      fromRecipes: Array.from(entry.fromRecipes),
    })
  }

  // 按名称排序，展示稳定
  items.sort((a, b) => a.name.localeCompare(b.name, 'zh'))
  return items
}

/** 把清单导出成纯文本（用于复制） */
export function shoppingListToText(items: ShoppingItem[]): string {
  const lines = ['🛒 购物清单', '']
  for (const item of items) {
    const prefix = item.emoji ? `${item.emoji} ` : ''
    lines.push(`- ${prefix}${item.name}${item.amount ? ` ${item.amount}` : ''}`)
  }
  return lines.join('\n')
}
