import { useEffect, useState } from 'react'
import { Dumbbell, X } from 'lucide-react'
import { useUIStore } from '../../store/useUIStore'
import { fetchFitnessProfile, saveFitnessProfile, type FitnessTargets } from '../../utils/fitness'

const GENDERS = ['男', '女']
const ACTIVITIES = ['久坐', '轻度', '中度', '高度', '极高']
const GOALS = ['减脂', '维持', '增肌']

export function FitnessModal() {
  const close = () => useUIStore.getState().setFitnessOpen(false)

  const [gender, setGender] = useState('男')
  const [age, setAge] = useState('25')
  const [height, setHeight] = useState('175')
  const [weight, setWeight] = useState('70')
  const [activity, setActivity] = useState('中度')
  const [goal, setGoal] = useState('增肌')

  const [targets, setTargets] = useState<FitnessTargets | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let active = true
    fetchFitnessProfile()
      .then(({ profile, targets }) => {
        if (!active) return
        if (profile) {
          setGender(profile.gender)
          setAge(String(profile.age))
          setHeight(String(profile.height_cm))
          setWeight(String(profile.weight_kg))
          setActivity(profile.activity_level)
          setGoal(profile.goal)
        }
        setTargets(targets)
        setError(null)
      })
      .catch(() => { if (active) setError('无法连接后端，请确认服务已启动') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  const handleSave = async () => {
    if (busy) return
    setBusy(true)
    try {
      const { targets } = await saveFitnessProfile({
        gender,
        age: Number(age),
        height_cm: Number(height),
        weight_kg: Number(weight),
        activity_level: activity,
        goal,
      })
      setTargets(targets)
      setError(null)
    } catch {
      setError('保存失败')
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
            <Dumbbell size={18} style={{ color: 'var(--accent)' }} />
            健身档案
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
          <p className="text-xs mb-4" style={{ color: 'var(--text-secondary)' }}>
            填好后，切换到 💪 健身模式，AI 会按你的每日营养目标推荐高蛋白菜谱。
          </p>

          {loading ? (
            <p className="text-sm py-4" style={{ color: 'var(--text-secondary)' }}>加载中…</p>
          ) : (
            <div className="space-y-3">
              {/* 性别 + 目标（选择按钮组） */}
              <Field label="性别">
                <Segmented options={GENDERS} value={gender} onChange={setGender} />
              </Field>
              <Field label="目标">
                <Segmented options={GOALS} value={goal} onChange={setGoal} />
              </Field>

              {/* 年龄 / 身高 / 体重 */}
              <div className="grid grid-cols-3 gap-2">
                <NumField label="年龄" value={age} onChange={setAge} unit="岁" />
                <NumField label="身高" value={height} onChange={setHeight} unit="cm" />
                <NumField label="体重" value={weight} onChange={setWeight} unit="kg" />
              </div>

              {/* 活动量 */}
              <Field label="活动量">
                <Segmented options={ACTIVITIES} value={activity} onChange={setActivity} />
              </Field>

              {error && <p className="text-sm" style={{ color: 'var(--accent-red, #ef4444)' }}>{error}</p>}

              <button
                onClick={handleSave}
                disabled={busy}
                className="w-full py-2.5 rounded-lg text-sm font-medium transition-all disabled:opacity-40"
                style={{ backgroundColor: 'var(--accent)', color: '#fff' }}
              >
                {busy ? '保存中…' : '保存并计算每日目标'}
              </button>

              {/* 每日目标展示 */}
              {targets && (
                <div className="mt-2 p-3 rounded-xl" style={{ backgroundColor: 'var(--bg-secondary)' }}>
                  <div className="text-xs mb-2" style={{ color: 'var(--text-secondary)' }}>
                    🎯 {targets.goal} · 每日营养目标
                  </div>
                  <div className="flex gap-2">
                    {[
                      { label: '热量', value: targets.calories, unit: 'kcal', emoji: '🔥' },
                      { label: '蛋白', value: targets.protein, unit: 'g', emoji: '🍗' },
                      { label: '碳水', value: targets.carbs, unit: 'g', emoji: '🍚' },
                      { label: '脂肪', value: targets.fat, unit: 'g', emoji: '🥑' },
                    ].map((n) => (
                      <div key={n.label} className="flex-1 text-center px-1 py-1.5 rounded-lg" style={{ backgroundColor: 'var(--bg-primary)' }}>
                        <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>{n.emoji} {n.label}</div>
                        <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                          {n.value}<span className="text-xs font-normal" style={{ color: 'var(--text-secondary)' }}>{n.unit}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs mb-1.5" style={{ color: 'var(--text-secondary)' }}>{label}</label>
      {children}
    </div>
  )
}

function NumField({ label, value, onChange, unit }: { label: string; value: string; onChange: (v: string) => void; unit: string }) {
  return (
    <div>
      <label className="block text-xs mb-1.5" style={{ color: 'var(--text-secondary)' }}>{label}</label>
      <div className="flex items-center rounded-lg px-2" style={{ border: '1px solid var(--border-color)' }}>
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full py-2 bg-transparent outline-none text-sm"
          style={{ color: 'var(--text-primary)' }}
        />
        <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{unit}</span>
      </div>
    </div>
  )
}

function Segmented({ options, value, onChange }: { options: string[]; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex gap-1 flex-wrap">
      {options.map((opt) => {
        const active = opt === value
        return (
          <button
            key={opt}
            onClick={() => onChange(opt)}
            className="px-3 py-1.5 rounded-lg text-sm transition-colors"
            style={active
              ? { backgroundColor: 'var(--accent)', color: '#fff' }
              : { backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}
          >
            {opt}
          </button>
        )
      })}
    </div>
  )
}
