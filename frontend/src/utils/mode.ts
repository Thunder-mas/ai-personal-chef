export interface ModeOption {
  key: string
  name: string
  emoji: string
}

interface ModeResponse {
  mode: string
  modes: ModeOption[]
}

export async function fetchMode(): Promise<ModeResponse> {
  const r = await fetch('/api/mode')
  if (!r.ok) throw new Error('获取模式失败')
  return r.json()
}

export async function setMode(mode: string): Promise<ModeResponse> {
  const r = await fetch('/api/mode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  })
  if (!r.ok) throw new Error('切换模式失败')
  return r.json()
}
