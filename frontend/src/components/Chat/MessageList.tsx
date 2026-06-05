import { useEffect, useRef } from 'react'
import { ChefHat } from 'lucide-react'
import { useChatStore } from '../../store/useChatStore'
import { MessageBubble } from './MessageBubble'
import { TypingIndicator } from './TypingIndicator'

export function MessageList() {
  const currentConversationId = useChatStore((s) => s.currentConversationId)
  const conversations = useChatStore((s) => s.conversations)
  const isStreaming = useChatStore((s) => s.isStreaming)
  const containerRef = useRef<HTMLDivElement>(null)

  const currentConv = conversations.find((c) => c.id === currentConversationId)
  const messages = currentConv?.messages ?? []

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages.length])

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col justify-end">
        <div className="flex-shrink-0 max-w-2xl mx-auto text-center pb-50">
          <div
            className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4"
            style={{ backgroundColor: 'color-mix(in srgb, var(--accent) 15%, transparent)' }}
          >
            <ChefHat size={32} style={{ color: 'var(--accent)' }} />
          </div>
          <h1
            className="text-3xl font-bold mb-2"
            style={{ color: 'var(--text-primary)' }}
          >
            AI Chef
          </h1>
          <p
            className="text-base"
            style={{ color: 'var(--text-secondary)' }}
          >
            告诉我你想吃什么，或者你有什么食材
          </p>
          <p
            className="text-sm mt-1"
            style={{ color: 'var(--text-secondary)', opacity: 0.7 }}
          >
            我会为你推荐菜谱
          </p>
        </div>
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
