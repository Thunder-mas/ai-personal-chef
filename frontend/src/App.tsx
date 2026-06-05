import { useEffect } from 'react'
import { PanelLeft, Search, Plus } from 'lucide-react'
import { Sidebar } from './components/Layout/Sidebar'
import { MainArea } from './components/Layout/MainArea'
import { ShoppingListModal } from './components/ShoppingList/ShoppingListModal'
import { PreferencesModal } from './components/Preferences/PreferencesModal'
import { useChatStore } from './store/useChatStore'
import { useUIStore } from './store/useUIStore'

function App() {
  const sidebarOpen = useUIStore((s) => s.sidebarOpen)
  const toggleSidebar = useUIStore((s) => s.toggleSidebar)
  const setSidebarOpen = useUIStore((s) => s.setSidebarOpen)
  const shoppingListOpen = useUIStore((s) => s.shoppingListOpen)
  const preferencesOpen = useUIStore((s) => s.preferencesOpen)
  const darkMode = useChatStore((s) => s.darkMode)
  const createNewChat = useChatStore((s) => s.createNewChat)
  const conversations = useChatStore((s) => s.conversations)
  const currentConversationId = useChatStore((s) => s.currentConversationId)
  const currentConv = conversations.find((c) => c.id === currentConversationId)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
  }, [darkMode])

  useEffect(() => {
    const convs = useChatStore.getState().conversations
    if (convs.length === 0) {
      useChatStore.getState().createNewChat()
    }
  }, [])

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) setSidebarOpen(false)
      else setSidebarOpen(true)
    }
    window.addEventListener('resize', handleResize)
    handleResize()
    return () => window.removeEventListener('resize', handleResize)
  }, [setSidebarOpen])

  return (
    <div
      className="relative h-screen w-screen overflow-hidden"
      style={{ backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)' }}
    >
      <Sidebar />

      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-20 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Content Area */}
      <div
        className="flex flex-col h-full transition-all duration-300"
        style={{
          marginLeft: sidebarOpen ? '280px' : '0',
        }}
      >
        {/* Header Bar - shows when sidebar is collapsed */}
        {!sidebarOpen && (
          <div
            className="flex items-center gap-3 px-4 pt-2 pb-3"
            style={{
              borderBottom: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-primary)',
            }}
          >
            <button
              onClick={toggleSidebar}
              className="p-1.5 rounded-lg transition-colors"
              style={{ color: 'var(--text-secondary)' }}
              onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)' }}
              onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-secondary)' }}
            >
              <PanelLeft size={18} />
            </button>
            <svg viewBox="0 0 64 64" className="w-6 h-6" fill="none">
              <circle cx="32" cy="32" r="30" fill="#4F6EF7"/>
              <circle cx="24" cy="22" r="8" fill="white"/>
              <circle cx="32" cy="18" r="9" fill="white"/>
              <circle cx="40" cy="22" r="8" fill="white"/>
              <path d="M18 34 C18 20 22 12 32 12 C42 12 46 20 46 34 Z" fill="white"/>
              <rect x="18" y="34" width="28" height="8" rx="2" fill="white"/>
            </svg>
            <button
              onClick={toggleSidebar}
              className="p-1.5 rounded-lg transition-colors"
              style={{ color: 'var(--text-secondary)' }}
              onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)' }}
              onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-secondary)' }}
            >
              <Search size={18} />
            </button>
            <button
              onClick={createNewChat}
              className="p-1.5 rounded-lg transition-colors"
              style={{ color: 'var(--text-secondary)' }}
              onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)' }}
              onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-secondary)' }}
            >
              <Plus size={18} />
            </button>
            {currentConv && (
              <div className="flex-1 truncate text-sm" style={{ color: 'var(--text-primary)' }}>
                {currentConv.title}
              </div>
            )}
          </div>
        )}

        <MainArea />
      </div>

      {shoppingListOpen && <ShoppingListModal />}
      {preferencesOpen && <PreferencesModal />}
    </div>
  )
}

export default App
