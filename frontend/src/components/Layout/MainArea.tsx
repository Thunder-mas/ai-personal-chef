import { MessageList } from '../Chat/MessageList'
import { InputArea } from '../Chat/InputArea'

export function MainArea() {
  return (
    <div
      className="flex-1 flex flex-col min-w-0 h-full overflow-hidden"
      style={{
        backgroundColor: 'var(--bg-primary)',
        // 左右对称内边距，内容靠 max-w-2xl + mx-auto 居中；
        // 侧边栏的让位已由 App.tsx 的 marginLeft 处理，这里不需要再补左边距
        paddingLeft: '16px',
        paddingRight: '16px',
      }}
    >
      <MessageList />
      <InputArea />
    </div>
  )
}
