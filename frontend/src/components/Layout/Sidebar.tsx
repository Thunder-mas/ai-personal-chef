import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import { useChatStore } from '../../store/useChatStore'
import { IconButton } from '../common/IconButton'
import { ThemeToggle } from '../common/ThemeToggle'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const {
    createNewChat,
    switchConversation,
    setSearchTerm,
    currentConversationId,
    filteredConversations,
  } = useChatStore()

  const conversations = filteredConversations()

  const handleNewChat = () => {
    createNewChat()
    onClose()
  }

  const handleSelect = (id: string) => {
    switchConversation(id)
    onClose()
  }

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 md:hidden"
          onClick={onClose}
        />
      )}

      <div
        className={`
          fixed md:relative z-50 md:z-auto
          w-[260px] flex-shrink-0 h-full
          border-r flex flex-col
          transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}
        style={{
          backgroundColor: 'var(--bg-sidebar)',
          borderColor: 'var(--border-color)',
        }}
      >
        {/* Header */}
        <div className="p-4 flex items-center justify-between">
          <span className="font-bold text-lg" style={{ color: 'var(--text-primary)' }}>
            AI Chef
          </span>
          <IconButton icon="Plus" onClick={handleNewChat} label="新对话" />
        </div>

        {/* Search */}
        <div className="px-3 mb-2">
          <input
            type="text"
            placeholder="搜索对话..."
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-lg px-3 py-2 text-sm outline-none"
            style={{
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-primary)',
              color: 'var(--text-primary)',
            }}
          />
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto px-2">
          {conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => handleSelect(conv.id)}
              className="w-full text-left px-3 py-2 rounded-lg mb-1 truncate transition-colors"
              style={{
                backgroundColor:
                  conv.id === currentConversationId
                    ? 'var(--bg-primary)'
                    : 'transparent',
                color: 'var(--text-primary)',
                borderLeft:
                  conv.id === currentConversationId
                    ? '2px solid var(--accent)'
                    : '2px solid transparent',
              }}
              onMouseEnter={(e) => {
                if (conv.id !== currentConversationId) {
                  e.currentTarget.style.backgroundColor = 'var(--bg-primary)'
                }
              }}
              onMouseLeave={(e) => {
                if (conv.id !== currentConversationId) {
                  e.currentTarget.style.backgroundColor = 'transparent'
                }
              }}
            >
              <div className="text-sm font-medium truncate">{conv.title}</div>
              <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                {formatDistanceToNow(conv.lastUpdated, { addSuffix: true, locale: zhCN })}
              </div>
            </button>
          ))}
        </div>

        {/* Footer */}
        <div
          className="p-3 flex items-center justify-between"
          style={{ borderTop: '1px solid var(--border-color)' }}
        >
          <ThemeToggle />
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium"
            style={{ backgroundColor: 'var(--accent)', color: '#fff' }}
          >
            U
          </div>
        </div>
      </div>
    </>
  )
}
