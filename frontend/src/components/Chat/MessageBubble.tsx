import { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import type { Message, RecipeData, MealPlan } from '../../types/chat'
import { RecipeCard } from './RecipeCard'
import { MealPlanCard } from './MealPlanCard'

interface MessageBubbleProps {
  message: Message
}

type Segment =
  | { type: 'text'; content: string }
  | { type: 'recipe'; recipe: RecipeData }
  | { type: 'mealplan'; plan: MealPlan }

function cleanJsonStr(jsonStr: string): string {
  // 只匹配 servings 字段的值，不吞掉后面的逗号或括号
  return jsonStr.replace(/"servings"\s*:\s*"?(\d+)\s*[^,}\]]*"?/g, '"servings":$1')
}

function tryParseRecipe(jsonStr: string): RecipeData | null {
  try {
    const cleaned = cleanJsonStr(jsonStr.trim())
    const parsed = JSON.parse(cleaned)
    if (parsed.name && parsed.ingredients && parsed.steps) {
      return parsed as RecipeData
    }
  } catch {
    // 解析失败
  }
  return null
}

function tryParseMealPlan(jsonStr: string): MealPlan | null {
  try {
    const parsed = JSON.parse(jsonStr.trim())
    if (parsed && Array.isArray(parsed.days) && parsed.days.length > 0) {
      return parsed as MealPlan
    }
  } catch {
    // 解析失败
  }
  return null
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

function parseAllRecipes(content: string): Segment[] {
  const segments: Segment[] = []

  // 策略1：匹配所有代码块，按语言标签分派（mealplan / recipe|json）
  const codeBlockRegex = /```(\w+)?\s*\n?([\s\S]*?)\n?\s*```/g
  const blocks: Array<{ start: number; end: number; seg: Segment }> = []

  let match: RegExpExecArray | null
  while ((match = codeBlockRegex.exec(content)) !== null) {
    const tag = (match[1] || '').toLowerCase()
    const body = match[2]
    const range = { start: match.index, end: match.index + match[0].length }
    if (tag === 'mealplan') {
      const plan = tryParseMealPlan(body)
      if (plan) blocks.push({ ...range, seg: { type: 'mealplan', plan } })
    } else {
      const recipe = tryParseRecipe(body)
      if (recipe) blocks.push({ ...range, seg: { type: 'recipe', recipe } })
    }
  }

  // 策略2：如果没有代码块匹配，扫描全文找JSON对象（仅菜谱）
  if (blocks.length === 0) {
    const jsonObjects = extractJsonObjects(content)
    for (const jsonStr of jsonObjects) {
      const recipe = tryParseRecipe(jsonStr)
      if (recipe) {
        const startIdx = content.indexOf(jsonStr)
        blocks.push({
          start: startIdx,
          end: startIdx + jsonStr.length,
          seg: { type: 'recipe', recipe },
        })
        break
      }
    }
  }

  // 按位置排序
  blocks.sort((a, b) => a.start - b.start)

  // 根据代码块位置切割内容
  let lastEnd = 0
  for (const block of blocks) {
    const textBefore = content.slice(lastEnd, block.start).trim()
    if (textBefore) {
      segments.push({ type: 'text', content: textBefore })
    }
    segments.push(block.seg)
    lastEnd = block.end
  }

  // 剩余文本
  const remaining = content.slice(lastEnd).trim()
  if (remaining) {
    segments.push({ type: 'text', content: remaining })
  }

  // 如果没有任何匹配，返回原始内容
  if (segments.length === 0) {
    segments.push({ type: 'text', content })
  }

  return segments
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  const segments = useMemo(
    () => (isUser ? [] : parseAllRecipes(message.content)),
    [isUser, message.content]
  )

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div
          className="max-w-[80%] px-5 py-3.5 bg-[var(--bubble-user)] rounded-2xl rounded-br-md"
        >
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
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
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeHighlight]}
                  >
                    {seg.content}
                  </ReactMarkdown>
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
