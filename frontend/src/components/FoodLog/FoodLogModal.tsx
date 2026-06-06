import { useEffect, useState } from 'react'
import { Activity, X, Plus, Trash2 } from 'lucide-react'
import { useUIStore } from '../../store/useUIStore'
import {
  fetchFoodLog, addFoodEntry, deleteFoodEntry,
  type DaySummary,
} from '../../utils/foodLog'

export function FoodLogModal() {
  const close = () => useUIStore.getState().setFoodLogOpen(false)

  const [data, setData] = useState<DaySummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // 手动添加表单
  const [name, setName] = useState('')
  const [cal, setCal] = useState('')
  const [pro, setPro] = useState('')
  const [carb, setCarb] = useState('')
  const [fat, setFat] = useState('')

  useEffect(() => {
    let active = true
    fetchFoodLog()
      .then((d) => { if (active) { setData(d); setError(null) } })
      .catch(() => { if (active) setError('无法连接后端，请确认服务已启动') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  const handleAdd = async () => {
    if (!name.trim() || busy) return
    setBusy(true)
    try {
      const d = await addFoodEntry({
        name: name.trim(),
        calories: Number(cal) || 0,
        protein: Number(pro) || 0,
        carbs: Number(carb) || 0,
        fat: Number(fat) || 0,
      })
      setData(d)
      setName(''); setCal(''); setPro(''); setCarb(''); setFat('')
      setError(null)
    } catch {
      setError('添加失败')
    } finally {
      setBusy(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (busy) return
    setBusy(true)
    try {
      setData(await deleteFoodEntry(id))
    } catch {
      setError('删除失败')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={close}>
      <div
        className="w-full max-w-md max-h-[85vh] flex flex-col rounded-2xl overflow-hidden"
        style={{ backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-4 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border-color)' }}>
          <h3 className="flex items-center gap-2 text-base font-bold" style={{ color: 'var(--text-primary)' }}>
            <Activity size={18} style={{ color: 'var(--accent)' }} />
            今日进度
          </h3>
          <button onClick={close} className="p-1 rounded-lg" style={{ color: 'var(--text-secondary)' }} aria-label="关闭">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {loading ? (
            <p className="text-sm py-4" style={{ color: 'var(--text-secondary)' }}>加载中…</p>
          ) : !data ? (
            <p className="text-sm py-4" style={{ color: 'var(--accent-red, #ef4444)' }}>{error}</p>
          ) : (
            <>
              {/* 进度条 */}
              {data.targets ? (
                <div className="space-y-3 mb-4">
                  <Bar label="🔥 热量" consumed={data.totals.calories} target={data.targets.calories} unit="kcal" color="var(--accent)" />
                  <Bar label="🍗 蛋白" consumed={data.totals.protein} target={data.targets.protein} unit="g" color="#22c55e" />
                  <Bar label="🍚 碳水" consumed={data.totals.carbs} target={data.targets.carbs} unit="g" color="#f59e0b" />
                  <Bar label="🥑 脂肪" consumed={data.totals.fat} target={data.targets.fat} unit="g" color="#a855f7" />
                </div>
              ) : (
                <p className="text-xs mb-4" style={{ color: 'var(--text-secondary)' }}>
                  今日已摄入：{data.totals.calories} kcal / 蛋白 {data.totals.protein}g。
                  去「健身档案」设置目标后，这里会显示进度条。
                </p>
              )}

              {/* 今日列表 */}
              <div className="text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>
                今日记录（{data.entries.length}）
              </div>
              {data.entries.length === 0 ? (
                <p className="text-sm mb-3" style={{ color: 'var(--text-secondary)' }}>还没有记录，下面添加，或在菜谱卡点「记录」。</p>
              ) : (
                <div className="space-y-1 mb-4">
                  {data.entries.map((e) => (
                    <div key={e.id} className="flex items-center gap-2 px-3 py-2 rounded-lg" style={{ backgroundColor: 'var(--bg-secondary)' }}>
                      <span className="flex-1 text-sm truncate" style={{ color: 'var(--text-primary)' }}>{e.name}</span>
                      <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                        {e.calories}kcal · 蛋{e.protein}
                      </span>
                      <button onClick={() => handleDelete(e.id)} disabled={busy} className="p-1 rounded disabled:opacity-40" style={{ color: 'var(--text-secondary)' }} aria-label="删除">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* 手动添加 */}
              <div className="text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>手动添加</div>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="食物名称，如 水煮蛋"
                className="w-full px-3 py-2 mb-2 rounded-lg text-sm bg-transparent outline-none"
                style={{ border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
              />
              <div className="grid grid-cols-4 gap-2 mb-2">
                <MiniNum value={cal} onChange={setCal} ph="热量" />
                <MiniNum value={pro} onChange={setPro} ph="蛋白" />
                <MiniNum value={carb} onChange={setCarb} ph="碳水" />
                <MiniNum value={fat} onChange={setFat} ph="脂肪" />
              </div>
              {error && <p className="text-sm mb-2" style={{ color: 'var(--accent-red, #ef4444)' }}>{error}</p>}
              <button
                onClick={handleAdd}
                disabled={busy || !name.trim()}
                className="w-full flex items-center justify-center gap-1 py-2 rounded-lg text-sm font-medium transition-all disabled:opacity-40"
                style={{ backgroundColor: 'var(--accent)', color: '#fff' }}
              >
                <Plus size={16} /> 添加到今日
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function Bar({ label, consumed, target, unit, color }: { label: string; consumed: number; target: number; unit: string; color: string }) {
  const pct = target > 0 ? Math.min(100, Math.round((consumed / target) * 100)) : 0
  const over = target > 0 && consumed > target
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span style={{ color: 'var(--text-primary)' }}>{label}</span>
        <span style={{ color: over ? 'var(--accent-red, #ef4444)' : 'var(--text-secondary)' }}>
          {consumed} / {target} {unit}
        </span>
      </div>
      <div className="h-2 rounded-full overflow-hidden" style={{ backgroundColor: 'var(--bg-secondary)' }}>
        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: over ? 'var(--accent-red, #ef4444)' : color }} />
      </div>
    </div>
  )
}

function MiniNum({ value, onChange, ph }: { value: string; onChange: (v: string) => void; ph: string }) {
  return (
    <input
      type="number"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={ph}
      className="w-full px-2 py-2 rounded-lg text-sm bg-transparent outline-none"
      style={{ border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
    />
  )
}
