// ============================================
// Lumina 墨光 · D-06 学习广场
// 自主学习与闯关奖励系统 · 入口页
// ============================================
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { get, post } from '../api/client'
import type { LearningPath, MyXpSummary, CheckInResult, DailyChallenge } from '../api/types'
import { track } from '../utils/tracker'

type Category = '全部' | '编程' | '设计' | '语言' | '通识'
type Difficulty = '全部' | '入门' | '进阶' | '挑战'
type SortKey = '热门' | '最新' | '推荐'

interface PathListResp {
  code: number
  data: LearningPath[]
  pagination: { offset: number; limit: number; total: number; has_more: boolean }
}

export default function LearningPlaza() {
  const navigate = useNavigate()
  const [paths, setPaths] = useState<LearningPath[]>([])
  const [xp, setXp] = useState<MyXpSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [checkedToday, setCheckedToday] = useState(false)
  const [category, setCategory] = useState<Category>('全部')
  const [difficulty, setDifficulty] = useState<Difficulty>('全部')
  const [sort, setSort] = useState<SortKey>('热门')

  useEffect(() => {
    ;(async () => {
      try {
        const [pathsRes, xpRes] = await Promise.all([
          get<PathListResp>('/learning/paths?limit=50'),
          get<MyXpSummary>('/learning/my/xp').catch(() => null),
        ])
        setPaths(pathsRes.data ?? [])
        setXp(xpRes)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  async function handleCheckIn() {
    if (checkedToday) return
    try {
      const res = await post<CheckInResult>('/learning/checkin', {})
      setCheckedToday(true)
      if (res.checked_in && xp) {
        setXp({ ...xp, total_xp: xp.total_xp + res.xp_earned, current_streak: res.new_streak })
      }
      track('learning.daily_checkin', { xp_earned: res.xp_earned, streak: res.new_streak })
    } catch (err) {
      console.error('打卡失败', err)
    }
  }

  if (loading) return <div className="muted">加载中…</div>

  // 筛选路径
  const filtered = paths.filter((p) => {
    if (category !== '全部' && p.category !== category) return false
    if (difficulty !== '全部' && p.difficulty !== difficulty) return false
    return true
  })

  // 排序
  const sorted = [...filtered].sort((a, b) => {
    if (sort === '热门') return b.learner_count - a.learner_count
    if (sort === '最新') return new Date(b.created_by).getTime() - new Date(a.created_by).getTime()
    // 推荐：有进度优先，然后按学习人数
    return (b.my_progress ?? 0) - (a.my_progress ?? 0) || b.learner_count - a.learner_count
  })

  return (
    <div>
      {/* Hero 横幅 */}
      <section className="learning-hero">
        <div className="learning-hero-left">
          <h1 className="page-title" style={{ marginBottom: 0 }}>
            学习<em>广场</em>
          </h1>
          <p className="muted" style={{ marginTop: 4 }}>选择一个路径，像闯关一样完成自主学习 · 每关都有 XP 与徽章奖励</p>
        </div>
        <div className="learning-hero-right">
          {xp && (
            <>
              <div className="xp-badge">
                <div className="xp-value">{xp.total_xp.toLocaleString()}</div>
                <div className="xp-label">累计 XP</div>
              </div>
              <div className="streak-box">
                <div className="streak-value">🔥 {xp.current_streak} 天</div>
                <div className="streak-label">连续打卡</div>
              </div>
            </>
          )}
          <button
            className={`btn gold lg ${checkedToday ? 'checked' : ''}`}
            onClick={handleCheckIn}
            disabled={checkedToday}
          >
            {checkedToday ? '✅ 已打卡' : '📅 今日打卡'}
          </button>
        </div>
      </section>

      {/* 筛选栏 */}
      <section className="filterbar">
        <FilterGroup label="分类" value={category} options={['全部', '编程', '设计', '语言', '通识']} onChange={(v) => setCategory(v as Category)} />
        <FilterGroup label="难度" value={difficulty} options={['全部', '入门', '进阶', '挑战']} onChange={(v) => setDifficulty(v as Difficulty)} />
        <FilterGroup label="排序" value={sort} options={['热门', '最新', '推荐']} onChange={(v) => setSort(v as SortKey)} />
      </section>

      {/* 路径网格 + 侧栏 */}
      <section className="plaza-layout">
        <div className="path-grid">
          {sorted.map((p) => (
            <PathCard key={p.id} path={p} onClick={() => navigate(`/learning/paths/${p.id}`)} />
          ))}
          {sorted.length === 0 && <div className="empty-hint">该筛选组合下暂无路径，试试切换分类或难度</div>}
        </div>

        <aside className="plaza-sidebar">
          {/* 今日挑战 */}
          <div className="challenge-card">
            <div className="challenge-tag">⚡ 今日挑战 · 限时 24h</div>
            <div className="challenge-question">
              Python：以下哪个不是不可变类型？
              <div className="challenge-options">A. tuple&nbsp;&nbsp;B. str&nbsp;&nbsp;C. list&nbsp;&nbsp;D. frozenset</div>
            </div>
            <div className="challenge-hint">
              答对得 <span className="xp-hl">+20 XP</span>，答错不扣分
            </div>
            <button className="btn primary" onClick={() => navigate('/learning/challenges/today')}>
              立即作答
            </button>
          </div>

          {/* 继续学习 */}
          {xp && paths.find((p) => p.my_progress && p.my_progress > 0) && (
            <div className="continue-card">
              <div className="continue-label">▶ 继续学习</div>
              <div className="continue-name">
                {paths.find((p) => p.my_progress && p.my_progress > 0)?.title}
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${paths.find((p) => p.my_progress && p.my_progress > 0)?.my_progress ?? 0}%` }} />
              </div>
              <div className="continue-meta">
                <span>{paths.find((p) => p.my_progress && p.my_progress > 0)?.my_progress}% 完成</span>
                <button className="btn primary tiny" onClick={() => {
                  const p = paths.find((p) => p.my_progress && p.my_progress > 0)
                  if (p) navigate(`/learning/paths/${p.id}`)
                }}>
                  继续 →
                </button>
              </div>
            </div>
          )}
        </aside>
      </section>

      <div className="compliance-hint">
        ⚖️ 学习路径推荐基于你的学习行为生成，可在「设置 → 隐私」中关闭个性化推荐
      </div>
    </div>
  )
}

function FilterGroup({ label, value, options, onChange }: {
  label: string
  value: string
  options: string[]
  onChange: (v: string) => void
}) {
  return (
    <div className="filter-group">
      <span className="filter-label">{label}</span>
      {options.map((opt) => (
        <button
          key={opt}
          className={`chip ${value === opt ? 'on' : ''}`}
          onClick={() => onChange(opt)}
        >
          {opt}
        </button>
      ))}
    </div>
  )
}

function PathCard({ path, onClick }: { path: LearningPath; onClick: () => void }) {
  const diffPillClass = path.difficulty === '入门' ? 'green' : path.difficulty === '进阶' ? 'cobalt' : 'red'

  return (
    <div className="card path-card" onClick={onClick}>
      <div className="path-cover" style={{ background: getGradient(path.category) }}>
        <span className="path-glyph">{getGlyph(path.category)}</span>
        <span className={`pill diff ${diffPillClass}`}>{path.difficulty}</span>
      </div>
      <div className="path-body">
        <div className="path-title">{path.title}</div>
        <div className="path-desc">
          {path.stage_count} 个关卡串联文章、视频、测验与挑战，完成全部关卡即可获得路径徽章与 {path.total_xp} XP 总奖励。
        </div>
        <div className="path-tags">
          <span className="pill gray">{path.category}</span>
          <span className={`pill ${diffPillClass}`}>{path.difficulty}</span>
          <span className="pill yellow">{path.stage_count} 关</span>
        </div>
        <div className="path-footer">
          <span className="xp-hl">{path.total_xp} XP</span>
          <span className="pill gray small">{path.learner_count} 人学习</span>
        </div>
        {path.my_progress !== null && path.my_progress !== undefined && path.my_progress > 0 ? (
          <>
            <div className="progress-bar" style={{ marginTop: 10 }}>
              <div className="progress-fill" style={{ width: `${path.my_progress}%` }} />
            </div>
            <div className="path-meta">
              <span>我的进度</span>
              <span>{path.my_progress}%</span>
            </div>
          </>
        ) : (
          <div className="path-meta" style={{ marginTop: 10 }}>
            <span>尚未开始</span>
            <span>点击开始 →</span>
          </div>
        )}
      </div>
    </div>
  )
}

function getGlyph(category: string): string {
  const glyphs: Record<string, string> = {
    '编程': '🐍',
    '设计': '🎨',
    '语言': '✍️',
    '通识': '🧠',
  }
  return glyphs[category] ?? '📚'
}

function getGradient(category: string): string {
  const gradients: Record<string, string> = {
    '编程': 'linear-gradient(135deg,#3D46C9,#7C3AED)',
    '设计': 'linear-gradient(135deg,#E85D3A,#F5B800)',
    '语言': 'linear-gradient(135deg,#2A7F4F,#94C97A)',
    '通识': 'linear-gradient(135deg,#1F7A8C,#2A7F4F)',
  }
  return gradients[category] ?? 'linear-gradient(135deg,#3D46C9,#7C3AED)'
}
