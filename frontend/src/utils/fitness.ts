// 健身档案 API（走 Vite 代理 /api → 后端 :8000）

export interface FitnessProfile {
  gender: string         // 男 / 女
  age: number
  height_cm: number
  weight_kg: number
  target_weight_kg?: number | null // 目标体重
  activity_level: string // 久坐/轻度/中度/高度/极高
  goal: string           // 减脂/维持/增肌
}

export interface FitnessTargets {
  goal: string
  calories: number       // 目标每日热量
  protein: number
  carbs: number
  fat: number
  maintenance: number    // 维持热量(TDEE)
  daily_adjust: number   // 每日缺口(负)/盈余(正)
  weekly_rate_kg: number // 每周目标变化
  target_weight?: number | null
  weeks_to_goal?: number | null // 预计达成周数
}

interface FitnessResponse {
  profile: FitnessProfile | null
  targets: FitnessTargets | null
}

export async function fetchFitnessProfile(): Promise<FitnessResponse> {
  const r = await fetch('/api/fitness/profile')
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export async function saveFitnessProfile(p: FitnessProfile): Promise<FitnessResponse> {
  const r = await fetch('/api/fitness/profile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(p),
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}
