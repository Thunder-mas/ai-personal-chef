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

  createNewChat: (mode?: string) => void
  switchMode: (mode: string) => void
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

      createNewChat: (mode?: string) => {
        const state = get()
        const current = state.conversations.find((c) => c.id === state.currentConversationId)
        // 没指定就继承当前对话的模式，再退到默认 gourmet
        const newMode = mode ?? current?.mode ?? 'gourmet'
        const id = uuid()
        const newConv: Conversation = {
          id,
          title: '新对话',
          lastUpdated: Date.now(),
          messages: [],
          favoriteRecipes: [],
          mode: newMode,
        }
        set((state) => ({
          conversations: [newConv, ...state.conversations],
          currentConversationId: id,
        }))
      },

      // 切模式 = 开该模式的新对话；当前对话若为空则原地改模式，避免堆空对话
      switchMode: (mode) => {
        const state = get()
        const current = state.conversations.find((c) => c.id === state.currentConversationId)
        if (current && current.messages.length === 0) {
          set((s) => ({
            conversations: s.conversations.map((c) =>
              c.id === current.id ? { ...c, mode } : c
            ),
          }))
        } else {
          get().createNewChat(mode)
        }
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
          // convId 作为 thread_id；convMode 作为该对话的模式（每对话独立）
          const convMode = get().conversations.find((c) => c.id === convId)?.mode ?? 'gourmet'
          for await (const chunk of streamChat(currentMessages, controller.signal, convId ?? undefined, convMode)) {
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
      version: 2,
      // v0→v1：favoriteRecipes string[] → 完整 RecipeData[]
      // v1→v2：给模式系统之前建的老对话补默认模式 gourmet
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
        if (version < 2 && persisted?.conversations) {
          persisted.conversations = persisted.conversations.map((c: any) => ({
            ...c,
            mode: c.mode ?? 'gourmet',
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
