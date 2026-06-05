// 偏好相关 API（走 Vite 代理 /api → 后端 :8000）

async function readPreferences(res: Response): Promise<string[]> {
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const data = await res.json()
  return data.preferences ?? []
}

export async function fetchPreferences(): Promise<string[]> {
  return readPreferences(await fetch('/api/preferences'))
}

export async function addPreference(preference: string): Promise<string[]> {
  return readPreferences(
    await fetch('/api/preferences', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preference }),
    })
  )
}

export async function deletePreference(preference: string): Promise<string[]> {
  return readPreferences(
    await fetch('/api/preferences', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preference }),
    })
  )
}
