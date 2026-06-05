import { Heart, Clock, Users, ChefHat } from 'lucide-react'
import type { RecipeData } from '../../types/chat'
import { useChatStore } from '../../store/useChatStore'

interface RecipeCardProps {
  recipe: RecipeData
}

export function RecipeCard({ recipe }: RecipeCardProps) {
  const conversations = useChatStore((s) => s.conversations)
  const currentConversationId = useChatStore((s) => s.currentConversationId)
  const toggleFavoriteRecipe = useChatStore((s) => s.toggleFavoriteRecipe)
  const currentConv = conversations.find(c => c.id === currentConversationId)
  const isFavorite = currentConv?.favoriteRecipes?.some((r) => r.name === recipe.name) ?? false

  const difficultyColor = {
    '简单': 'text-green-600 dark:text-green-400',
    '中等': 'text-yellow-600 dark:text-yellow-400',
    '复杂': 'text-red-600 dark:text-red-400'
  }

  const handleFavorite = () => {
    toggleFavoriteRecipe(recipe)
  }

  return (
    <div
      className="rounded-2xl border overflow-hidden my-4"
      style={{
        backgroundColor: 'var(--bg-secondary)',
        borderColor: 'var(--border-color)',
      }}
    >
      {/* 头部：菜名和描述 */}
      <div className="px-5 pt-5 pb-3">
        <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
          🍳 {recipe.name}
        </h3>
        <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
          {recipe.description}
        </p>
      </div>

      {/* 信息栏：难度、时间、人数 */}
      <div
        className="px-5 py-3 flex items-center gap-4 text-sm"
        style={{
          borderTop: '1px solid var(--border-color)',
          borderBottom: '1px solid var(--border-color)',
        }}
      >
        <span className={`flex items-center gap-1 ${difficultyColor[recipe.difficulty]}`}>
          <ChefHat size={14} />
          {recipe.difficulty}
        </span>
        <span className="flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
          <Clock size={14} />
          {recipe.cookingTime}
        </span>
        <span className="flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
          <Users size={14} />
          {recipe.servings}人份
        </span>
        {recipe.tags && recipe.tags.length > 0 && (
          <div className="flex gap-1 ml-auto">
            {recipe.tags.map((tag) => (
              <span
                key={tag}
                className="px-2 py-0.5 rounded-full text-xs"
                style={{
                  backgroundColor: 'var(--accent)',
                  color: '#fff',
                }}
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* 食材列表 */}
      <div className="px-5 py-4">
        <h4 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>
          📋 食材
        </h4>
        <div className="grid grid-cols-2 gap-2">
          {recipe.ingredients.map((ing, idx) => (
            <div
              key={idx}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm"
              style={{ backgroundColor: 'var(--bg-primary)' }}
            >
              <span>{ing.emoji || '•'}</span>
              <span style={{ color: 'var(--text-primary)' }}>{ing.name}</span>
              <span className="ml-auto" style={{ color: 'var(--text-secondary)' }}>
                {ing.amount}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* 步骤列表 */}
      <div className="px-5 py-4" style={{ borderTop: '1px solid var(--border-color)' }}>
        <h4 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>
          👨‍🍳 步骤
        </h4>
        <ol className="space-y-3">
          {recipe.steps.map((step, idx) => (
            <li key={idx} className="flex gap-3 text-sm">
              <span
                className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold"
                style={{ backgroundColor: 'var(--accent)', color: '#fff' }}
              >
                {idx + 1}
              </span>
              <span className="pt-0.5" style={{ color: 'var(--text-primary)' }}>
                {step}
              </span>
            </li>
          ))}
        </ol>
      </div>

      {/* 小贴士 */}
      {recipe.tips && (
        <div
          className="px-5 py-4"
          style={{
            borderTop: '1px solid var(--border-color)',
            backgroundColor: 'var(--bg-primary)',
          }}
        >
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            💡 {recipe.tips}
          </p>
        </div>
      )}

      {/* 收藏按钮 */}
      <div className="px-5 py-3" style={{ borderTop: '1px solid var(--border-color)' }}>
        <button
          onClick={handleFavorite}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all"
          style={{
            backgroundColor: isFavorite ? 'var(--accent-alpha, rgba(239,68,68,0.1))' : 'var(--bg-primary)',
            color: isFavorite ? 'var(--accent-red, #ef4444)' : 'var(--text-secondary)',
            border: `1px solid ${isFavorite ? 'var(--accent-red-border, rgba(239,68,68,0.3))' : 'var(--border-color)'}`,
          }}
        >
          <Heart size={16} fill={isFavorite ? 'currentColor' : 'none'} />
          {isFavorite ? '已收藏' : '收藏菜谱'}
        </button>
      </div>
    </div>
  )
}
