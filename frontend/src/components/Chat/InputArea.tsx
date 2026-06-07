import { useState, useRef, type KeyboardEvent } from 'react'
import { Send, ImagePlus, X } from 'lucide-react'
import { useChatStore } from '../../store/useChatStore'

interface ImagePreview {
  file: File
  preview: string
}

export function InputArea() {
  const [input, setInput] = useState('')
  const [images, setImages] = useState<ImagePreview[]>([])
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const isStreaming = useChatStore((s) => s.isStreaming)

  const adjustHeight = () => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`
  }

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    adjustHeight()
  }

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return

    const newImages: ImagePreview[] = Array.from(files).map((file) => ({
      file,
      preview: URL.createObjectURL(file),
    }))

    setImages((prev) => [...prev, ...newImages])

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeImage = (index: number) => {
    setImages((prev) => {
      const removed = prev[index]
      URL.revokeObjectURL(removed.preview)
      return prev.filter((_, i) => i !== index)
    })
  }

  const fileToBase64 = (file: File): Promise<string> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result as string)
      reader.onerror = reject
      reader.readAsDataURL(file)
    })

  const handleSend = async () => {
    const trimmed = input.trim()
    if ((!trimmed && images.length === 0) || isStreaming) return

    const base64Images = await Promise.all(images.map((img) => fileToBase64(img.file)))

    // 立即清空输入框与图片预览（不等 AI 回复结束）
    setInput('')
    images.forEach((img) => URL.revokeObjectURL(img.preview))
    setImages([])
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    // 发送：sendMessage 内部会把用户消息入列并流式更新对话，无需 await 来清空输入
    await sendMessage(trimmed, base64Images.length > 0 ? base64Images : undefined)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="pb-4 pt-2">
      <div
        className="max-w-2xl mx-auto rounded-2xl px-4 py-3"
        style={{ backgroundColor: 'var(--bg-secondary)' }}
      >
        {images.length > 0 && (
          <div className="flex gap-2 pb-3 flex-wrap">
            {images.map((img, index) => (
              <div key={index} className="relative group">
                <img
                  src={img.preview}
                  alt="上传图片"
                  className="w-20 h-20 object-cover rounded-lg"
                />
                <button
                  onClick={() => removeImage(index)}
                  className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{ backgroundColor: 'var(--accent)', color: '#fff' }}
                >
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        )}

        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="告诉 AI Chef 你想吃什么..."
          rows={1}
          className="w-full resize-none bg-transparent outline-none"
          style={{
            color: 'var(--text-primary)',
            fontSize: '16px',
            lineHeight: '1.5',
            maxHeight: '150px',
          }}
          disabled={isStreaming}
        />

        <div className="flex items-center justify-between pt-2">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors"
            style={{
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-color)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--accent)'
              e.currentTarget.style.color = 'var(--accent)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-color)'
              e.currentTarget.style.color = 'var(--text-secondary)'
            }}
          >
            <ImagePlus size={14} />
            上传图片
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            onChange={handleImageUpload}
            className="hidden"
          />

          <button
            onClick={handleSend}
            disabled={(!input.trim() && images.length === 0) || isStreaming}
            className="w-9 h-9 rounded-full flex items-center justify-center text-white disabled:opacity-40 hover:opacity-90 transition-opacity"
            style={{ backgroundColor: 'var(--accent)' }}
            aria-label="发送消息"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  )
}
