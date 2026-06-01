import { Plus, Search, Trash2, Menu, X } from 'lucide-react'

const iconMap = {
  Plus,
  Search,
  Trash2,
  Menu,
  X,
} as const

interface IconButtonProps {
  icon: keyof typeof iconMap
  onClick: () => void
  label: string
  className?: string
}

export function IconButton({ icon, onClick, label, className = '' }: IconButtonProps) {
  const Icon = iconMap[icon]
  return (
    <button
      onClick={onClick}
      aria-label={label}
      className={`p-2 rounded-lg transition-colors hover:bg-[var(--bg-primary)] ${className}`}
      style={{ color: 'var(--text-secondary)' }}
    >
      <Icon size={18} />
    </button>
  )
}
