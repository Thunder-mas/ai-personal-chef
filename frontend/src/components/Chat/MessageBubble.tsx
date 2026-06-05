import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import type { Message, RecipeData } from '../../types/chat'
import { RecipeCard } from './RecipeCard'

interface MessageBubbleProps {
  message: Message
}

function parseRecipeContent(content: string): { before: string; recipe: RecipeData | null; after: string } {
  const recipeRegex = /```recipe\n([\s\S]*?)\n```/
  const match = content.match(recipeRegex)

  if (!match) {
    return { before: content, recipe: null, after: '' }
  }

  const before = content.slice(0, match.index).trim()
  const after = content.slice(match.index! + match[0].length).trim()

  try {
    const recipe = JSON.parse(match[1]) as RecipeData
    return { before, recipe, after }
  } catch {
    return { before: content, recipe: null, after: '' }
  }
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

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

  const { before, recipe, after } = parseRecipeContent(message.content)

  return (
    <div className="flex justify-start">
      <div className="max-w-[80%]">
        {before && (
          <div
            className="px-5 py-3.5 bg-[var(--bubble-ai)] rounded-2xl rounded-bl-md shadow-[var(--shadow)]"
          >
            <div className="markdown-body">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
              >
                {before}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {recipe && <RecipeCard recipe={recipe} />}

        {after && (
          <div
            className="px-5 py-3.5 bg-[var(--bubble-ai)] rounded-2xl rounded-bl-md shadow-[var(--shadow)]"
          >
            <div className="markdown-body">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
              >
                {after}
              </ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
