export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  status?: 'sending' | 'streaming' | 'done' | 'error'
}

export interface RecipeData {
  name: string           // 菜名
  description: string    // 简短描述
  difficulty: '简单' | '中等' | '复杂'  // 难度等级
  cookingTime: string    // 烹饪时间：30分钟
  servings: number       // 用餐人数：2
  ingredients: Array<{   // 食材列表
    name: string         // 食材名称
    amount: string       // 用量：300g
    emoji?: string       // 可选emoji图标
  }>
  steps: string[]        // 烹饪步骤
  tips?: string          // 可选小贴士
  tags?: string[]        // 可选标签：['川菜', '快手菜']
}

export interface Conversation {
  id: string
  title: string
  lastUpdated: number
  messages: Message[]
  pinned?: boolean
  favoriteRecipes?: string[]  // 收藏的菜谱名称列表
}
