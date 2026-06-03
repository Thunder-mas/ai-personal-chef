import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import type { Message } from '../../types/chat'

interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-slide-up`}>
      <div
        className={`max-w-[75%] px-4 py-3 shadow-sm ${
          isUser
            ? 'rounded-2xl rounded-br-md'
            : 'rounded-2xl rounded-bl-md markdown-body'
        }`}
        style={{
          backgroundColor: isUser ? 'var(--bubble-user)' : 'var(--bubble-ai)',
          color: 'var(--text-primary)',
        }}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
            {message.content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  )
}
