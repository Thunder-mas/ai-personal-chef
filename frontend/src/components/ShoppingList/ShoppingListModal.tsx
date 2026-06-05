import { useMemo, useState } from 'react'
import { ShoppingCart, X, Copy, Check } from 'lucide-react'
import { useChatStore } from '../../store/useChatStore'
import { useUIStore } from '../../store/useUIStore'
import { mergeIngredients, shoppingListToText } from '../../utils/shoppingList'
import type { RecipeData } from '../../types/chat'

// 同名去重，保留食材更全的那条
function dedupeByName(recipes: RecipeData[]): RecipeData[] {
  const byName = new Map<string, RecipeData>()
  for (const r of recipes) {
    const existing = byName.get(r.name)
    const existingLen = existing?.ingredients?.length || 0
    const len = r.ingredients?.length || 0
    if (!existing || existingLen < len) byName.set(r.name, r)
  }
  return Array.from(byName.values())
}

// 跨所有对话收集去重后的收藏菜谱
function collectFavorites(conversations: { favoriteRecipes?: RecipeData[] }[]): RecipeData[] {
  const all: RecipeData[] = []
  for (const c of conversations) {
    for (const r of c.favoriteRecipes || []) all.push(r)
  }
  return dedupeByName(all)
}

export function ShoppingListModal() {
  const conversations = useChatStore((s) => s.conversations)
  const source = useUIStore((s) => s.shoppingListSource)
  const close = useUIStore((s) => s.closeShoppingList)

  // 有外部数据源（周计划）就用它，否则用收藏
  const allRecipes = useMemo(
    () => (source && source.length ? dedupeByName(source) : collectFavorites(conversations)),
    [source, conversations]
  )

  const [selectedNames, setSelectedNames] = useState<Set<string>>(
    () => new Set(allRecipes.map((r) => r.name))
  )
  const [checkedItems, setCheckedItems] = useState<Set<string>>(() => new Set())
  const [copied, setCopied] = useState(false)

  const selectedRecipes = useMemo(
    () => allRecipes.filter((r) => selectedNames.has(r.name)),
    [allRecipes, selectedNames]
  )
  const items = useMemo(() => mergeIngredients(selectedRecipes), [selectedRecipes])

  const toggleRecipe = (name: string) => {
    setSelectedNames((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  const toggleItem = (name: string) => {
    setCheckedItems((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shoppingListToText(items))
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // 剪贴板不可用时静默失败
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={close}
    >
      <div
        className="w-full max-w-lg max-h-[80vh] flex flex-col rounded-2xl overflow-hidden"
        style={{ backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="px-5 py-4 flex items-center justify-between"
          style={{ borderBottom: '1px solid var(--border-color)' }}
        >
          <h3 className="flex items-center gap-2 text-base font-bold" style={{ color: 'var(--text-primary)' }}>
            <ShoppingCart size={18} style={{ color: 'var(--accent)' }} />
            购物清单
          </h3>
          <button
            onClick={close}
            className="p-1 rounded-lg transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)' }}
            onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-secondary)' }}
            aria-label="关闭"
          >
            <X size={18} />
          </button>
        </div>

        {allRecipes.length === 0 ? (
          <div className="px-5 py-12 text-center">
            <ShoppingCart size={36} className="mx-auto mb-3" style={{ color: 'var(--text-secondary)', opacity: 0.4 }} />
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>还没有收藏的菜谱</p>
            <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)', opacity: 0.6 }}>
              先在菜谱卡片上点"收藏菜谱"，再来生成购物清单
            </p>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto px-5 py-4">
            {/* 选择菜谱 */}
            <div className="mb-5">
              <div className="text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>
                选择菜谱（{selectedRecipes.length}/{allRecipes.length}）
              </div>
              <div className="flex flex-wrap gap-2">
                {allRecipes.map((r) => {
                  const active = selectedNames.has(r.name)
                  return (
                    <button
                      key={r.name}
                      onClick={() => toggleRecipe(r.name)}
                      className="px-3 py-1.5 rounded-full text-sm transition-all"
                      style={{
                        backgroundColor: active ? 'var(--accent)' : 'var(--bg-secondary)',
                        color: active ? '#fff' : 'var(--text-secondary)',
                        border: `1px solid ${active ? 'var(--accent)' : 'var(--border-color)'}`,
                      }}
                    >
                      🍳 {r.name}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* 采购清单 */}
            <div className="text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>
              采购清单（{items.length} 项）
            </div>
            {items.length === 0 ? (
              <p className="text-sm py-4" style={{ color: 'var(--text-secondary)' }}>
                选中的菜谱没有可聚合的食材
              </p>
            ) : (
              <div className="space-y-1">
                {items.map((item) => {
                  const checked = checkedItems.has(item.name)
                  return (
                    <button
                      key={item.name}
                      onClick={() => toggleItem(item.name)}
                      className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-left transition-colors"
                      style={{ backgroundColor: 'var(--bg-secondary)' }}
                    >
                      <span
                        className="flex-shrink-0 w-5 h-5 rounded flex items-center justify-center"
                        style={{
                          backgroundColor: checked ? 'var(--accent)' : 'transparent',
                          border: `1.5px solid ${checked ? 'var(--accent)' : 'var(--border-color)'}`,
                        }}
                      >
                        {checked && <Check size={13} color="#fff" />}
                      </span>
                      <span>{item.emoji || '•'}</span>
                      <span
                        style={{
                          color: 'var(--text-primary)',
                          textDecoration: checked ? 'line-through' : 'none',
                          opacity: checked ? 0.5 : 1,
                        }}
                      >
                        {item.name}
                      </span>
                      {item.amount && (
                        <span className="ml-auto" style={{ color: 'var(--text-secondary)', opacity: checked ? 0.5 : 1 }}>
                          {item.amount}
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        {allRecipes.length > 0 && items.length > 0 && (
          <div
            className="px-5 py-3 flex items-center justify-between"
            style={{ borderTop: '1px solid var(--border-color)' }}
          >
            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              已勾选 {checkedItems.size}/{items.length}
            </span>
            <button
              onClick={handleCopy}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all"
              style={{ backgroundColor: 'var(--accent)', color: '#fff' }}
            >
              {copied ? <Check size={15} /> : <Copy size={15} />}
              {copied ? '已复制' : '复制清单'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
