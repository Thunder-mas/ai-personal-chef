export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  status?: 'sending' | 'streaming' | 'done' | 'error'
}

export interface RecipeData {
  title: string
  description: string
  imageUrl?: string
  ingredients: string[]
  steps: string[]
  prepTime: string
  cookTime: string
}

export interface Conversation {
  id: string
  title: string
  lastUpdated: number
  messages: Message[]
  pinned?: boolean
}
