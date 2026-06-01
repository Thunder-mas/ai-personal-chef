import { useRef } from 'react'
import { ChefHat } from 'lucide-react'
import { useChatStore } from '../../store/useChatStore'
import { useAutoScroll } from '../../hooks/useAutoScroll'
import { MessageBubble } from './MessageBubble'
import { TypingIndicator } from './TypingIndicator'

function WelcomeScreen() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4 px-4">
      <div
        className="w-16 h-16 rounded-2xl flex items-center justify-center"
        style={{ backgroundColor: 'var(--accent)', color: '#fff' }}
      >
        <ChefHat size={32} />
      </div>
      <h2 className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>
        AI 私人厨师
      </h2>
      <p className="text-center max-w-md" style={{ color: 'var(--text-secondary)' }}>
        告诉我你有什么食材，我来帮你想想做什么好吃的
      </p>
    </div>
  )
}

export function MessageList() {
  const messages = useChatStore((s) => s.currentMessages())
  const isStreaming = useChatStore((s) => s.isStreaming)
  const containerRef = useRef<HTMLDivElement>(null)

  useAutoScroll(containerRef, messages)

  if (messages.length === 0) {
    return <WelcomeScreen />
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto px-4 py-6"
    >
      <div className="max-w-3xl mx-auto space-y-6">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {isStreaming &&
          messages.length > 0 &&
          messages[messages.length - 1].role === 'assistant' &&
          messages[messages.length - 1].content === '' && (
            <TypingIndicator />
          )}
      </div>
    </div>
  )
}
