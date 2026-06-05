import { useEffect, useState } from 'react'
import { SlidersHorizontal, X, Plus, Trash2 } from 'lucide-react'
import { useUIStore } from '../../store/useUIStore'
import { fetchPreferences, addPreference, deletePreference } from '../../utils/preferences'

export function PreferencesModal() {
  const close = () => useUIStore.getState().setPreferencesOpen(false)

  const [prefs, setPrefs] = useState<string[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let active = true
    fetchPreferences()
      .then((p) => { if (active) { setPrefs(p); setError(null) } })
      .catch(() => { if (active) setError('无法连接后端，请确认服务已启动') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  const handleAdd = async () => {
    const text = input.trim()
    if (!text || busy) return
    setBusy(true)
    try {
      setPrefs(await addPreference(text))
      setInput('')
      setError(null)
    } catch {
      setError('添加失败')
    } finally {
      setBusy(false)
    }
  }

  const handleDelete = async (p: string) => {
    if (busy) return
    setBusy(true)
    try {
      setPrefs(await deletePreference(p))
      setError(null)
    } catch {
      setError('删除失败')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={close}
    >
      <div
        className="w-full max-w-md max-h-[80vh] flex flex-col rounded-2xl overflow-hidden"
        style={{ backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="px-5 py-4 flex items-center justify-between"
          style={{ borderBottom: '1px solid var(--border-color)' }}
        >
          <h3 className="flex items-center gap-2 text-base font-bold" style={{ color: 'var(--text-primary)' }}>
            <SlidersHorizontal size={18} style={{ color: 'var(--accent)' }} />
            口味偏好
          </h3>
          <button
            onClick={close}
            className="p-1 rounded-lg transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)' }}
            onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-secondary)' }}
            aria-label="关闭"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          <p className="text-xs mb-3" style={{ color: 'var(--text-secondary)' }}>
            这些偏好会在每次推荐时自动生效。也可以直接在对话里说"我不吃香菜""对花生过敏"，AI 会自动记录。
          </p>

          {/* 手动添加 */}
          <div className="flex gap-2 mb-4">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleAdd() }}
              placeholder="如：不吃香菜 / 喜欢清淡"
              className="flex-1 px-3 py-2 rounded-lg text-sm bg-transparent outline-none"
              style={{ border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
            />
            <button
              onClick={handleAdd}
              disabled={busy || !input.trim()}
              className="flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium transition-all disabled:opacity-40"
              style={{ backgroundColor: 'var(--accent)', color: '#fff' }}
            >
              <Plus size={16} />
              添加
            </button>
          </div>

          {error && (
            <p className="text-sm mb-3" style={{ color: 'var(--accent-red)' }}>{error}</p>
          )}

          {/* 列表 */}
          {loading ? (
            <p className="text-sm py-4" style={{ color: 'var(--text-secondary)' }}>加载中…</p>
          ) : prefs.length === 0 && !error ? (
            <div className="px-2 py-8 text-center">
              <SlidersHorizontal size={32} className="mx-auto mb-2" style={{ color: 'var(--text-secondary)', opacity: 0.4 }} />
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>还没有记录任何偏好</p>
            </div>
          ) : (
            <div className="space-y-1">
              {prefs.map((p) => (
                <div
                  key={p}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg"
                  style={{ backgroundColor: 'var(--bg-secondary)' }}
                >
                  <span className="flex-1 text-sm" style={{ color: 'var(--text-primary)' }}>{p}</span>
                  <button
                    onClick={() => handleDelete(p)}
                    disabled={busy}
                    className="p-1 rounded transition-colors disabled:opacity-40"
                    style={{ color: 'var(--text-secondary)' }}
                    onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent-red)' }}
                    onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-secondary)' }}
                    aria-label="删除"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
