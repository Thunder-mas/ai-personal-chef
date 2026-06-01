import { Message } from '../types/chat'

interface StreamChunk {
  type: 'chunk' | 'done' | 'error'
  content?: string
}

export async function* streamChat(
  messages: Message[]
): AsyncGenerator<string, void, unknown> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: messages.map((m) => ({ role: m.role, content: m.content })),
    }),
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data: StreamChunk = JSON.parse(line.slice(6))
        if (data.type === 'chunk' && data.content) {
          yield data.content
        } else if (data.type === 'error') {
          throw new Error(data.content || 'Unknown error')
        } else if (data.type === 'done') {
          return
        }
      }
    }
  }
}
