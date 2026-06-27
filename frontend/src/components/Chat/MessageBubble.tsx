import { lazy, Suspense, useMemo } from 'react'
import type { Message, RecipeData, MealPlan } from '../../types/chat'
import { RecipeCard } from './RecipeCard'
import { MealPlanCard } from './MealPlanCard'

// 懒加载 markdown 渲染（含大体积的代码高亮库），首屏不下载
const Markdown = lazy(() => import('./Markdown'))

interface MessageBubbleProps {
  message: Message
}

type Segment =
  | { type: 'text'; content: string }
  | { type: 'recipe'; recipe: RecipeData }
  | { type: 'mealplan'; plan: MealPlan }

// 轻量修复常见的 LLM JSON 小毛病
function repairJson(jsonStr: string): string {
  let t = jsonStr.trim()
  // servings 写成 "2人份" 之类 → 取数字
  t = t.replace(/"servings"\s*:\s*"?(\d+)\s*[^,}\]]*"?/g, '"servings":$1')
  // 去掉对象/数组结尾多余的逗号： ,}  ,]
  t = t.replace(/,\s*([}\]])/g, '$1')
  return t
}

// 把一段 JSON 按"形状"分派成 菜谱 / 周计划 卡片；不符合则返回 null
function parseCard(jsonStr: string): Segment | null {
  let parsed: any
  try {
    parsed = JSON.parse(repairJson(jsonStr))
  } catch {
    return null
  }
  if (parsed && Array.isArray(parsed.days) && parsed.days.length > 0) {
    return { type: 'mealplan', plan: parsed as MealPlan }
  }
  if (parsed && parsed.name && parsed.ingredients && parsed.steps) {
    return { type: 'recipe', recipe: parsed as RecipeData }
  }
  return null
}

// 去掉残留的代码围栏标记，避免把 ```recipe / ``` 当普通文本显示出来
function cleanText(s: string): string {
  return s.replace(/```[a-zA-Z]*/g, '').trim()
}

// 从文本中智能提取JSON对象（处理嵌套括号）
function extractJsonObjects(text: string): string[] {
  const results: string[] = []
  let i = 0
  while (i < text.length) {
    if (text[i] === '{') {
      let depth = 0
      let start = i
      let inString = false
      let escaped = false
      for (let j = i; j < text.length; j++) {
        const ch = text[j]
        if (escaped) {
          escaped = false
          continue
        }
        if (ch === '\\') {
          escaped = true
          continue
        }
        if (ch === '"') {
          inString = !inString
          continue
        }
        if (inString) continue
        if (ch === '{') depth++
        if (ch === '}') {
          depth--
          if (depth === 0) {
            results.push(text.slice(start, j + 1))
            i = j + 1
            break
          }
        }
      }
      if (depth !== 0) i++ // 没找到匹配的 }，跳过
    } else {
      i++
    }
  }
  return results
}

function parseAllRecipes(content: string, isStreaming: boolean): Segment[] {
  const segments: Segment[] = []

  // 用花括号匹配找出所有【完整】JSON 对象（不依赖代码围栏是否闭合，最稳），按形状分派卡片
  const blocks: Array<{ start: number; end: number; seg: Segment }> = []
  let searchFrom = 0
  for (const jsonStr of extractJsonObjects(content)) {
    const seg = parseCard(jsonStr)
    if (!seg) continue
    const start = content.indexOf(jsonStr, searchFrom)
    if (start < 0) continue
    blocks.push({ start, end: start + jsonStr.length, seg })
    searchFrom = start + jsonStr.length
  }

  // 卡片之间/前后的文本（去掉残留围栏）
  let lastEnd = 0
  for (const block of blocks) {
    const before = cleanText(content.slice(lastEnd, block.start))
    if (before) segments.push({ type: 'text', content: before })
    segments.push(block.seg)
    lastEnd = block.end
  }

  // 尾部：流式中若有尚未闭合的卡片 JSON（{ 多于 }），用占位代替，避免露出原始 JSON
  const tail = content.slice(lastEnd)
  const opens = (tail.match(/\{/g) || []).length
  const closes = (tail.match(/\}/g) || []).length
  if (isStreaming && opens > closes) {
    const head = cleanText(tail.slice(0, tail.indexOf('{')))
    if (head) segments.push({ type: 'text', content: head })
    segments.push({ type: 'text', content: '🍳 正在生成卡片…' })
  } else {
    const t = cleanText(tail)
    if (t) segments.push({ type: 'text', content: t })
  }

  if (segments.length === 0) {
    segments.push({ type: 'text', content })
  }

  return segments
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  const segments = useMemo(
    () => (isUser ? [] : parseAllRecipes(message.content, message.status === 'streaming')),
    [isUser, message.content, message.status]
  )

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div
          className="max-w-[80%] px-5 py-3.5 bg-[var(--bubble-user)] rounded-2xl rounded-br-md"
        >
          {message.images && message.images.length > 0 && (
            <div className="flex gap-2 flex-wrap mb-2">
              {message.images.map((src, i) => (
                <img
                  key={i}
                  src={src}
                  alt="上传图片"
                  className="w-32 h-32 object-cover rounded-lg"
                />
              ))}
            </div>
          )}
          {message.content && (
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[80%]">
        {segments.map((seg, idx) => {
          if (seg.type === 'text') {
            return (
              <div
                key={idx}
                className="px-5 py-3.5 bg-[var(--bubble-ai)] rounded-2xl rounded-bl-md shadow-[var(--shadow)]"
              >
                <div className="markdown-body">
                  <Suspense fallback={<p className="whitespace-pre-wrap break-words">{seg.content}</p>}>
                    <Markdown>{seg.content}</Markdown>
                  </Suspense>
                </div>
              </div>
            )
          }
          if (seg.type === 'recipe') {
            return <RecipeCard key={idx} recipe={seg.recipe} />
          }
          return <MealPlanCard key={idx} plan={seg.plan} />
        })}
      </div>
    </div>
  )
}
