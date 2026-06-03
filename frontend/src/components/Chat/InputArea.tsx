import { useState, useRef, useEffect } from 'react'
import { Send, Paperclip } from 'lucide-react'
import { useChatStore } from '../../store/useChatStore'

export function InputArea() {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const isStreaming = useChatStore((s) => s.isStreaming)

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return
    const msg = input.trim()
    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
    await sendMessage(msg)
  }

  useEffect(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 150) + 'px'
    }
  }, [input])

  return (
    <div
      className="px-4 py-4"
      style={{ borderTop: '1px solid var(--border-color)', backgroundColor: 'var(--bg-primary)' }}
    >
      <div className="max-w-2xl mx-auto flex items-end gap-2">
        <button
          className="shrink-0 p-3 rounded-xl transition-colors"
          style={{ color: 'var(--text-secondary)' }}
          onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)' }}
          onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-secondary)' }}
          aria-label="上传图片"
        >
          <Paperclip size={20} />
        </button>

        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          placeholder="告诉 AI Chef 你想吃什么..."
          rows={1}
          className="flex-1 resize-none rounded-xl px-4 py-3 outline-none text-sm"
          style={{
            border: '1px solid var(--border-color)',
            backgroundColor: 'var(--bg-secondary)',
            color: 'var(--text-primary)',
            maxHeight: '150px',
          }}
        />

        <button
          onClick={handleSend}
          disabled={!input.trim() || isStreaming}
          className="shrink-0 p-3 rounded-xl text-white transition-opacity disabled:opacity-40"
          style={{ backgroundColor: 'var(--accent)' }}
        >
          <Send size={20} />
        </button>
      </div>
    </div>
  )
}
