// 今日饮食记录 API（走 Vite 代理 /api → 后端 :8000）

export interface FoodEntry {
  id: number
  name: string
  calories: number
  protein: number
  carbs: number
  fat: number
}

export interface Macros {
  calories: number
  protein: number
  carbs: number
  fat: number
}

export interface DaySummary {
  date: string
  entries: FoodEntry[]
  totals: Macros
  targets: (Macros & { goal: string }) | null
  remaining: Macros | null
}

export interface NewFoodEntry {
  name: string
  calories?: number
  protein?: number
  carbs?: number
  fat?: number
}

export async function fetchFoodLog(): Promise<DaySummary> {
  const r = await fetch('/api/food-log')
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function addFoodEntry(entry: NewFoodEntry): Promise<DaySummary> {
  const r = await fetch('/api/food-log', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(entry),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function deleteFoodEntry(id: number): Promise<DaySummary> {
  const r = await fetch(`/api/food-log/${id}`, { method: 'DELETE' })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}
