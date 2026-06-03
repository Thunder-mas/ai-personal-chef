import { useState, useEffect } from 'react'
import { Menu } from 'lucide-react'
import { Sidebar } from './components/Layout/Sidebar'
import { MainArea } from './components/Layout/MainArea'
import { useChatStore } from './store/useChatStore'

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { darkMode, createNewChat } = useChatStore()

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
  }, [darkMode])

  useEffect(() => {
    const convs = useChatStore.getState().conversations
    if (convs.length === 0) {
      createNewChat()
    }
  }, [])

  return (
    <div
      className="flex h-screen w-screen overflow-hidden"
      style={{ backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)' }}
    >
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col min-w-0 h-full">
        {/* Header bar */}
        <div
          className="flex items-center px-4 py-3"
          style={{ borderBottom: '1px solid var(--border-color)' }}
        >
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg md:hidden"
            style={{ color: 'var(--text-secondary)' }}
          >
            <Menu size={20} />
          </button>
          <span className="ml-1 md:ml-0 font-bold text-lg" style={{ color: 'var(--text-primary)' }}>
            AI Chef
          </span>
        </div>

        <MainArea />
      </div>
    </div>
  )
}

export default App
