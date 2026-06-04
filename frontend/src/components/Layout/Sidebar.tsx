import { useState, useRef, useEffect, useMemo } from 'react'
import { isToday, isWithinInterval, subDays, startOfDay } from 'date-fns'
import { PanelLeftClose, MoreHorizontal, Pencil, Trash2, Pin, Plus, Search } from 'lucide-react'
import { useChatStore } from '../../store/useChatStore'
import { useUIStore } from '../../store/useUIStore'
import { ThemeToggle } from '../common/ThemeToggle'
import type { Conversation } from '../../types/chat'

interface GroupedConversations {
  label: string
  items: Conversation[]
}

function groupConversations(conversations: GroupedConversations['items']): GroupedConversations[] {
  const now = new Date()
  const todayStart = startOfDay(now)
  const sevenDaysAgo = subDays(todayStart, 7)
  const thirtyDaysAgo = subDays(todayStart, 30)

  const groups: GroupedConversations[] = [
    { label: '今天', items: [] },
    { label: '7 天内', items: [] },
    { label: '30 天内', items: [] },
    { label: '更早', items: [] },
  ]

  conversations.forEach((conv) => {
    const convDate = new Date(conv.lastUpdated)
    if (isToday(convDate)) {
      groups[0].items.push(conv)
    } else if (isWithinInterval(convDate, { start: sevenDaysAgo, end: todayStart })) {
      groups[1].items.push(conv)
    } else if (isWithinInterval(convDate, { start: thirtyDaysAgo, end: sevenDaysAgo })) {
      groups[2].items.push(conv)
    } else {
      groups[3].items.push(conv)
    }
  })

  return groups.filter((g) => g.items.length > 0)
}

export function Sidebar() {
  const sidebarOpen = useUIStore((s) => s.sidebarOpen)
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen)
  const {
    createNewChat,
    switchConversation,
    deleteConversation,
    renameConversation,
    togglePinConversation,
    setSearchTerm,
    currentConversationId,
    filteredConversations,
  } = useChatStore()

  const [openMenuId, setOpenMenuId] = useState<string | null>(null)
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const conversations = filteredConversations()
  const groupedConversations = useMemo(() => groupConversations(conversations), [conversations])

  const handleNewChat = () => {
    createNewChat()
  }

  const handleSelect = (id: string) => {
    switchConversation(id)
    setSidebarOpen(false)
  }

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    deleteConversation(id)
    setOpenMenuId(null)
  }

  const handlePin = (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    togglePinConversation(id)
    setOpenMenuId(null)
  }

  const handleRenameStart = (id: string, currentTitle: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setRenamingId(id)
    setRenameValue(currentTitle)
    setOpenMenuId(null)
  }

  const handleRenameConfirm = (id: string) => {
    if (renameValue.trim()) {
      renameConversation(id, renameValue.trim())
    }
    setRenamingId(null)
  }

  useEffect(() => {
    if (renamingId && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [renamingId])

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (!target.closest('[data-menu-container]')) {
        setOpenMenuId(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <aside
      className={`
        fixed top-0 left-0 h-full w-[280px] z-30
        flex flex-col
        transform transition-transform duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}
      style={{
        backgroundColor: 'var(--bg-sidebar)',
        borderRight: '1px solid var(--border-color)',
      }}
    >
      {/* Header */}
      <div className="px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg viewBox="0 0 64 64" className="w-7 h-7" fill="none">
            <circle cx="32" cy="32" r="30" fill="#4F6EF7"/>
            <circle cx="24" cy="22" r="8" fill="white"/>
            <circle cx="32" cy="18" r="9" fill="white"/>
            <circle cx="40" cy="22" r="8" fill="white"/>
            <path d="M18 34 C18 20 22 12 32 12 C42 12 46 20 46 34 Z" fill="white"/>
            <rect x="18" y="34" width="28" height="8" rx="2" fill="white"/>
          </svg>
          <span
            className="text-base font-semibold"
            style={{
              color: 'var(--text-primary)',
            }}
          >
            AI Chef
          </span>
        </div>
        <button
          onClick={() => setSidebarOpen(false)}
          className="p-1.5 rounded-lg transition-colors"
          style={{ color: 'var(--text-secondary)' }}
          onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)' }}
          onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-secondary)' }}
        >
          <PanelLeftClose size={18} />
        </button>
      </div>

      {/* New Chat Button */}
      <div className="px-3 mb-2">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg transition-all"
          style={{
            backgroundColor: 'var(--bg-primary)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-primary)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--accent)'
            e.currentTarget.style.color = 'var(--accent)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--border-color)'
            e.currentTarget.style.color = 'var(--text-primary)'
          }}
        >
          <Plus size={16} />
          <span className="text-sm">开启新对话</span>
          <span
            className="text-xs ml-auto"
            style={{ color: 'var(--text-secondary)' }}
          >
            Ctrl + J
          </span>
        </button>
      </div>

      {/* Search */}
      <div className="px-3 mb-1">
        <div
          className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg"
          style={{
            backgroundColor: 'var(--bg-primary)',
            border: '1px solid var(--border-color)',
          }}
        >
          <Search size={14} style={{ color: 'var(--text-secondary)' }} />
          <input
            type="text"
            placeholder="搜索对话..."
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 bg-transparent outline-none text-sm"
            style={{ color: 'var(--text-primary)' }}
          />
        </div>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto px-2 py-1">
        {groupedConversations.map((group) => (
          <div key={group.label} className="mb-2">
            <div
              className="px-2 py-1 text-xs"
              style={{ color: 'var(--text-secondary)' }}
            >
              {group.label}
            </div>
            {group.items.map((conv) => (
              <div
                key={conv.id}
                className="group relative rounded-lg mb-1.5"
                style={{
                  backgroundColor:
                    conv.id === currentConversationId
                      ? 'var(--bg-primary)'
                      : 'transparent',
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
                <button
                  onClick={() => handleSelect(conv.id)}
                  className="w-full text-left px-2 py-2 truncate"
                  style={{ color: 'var(--text-primary)' }}
                >
                  {renamingId === conv.id ? (
                    <input
                      ref={inputRef}
                      value={renameValue}
                      onChange={(e) => setRenameValue(e.target.value)}
                      onBlur={() => handleRenameConfirm(conv.id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleRenameConfirm(conv.id)
                        if (e.key === 'Escape') setRenamingId(null)
                      }}
                      onClick={(e) => e.stopPropagation()}
                      className="w-full text-sm bg-transparent outline-none border-b"
                      style={{ borderColor: 'var(--accent)', color: 'var(--text-primary)' }}
                    />
                  ) : (
                    <div className="flex items-center gap-1.5">
                      {conv.pinned && (
                        <Pin size={11} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                      )}
                      <div className="text-sm truncate">{conv.title}</div>
                    </div>
                  )}
                </button>

                {/* Menu Button */}
                <div
                  data-menu-container
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 z-10"
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setOpenMenuId(openMenuId === conv.id ? null : conv.id)
                    }}
                    className="p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                    style={{ color: 'var(--text-secondary)' }}
                    onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)' }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-secondary)' }}
                  >
                    <MoreHorizontal size={14} />
                  </button>

                  {/* Dropdown Menu */}
                  {openMenuId === conv.id && (
                    <div
                      className="absolute right-0 top-6 w-36 rounded-lg shadow-lg z-50 py-1"
                      style={{
                        backgroundColor: 'var(--bg-secondary)',
                        border: '1px solid var(--border-color)',
                      }}
                    >
                      <button
                        onClick={(e) => handleRenameStart(conv.id, conv.title, e)}
                        className="w-full flex items-center gap-2 px-2.5 py-1.5 text-sm transition-colors"
                        style={{ color: 'var(--text-primary)' }}
                        onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--bg-primary)' }}
                        onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent' }}
                      >
                        <Pencil size={13} />
                        重命名
                      </button>
                      <button
                        onClick={(e) => handlePin(conv.id, e)}
                        className="w-full flex items-center gap-2 px-2.5 py-1.5 text-sm transition-colors"
                        style={{ color: 'var(--text-primary)' }}
                        onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--bg-primary)' }}
                        onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent' }}
                      >
                        <Pin size={13} />
                        {conv.pinned ? '取消置顶' : '置顶'}
                      </button>
                      <div className="my-0.5 border-t" style={{ borderColor: 'var(--border-color)' }} />
                      <button
                        onClick={(e) => handleDelete(conv.id, e)}
                        className="w-full flex items-center gap-2 px-2.5 py-1.5 text-sm transition-colors"
                        style={{ color: '#ef4444' }}
                        onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'var(--bg-primary)' }}
                        onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent' }}
                      >
                        <Trash2 size={13} />
                        删除
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div
        className="px-3 py-2 flex items-center justify-between"
        style={{ borderTop: '1px solid var(--border-color)' }}
      >
        <ThemeToggle />
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center text-xs"
          style={{ backgroundColor: 'var(--accent)', color: '#fff' }}
        >
          U
        </div>
      </div>
    </aside>
  )
}
