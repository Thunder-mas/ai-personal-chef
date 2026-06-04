import { useEffect, useRef } from 'react'
import { ChefHat } from 'lucide-react'
import { useChatStore } from '../../store/useChatStore'
import { MessageBubble } from './MessageBubble'
import { TypingIndicator } from './TypingIndicator'

export function MessageList() {
  const messages = useChatStore((s) => s.currentMessages())
  const isStreaming = useChatStore((s) => s.isStreaming)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center px-4">
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
          style={{ backgroundColor: 'var(--accent)', color: '#fff' }}
        >
          <ChefHat size={32} />
        </div>
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
          AI Chef
        </h1>
        <p className="max-w-md" style={{ color: 'var(--text-secondary)' }}>
          告诉我你喜欢的口味或食材，我会为你推荐菜谱并解答烹饪问题。
        </p>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto"
    >
      <div
        className="max-w-2xl mx-auto pt-10 pb-6 px-6 space-y-6 rounded-2xl"
        style={{ marginTop: '30px' }}
      >
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {isStreaming && <TypingIndicator />}
      </div>
    </div>
  )
}
