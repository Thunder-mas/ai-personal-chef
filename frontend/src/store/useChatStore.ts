import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Conversation, Message, RecipeData } from '../types/chat'
import { streamChat } from '../utils/api'

function uuid(): string {
  return crypto.randomUUID()
}

function generateTitle(content: string): string {
  return content.slice(0, 30) + (content.length > 30 ? '...' : '')
}

interface ChatState {
  conversations: Conversation[]
  currentConversationId: string | null
  darkMode: boolean
  searchTerm: string
  isStreaming: boolean
  abortController: AbortController | null

  createNewChat: () => void
  switchConversation: (id: string) => void
  deleteConversation: (id: string) => void
  renameConversation: (id: string, title: string) => void
  togglePinConversation: (id: string) => void
  toggleFavoriteRecipe: (recipe: RecipeData) => void
  setSearchTerm: (term: string) => void
  toggleDarkMode: () => void
  sendMessage: (content: string, images?: string[]) => Promise<void>

  currentConversation: () => Conversation | undefined
  currentMessages: () => Message[]
  filteredConversations: () => Conversation[]
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      conversations: [],
      currentConversationId: null,
      darkMode: false,
      searchTerm: '',
      isStreaming: false,
      abortController: null,

      createNewChat: () => {
        const id = uuid()
        const newConv: Conversation = {
          id,
          title: '新对话',
          lastUpdated: Date.now(),
          messages: [],
          favoriteRecipes: [],
        }
        set((state) => ({
          conversations: [newConv, ...state.conversations],
          currentConversationId: id,
        }))
      },

      switchConversation: (id) => {
        const prev = get().abortController
        if (prev) prev.abort()
        set({ currentConversationId: id, abortController: null })
      },

      deleteConversation: (id) => {
        set((state) => {
          const remaining = state.conversations.filter((c) => c.id !== id)
          const newCurrentId =
            state.currentConversationId === id
              ? remaining[0]?.id ?? null
              : state.currentConversationId
          return {
            conversations: remaining,
            currentConversationId: newCurrentId,
          }
        })
      },

      renameConversation: (id, title) => {
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === id ? { ...c, title } : c
          ),
        }))
      },

      togglePinConversation: (id) => {
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === id ? { ...c, pinned: !c.pinned } : c
          ),
        }))
      },

      toggleFavoriteRecipe: (recipe) => {
        const state = get()
        const convId = state.currentConversationId
        if (!convId) return

        set((state) => ({
          conversations: state.conversations.map((c) => {
            if (c.id !== convId) return c
            const favorites = c.favoriteRecipes || []
            const isFavorited = favorites.some((r) => r.name === recipe.name)
            return {
              ...c,
              favoriteRecipes: isFavorited
                ? favorites.filter((r) => r.name !== recipe.name)
                : [...favorites, recipe],
            }
          }),
        }))
      },

      setSearchTerm: (term) => set({ searchTerm: term }),

      toggleDarkMode: () =>
        set((state) => ({ darkMode: !state.darkMode })),

      sendMessage: async (content, images) => {
        const prev = get().abortController
        if (prev) prev.abort()

        const controller = new AbortController()
        set({ abortController: controller })

        const state = get()
        let convId = state.currentConversationId

        if (!convId) {
          get().createNewChat()
          convId = get().currentConversationId
        }

        const userMsg: Message = {
          id: uuid(),
          role: 'user',
          content,
          timestamp: Date.now(),
          status: 'done',
          images,
        }

        const assistantMsg: Message = {
          id: uuid(),
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
          status: 'streaming',
        }

        set((state) => ({
          isStreaming: true,
          conversations: state.conversations.map((c) =>
            c.id === convId
              ? {
                  ...c,
                  title:
                    c.messages.length === 0
                      ? generateTitle(content)
                      : c.title,
                  lastUpdated: Date.now(),
                  messages: [...c.messages, userMsg, assistantMsg],
                }
              : c
          ),
        }))

        try {
          const currentMessages = get()
            .conversations.find((c) => c.id === convId)
            ?.messages.filter((m) => m.id !== assistantMsg.id) ?? []

          let accumulated = ''
          for await (const chunk of streamChat(currentMessages, controller.signal)) {
            accumulated += chunk
            set((state) => ({
              conversations: state.conversations.map((c) =>
                c.id === convId
                  ? {
                      ...c,
                      messages: c.messages.map((m) =>
                        m.id === assistantMsg.id
                          ? { ...m, content: accumulated }
                          : m
                      ),
                    }
                  : c
              ),
            }))
          }

          set((state) => ({
            isStreaming: false,
            abortController: null,
            conversations: state.conversations.map((c) =>
              c.id === convId
                ? {
                    ...c,
                    messages: c.messages.map((m) =>
                      m.id === assistantMsg.id
                        ? { ...m, status: 'done' }
                        : m
                    ),
                  }
                : c
            ),
          }))
        } catch (error) {
          if (error instanceof DOMException && error.name === 'AbortError') {
            set({ isStreaming: false, abortController: null })
            return
          }
          set((state) => ({
            isStreaming: false,
            abortController: null,
            conversations: state.conversations.map((c) =>
              c.id === convId
                ? {
                    ...c,
                    messages: c.messages.map((m) =>
                      m.id === assistantMsg.id
                        ? {
                            ...m,
                            status: 'error',
                            content: `出错了：${error instanceof Error ? error.message : '未知错误'}`,
                          }
                        : m
                    ),
                  }
                : c
            ),
          }))
        }
      },

      currentConversation: () => {
        const state = get()
        return state.conversations.find(
          (c) => c.id === state.currentConversationId
        )
      },

      currentMessages: () => {
        return get().currentConversation()?.messages ?? []
      },

      filteredConversations: () => {
        const state = get()
        const term = state.searchTerm.toLowerCase()
        const filtered = term
          ? state.conversations.filter((c) =>
              c.title.toLowerCase().includes(term)
            )
          : state.conversations
        return [...filtered].sort((a, b) => {
          if (a.pinned && !b.pinned) return -1
          if (!a.pinned && b.pinned) return 1
          return b.lastUpdated - a.lastUpdated
        })
      },
    }),
    {
      name: 'ai-chef-storage',
      version: 1,
      // v0 的 favoriteRecipes 是 string[]（仅菜名），v1 升级为完整 RecipeData[]。
      // 旧菜名无法还原食材，转成占位对象（空食材，不参与购物清单聚合）。
      migrate: (persisted: any, version: number) => {
        if (version < 1 && persisted?.conversations) {
          persisted.conversations = persisted.conversations.map((c: any) => ({
            ...c,
            favoriteRecipes: Array.isArray(c.favoriteRecipes)
              ? c.favoriteRecipes.map((f: any) =>
                  typeof f === 'string'
                    ? {
                        name: f,
                        description: '',
                        difficulty: '简单',
                        cookingTime: '',
                        servings: 1,
                        ingredients: [],
                        steps: [],
                      }
                    : f
                )
              : [],
          }))
        }
        return persisted
      },
      partialize: (state) => ({
        conversations: state.conversations,
        currentConversationId: state.currentConversationId,
        darkMode: state.darkMode,
      }),
    }
  )
)
