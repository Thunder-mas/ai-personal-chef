import { MessageList } from '../Chat/MessageList'
import { InputArea } from '../Chat/InputArea'
import { useUIStore } from '../../store/useUIStore'

export function MainArea() {
  const sidebarOpen = useUIStore((s) => s.sidebarOpen)

  return (
    <div
      className="flex-1 flex flex-col min-w-0 h-full overflow-hidden"
      style={{
        backgroundColor: 'var(--bg-primary)',
        paddingLeft: sidebarOpen ? '200px' : '400px',
        paddingRight: '14px',
      }}
    >
      <MessageList />
      <InputArea />
    </div>
  )
}
