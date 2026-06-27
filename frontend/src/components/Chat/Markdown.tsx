import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'

// 单独成块：react-markdown + remark-gfm + rehype-highlight + highlight.js 体积较大，
// 由 MessageBubble 用 React.lazy 按需加载，避免拖累首屏（高亮库尤其大）。
export default function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
      {children}
    </ReactMarkdown>
  )
}
