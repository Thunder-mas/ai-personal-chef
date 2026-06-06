import { useEffect, useState } from 'react'
import { fetchMode, type ModeOption } from '../../utils/mode'
import { useChatStore } from '../../store/useChatStore'

// 模式切换器：每个对话固定一个模式。切到别的模式 = 开该模式的新对话（空对话则原地改）。
// 当前对话已有内容时，切换会弹窗确认（因为会新开一个对话）。
export function ModeSwitcher() {
  const [modes, setModes] = useState<ModeOption[]>([])
  const [pending, setPending] = useState<ModeOption | null>(null) // 待确认要切到的模式
  const conversations = useChatStore((s) => s.conversations)
  const currentConversationId = useChatStore((s) => s.currentConversationId)
  const switchMode = useChatStore((s) => s.switchMode)

  const current = conversations.find((c) => c.id === currentConversationId)
  const activeMode = current?.mode ?? 'gourmet'

  useEffect(() => {
    fetchMode()
      .then(({ modes }) => setModes(modes))
      .catch(() => {
        /* 后端未启动时静默，不渲染切换器 */
      })
  }, [])

  const handleClick = (m: ModeOption) => {
    if (m.key === activeMode) return
    // 当前对话已有内容 → 切换会新开对话，先确认；空对话则原地改、无需打扰
    if (current && current.messages.length > 0) {
      setPending(m)
    } else {
      switchMode(m.key)
    }
  }

  const confirmSwitch = () => {
    if (pending) switchMode(pending.key)
    setPending(null)
  }

  if (modes.length === 0) return null

  return (
    <>
      <div className="flex justify-center py-2">
        <div
          className="inline-flex gap-1 p-1 rounded-full"
          style={{ backgroundColor: 'var(--bg-secondary)' }}
        >
          {modes.map((m) => {
            const active = m.key === activeMode
            return (
              <button
                key={m.key}
                onClick={() => handleClick(m)}
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

      {/* 切换确认弹窗 */}
      {pending && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
          onClick={() => setPending(null)}
        >
          <div
            className="w-full max-w-xs rounded-2xl p-5"
            style={{ backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-base font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
              切换到 {pending.emoji} {pending.name}？
            </h3>
            <p className="text-sm mb-4 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
              每个对话只属于一个模式。切换会为「{pending.name}」新开一个对话，
              当前对话会保留在左侧列表，随时可切回。
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setPending(null)}
                className="px-4 py-2 rounded-lg text-sm transition-colors"
                style={{ border: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}
              >
                取消
              </button>
              <button
                onClick={confirmSwitch}
                className="px-4 py-2 rounded-lg text-sm font-medium transition-opacity hover:opacity-90"
                style={{ backgroundColor: 'var(--accent)', color: '#fff' }}
              >
                切换并新建
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
