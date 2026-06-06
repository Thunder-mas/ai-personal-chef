export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  status?: 'sending' | 'streaming' | 'done' | 'error'
  images?: string[]  // base64 data URLs
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
  nutrition?: {          // 可选每份营养（健身模式下 AI 会填充）
    calories: number     // 热量 kcal
    protein: number      // 蛋白质 g
    carbs: number        // 碳水 g
    fat: number          // 脂肪 g
  }
}

export interface PlannedMeal {
  slot?: string          // 餐次：早餐 / 午餐 / 晚餐
  name: string           // 菜名
  brief?: string         // 一句话简述
  ingredients?: Array<{  // 食材（供购物清单聚合）
    name: string
    amount: string
    emoji?: string
  }>
}

export interface MealPlanDay {
  day: string            // 周一 / 周二 …
  meals: PlannedMeal[]   // 当天的餐（午餐/晚餐等）
}

export interface MealPlan {
  title?: string         // 计划标题，如"本周食谱"
  days: MealPlanDay[]    // 一周计划
}

export interface Conversation {
  id: string
  title: string
  lastUpdated: number
  messages: Message[]
  pinned?: boolean
  favoriteRecipes?: RecipeData[]  // 收藏的完整菜谱数据（含食材，供购物清单聚合）
  mode?: string                   // 该对话所属模式（美食/健身），切模式=开新对话
}
