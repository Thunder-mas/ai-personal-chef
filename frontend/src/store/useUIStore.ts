import { create } from 'zustand'
import type { RecipeData } from '../types/chat'

interface UIState {
  sidebarOpen: boolean
  viewFavorites: boolean
  shoppingListOpen: boolean
  shoppingListSource: RecipeData[] | null // null = 用收藏；非 null = 用这批菜谱（如周计划）
  preferencesOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  setViewFavorites: (v: boolean) => void
  openShoppingList: (source?: RecipeData[] | null) => void
  closeShoppingList: () => void
  setPreferencesOpen: (open: boolean) => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  viewFavorites: false,
  shoppingListOpen: false,
  shoppingListSource: null,
  preferencesOpen: false,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setViewFavorites: (v) => set({ viewFavorites: v }),
  openShoppingList: (source = null) => set({ shoppingListOpen: true, shoppingListSource: source }),
  closeShoppingList: () => set({ shoppingListOpen: false, shoppingListSource: null }),
  setPreferencesOpen: (open) => set({ preferencesOpen: open }),
}))
