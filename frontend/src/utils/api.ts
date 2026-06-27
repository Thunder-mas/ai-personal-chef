import type { Message } from '../types/chat'

interface StreamChunk {
  type: 'chunk' | 'done' | 'error'
  content?: string
}

// ==================== 多 Agent 套餐规划（营养师→主厨→采购）====================
export interface MealIngredient {
  name: string
  amount?: string
}

export interface MealDish {
  name: string
  reason?: string
  ingredients?: MealIngredient[]
}

export interface ShoppingGroup {
  category: string
  items: MealIngredient[]
}

export interface MealPlanResult {
  request: string
  nutrition_brief: string
  menu: MealDish[]
  retrieved: string[]
  shopping_list: ShoppingGroup[]
  _cached: boolean
}

// 后端 /api/meal-plan 逐 Agent 推送的 SSE 事件
export interface MealPlanEvent {
  type: 'start' | 'cached' | 'nutrition' | 'menu' | 'shopping' | 'done' | 'error'
  content?: string | MealDish[] | ShoppingGroup[]
  retrieved?: string[]
  result?: MealPlanResult
}

export async function* streamMealPlan(
  request: string,
  signal?: AbortSignal
): AsyncGenerator<MealPlanEvent, void, unknown> {
  const response = await fetch('/api/meal-plan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request }),
    signal,
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
  const body = response.body
  if (!body) {
    throw new Error('Response body is null')
  }

  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue // 忽略 ": connected" 心跳行
      try {
        const ev: MealPlanEvent = JSON.parse(line.slice(6))
        if (ev.type === 'error') {
          throw new Error((ev.content as string) || 'Unknown error')
        }
        yield ev
        if (ev.type === 'done') return
      } catch (e) {
        if (e instanceof SyntaxError) continue
        throw e
      }
    }
  }
}

export async function* streamChat(
  messages: Message[],
  signal?: AbortSignal,
  threadId?: string,
  mode?: string
): AsyncGenerator<string, void, unknown> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      thread_id: threadId, // 对话记忆线程：同一对话固定 id，后端按它记住历史
      mode,                // 该对话所属模式（每对话独立）
      messages: messages.map((m) => {
        if (m.images && m.images.length > 0) {
          const parts: Array<{ type: string; text?: string; image_url?: { url: string } }> = []
          if (m.content) {
            parts.push({ type: 'text', text: m.content })
          }
          for (const img of m.images) {
            parts.push({ type: 'image_url', image_url: { url: img } })
          }
          return { role: m.role, content: parts }
        }
        return { role: m.role, content: m.content }
      }),
    }),
    signal,
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  const body = response.body
  if (!body) {
    throw new Error('Response body is null')
  }

  const reader = body.getReader()
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
        try {
          const data: StreamChunk = JSON.parse(line.slice(6))
          if (data.type === 'chunk' && data.content) {
            yield data.content
          } else if (data.type === 'error') {
            throw new Error(data.content || 'Unknown error')
          } else if (data.type === 'done') {
            return
          }
        } catch (e) {
          if (e instanceof SyntaxError) continue
          throw e
        }
      }
    }
  }
}
