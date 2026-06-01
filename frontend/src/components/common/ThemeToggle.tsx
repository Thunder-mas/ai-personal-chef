import { Moon, Sun } from 'lucide-react'
import { useChatStore } from '../../store/useChatStore'

export function ThemeToggle() {
  const { darkMode, toggleDarkMode } = useChatStore()

  return (
    <button
      onClick={toggleDarkMode}
      aria-label="Toggle theme"
      className="p-2 rounded-lg transition-colors hover:bg-[var(--bg-primary)]"
      style={{ color: 'var(--text-secondary)' }}
    >
      {darkMode ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  )
}
