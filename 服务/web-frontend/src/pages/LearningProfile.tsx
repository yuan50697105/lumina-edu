// ============================================
// Lumina 墨光 · D-06 成就中心
// 自主学习与闯关奖励系统 · 成长档案
// ============================================
import { useEffect, useState } from 'react'
import { get } from '../api/client'
import type { MyXpSummary, Badge, CheckInDay, LearningStats } from '../api/types'

interface CheckInCalendarResp {
  days: CheckInDay[]
  current_streak: number
  longest_streak: number
}

export default function LearningProfile() {
  const [xp, setXp] = useState<MyXpSummary | null>(null)
  const [badges, setBadges] = useState<Badge[]>([])
  const [calendar, setCalendar] = useState<CheckInDay[]>([])
  const [stats, setStats] = useState<LearningStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    ;(async () => {
      try {
        const [xpRes, badgesRes, calendarRes, statsRes] = await Promise.all([
          get<MyXpSummary>('/learning/my/xp'),
          get<Badge[]>('/learning/badges'),
          get<CheckInCalendarResp>('/learning/checkin/calendar?month=current'),
          get<LearningStats>('/learning/stats').catch(() => null),
        ])
        setXp(xpRes)
        setBadges(badgesRes ?? [])
        setCalendar(calendarRes.days ?? [])
        setStats(statsRes)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  if (loading) return <div className="muted">加载中…</div>

  const earnedBadges = badges.filter((b) => b.earned)
  const lockedBadges = badges.filter((b) => !b.earned)

  return (
    <div>
      {/* 个人信息条 */}
      <section className="card profile-top">
        <div className="avatar-xl">
          {xp ? getTierIcon(xp.tier_name) : '🎓'}
        </div>
        <div className="profile-info">
          <div className="profile-name">
            学习者
            {xp && <span className={`tier t${xp.level <= 4 ? 1 : xp.level <= 9 ? 2 : xp.level <= 19 ? 3 : xp.level <= 29 ? 4 : xp.level <= 49 ? 5 : 6}`}>
              {getTierIcon(xp.tier_name)} Lv.{xp.level} {xp.tier_name}
            </span>}
          </div>
          {xp && (
            <div className="level-bar">
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${getLevelProgress(xp)}%` }} />
              </div>
              <div className="level-cap">
                <span>{xp.total_xp.toLocaleString()} XP</span>
                <span>距 Lv.{xp.level + 1} 还需 {(xp.next_level_xp - xp.total_xp).toLocaleString()} XP</span>
              </div>
            </div>
          )}
        </div>
        <button className="btn" onClick={() => alert('原型演示：编辑个人资料')}>
          编辑资料
        </button>
      </section>

      {/* 统计卡网格 */}
      <section className="stat-grid">
        <div className="card stat-card">
          <div className="stat-label">累计 XP</div>
          <div className="stat-value">
            <span className="xp-hl">{xp?.total_xp.toLocaleString() ?? '0'}</span>
          </div>
          <div className="stat-foot">本周 +{stats ? Math.round(stats.total_study_hours * 100) : 0} · 超过 {stats?.rank_percentile ?? 0}% 同学</div>
        </div>
        <div className="card stat-card">
          <div className="stat-label">连续打卡</div>
          <div className="stat-value">🔥 {xp?.current_streak ?? 0}<span className="stat-unit">天</span></div>
          <div className="stat-foot">历史最长 {xp?.longest_streak ?? 0} 天</div>
        </div>
        <div className="card stat-card">
          <div className="stat-label">完成路径</div>
          <div className="stat-value">{stats?.paths_completed ?? 0}<span className="stat-unit">个</span></div>
          <div className="stat-foot">进行中 0 个</div>
        </div>
        <div className="card stat-card">
          <div className="stat-label">获得徽章</div>
          <div className="stat-value">{earnedBadges.length}<span className="stat-unit">/ {badges.length}</span></div>
          <div className="stat-foot">还差 {lockedBadges.length} 枚集齐</div>
        </div>
      </section>

      {/* 打卡日历 + 徽章墙 */}
      <section className="ach-layout">
        {/* 打卡日历 */}
        <div className="card cal-card">
          <div className="cal-head">
            <div className="cal-month">近 30 天打卡</div>
            <div className="pill yellow">🔥 当前连续 {xp?.current_streak ?? 0} 天</div>
          </div>
          <div className="cal-grid">
            {['日', '一', '二', '三', '四', '五', '六'].map((wd) => (
              <div key={wd} className="cal-weekday">{wd}</div>
            ))}
            {renderCalendarDays(calendar)}
          </div>
          <div className="cal-legend">
            <span><i className="legend-dot checked" />已打卡</span>
            <span><i className="legend-dot today" />今日</span>
            <span><i className="legend-dot unchecked" />未打卡</span>
          </div>
        </div>

        {/* 徽章墙 */}
        <div className="card badge-wall">
          <div className="sec-title">
            徽章墙 <span className="sub">{earnedBadges.length} / {badges.length} 已获得</span>
          </div>
          <div className="badge-grid">
            {badges.map((badge) => (
              <div key={badge.id} className={`badge-cell ${badge.earned ? 'earned' : 'locked'}`}>
                <div className="badge-icon">{badge.icon}</div>
                <div className="badge-name">{badge.name}</div>
                <div className="badge-tip">
                  <b>{badge.icon} {badge.name}</b>
                  {badge.earned
                    ? `${badge.description}${badge.earned_at ? `<br>获得于 ${badge.earned_at}` : ''}`
                    : `🔒 ${badge.description}`
                  }
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="compliance-hint">
        ⚖️ 你的成就数据仅本人、授课教师与管理员可见；成绩信息受《个人信息保护法》保护，可在
        <a onClick={() => alert('原型演示：跳转隐私设置')}>个人中心 → 隐私</a> 查看与更正
      </div>
    </div>
  )
}

function renderCalendarDays(days: CheckInDay[]) {
  const today = new Date()
  const todayStr = today.toISOString().split('T')[0]

  // 生成 30 天的日历（从 29 天前到今天，再加 5 天未来）
  const calendarDays: { date: string; checked: boolean; isToday: boolean; isFuture: boolean }[] = []

  for (let i = 29; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    const dateStr = d.toISOString().split('T')[0]
    const dayData = days.find((day) => day.date === dateStr)
    calendarDays.push({
      date: dateStr,
      checked: dayData?.checked ?? false,
      isToday: dateStr === todayStr,
      isFuture: false,
    })
  }

  // 添加未来 5 天
  for (let i = 1; i <= 5; i++) {
    const d = new Date(today)
    d.setDate(d.getDate() + i)
    const dateStr = d.toISOString().split('T')[0]
    calendarDays.push({
      date: dateStr,
      checked: false,
      isToday: false,
      isFuture: true,
    })
  }

  // 计算第一天是周几，填充空白
  const firstDay = new Date(today)
  firstDay.setDate(firstDay.getDate() - 29)
  const startWeekday = firstDay.getDay()

  const elements: JSX.Element[] = []

  // 填充空白
  for (let i = 0; i < startWeekday; i++) {
    elements.push(<div key={`pad-${i}`} className="cal-day pad" />)
  }

  // 填充日期
  calendarDays.forEach((day, idx) => {
    const dateNum = new Date(day.date).getDate()
    const classes = ['cal-day']
    if (day.checked) classes.push('on')
    if (day.isToday) classes.push('today')
    if (day.isFuture) classes.push('future')

    elements.push(
      <div key={day.date} className={classes.join(' ')} title={`${day.date}${day.checked ? ' · 已打卡' : ''}`}>
        {dateNum}
      </div>
    )
  })

  return elements
}

function getLevelProgress(xp: MyXpSummary): number {
  // 简化计算：假设每级需要 100 * level XP
  const currentLevelMin = xp.level * 100
  const nextLevelMin = xp.next_level_xp
  const progress = ((xp.total_xp - currentLevelMin) / (nextLevelMin - currentLevelMin)) * 100
  return Math.max(0, Math.min(100, progress))
}

function getTierIcon(tierName: string): string {
  const icons: Record<string, string> = {
    '初心者': '🌱',
    '进取': '🥉',
    '好学': '🥈',
    '学者': '🥇',
    '学霸': '💎',
    '学神': '👑',
  }
  return icons[tierName] ?? '🎓'
}
