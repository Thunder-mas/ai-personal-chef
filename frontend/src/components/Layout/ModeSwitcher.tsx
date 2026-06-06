import { useEffect, useState } from 'react'
import { fetchMode, setMode as apiSetMode, type ModeOption } from '../../utils/mode'

// 模式切换器：切换后影响 AI 的人设与推荐行为（美食 / 健身 / …）
export function ModeSwitcher() {
  const [modes, setModes] = useState<ModeOption[]>([])
  const [current, setCurrent] = useState<string>('')

  useEffect(() => {
    fetchMode()
      .then(({ mode, modes }) => {
        setCurrent(mode)
        setModes(modes)
      })
      .catch(() => {
        /* 后端未启动时静默，不渲染切换器 */
      })
  }, [])

  const handleSwitch = async (key: string) => {
    if (key === current) return
    const prev = current
    setCurrent(key) // 乐观更新
    try {
      const { mode } = await apiSetMode(key)
      setCurrent(mode)
    } catch {
      setCurrent(prev) // 失败回滚
    }
  }

  if (modes.length === 0) return null

  return (
    <div className="flex justify-center py-2">
      <div
        className="inline-flex gap-1 p-1 rounded-full"
        style={{ backgroundColor: 'var(--bg-secondary)' }}
      >
        {modes.map((m) => {
          const active = m.key === current
          return (
            <button
              key={m.key}
              onClick={() => handleSwitch(m.key)}
              className="px-4 py-1.5 rounded-full text-sm font-medium transition-colors"
              style={
                active
                  ? { backgroundColor: 'var(--accent)', color: '#fff' }
                  : { color: 'var(--text-secondary)' }
              }
            >
              {m.emoji} {m.name}
            </button>
          )
        })}
      </div>
    </div>
  )
}
