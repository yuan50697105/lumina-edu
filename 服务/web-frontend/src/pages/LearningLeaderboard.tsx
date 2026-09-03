// ============================================
// Lumina 墨光 · D-06 排行榜
// 自主学习与闯关奖励系统 · 竞争激励
// ============================================
import { useEffect, useState } from 'react'
import { get } from '../api/client'
import type { LeaderboardResp, LeaderboardEntry } from '../api/types'

type Period = 'week' | 'month' | 'all'

export default function LearningLeaderboard() {
  const [data, setData] = useState<LeaderboardResp | null>(null)
  const [period, setPeriod] = useState<Period>('week')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    get<LeaderboardResp>(`/learning/leaderboard?period=${period}&limit=50`)
      .then(setData)
      .finally(() => setLoading(false))
  }, [period])

  if (loading || !data) return <div className="muted">加载中…</div>

  const entries = data.entries ?? []
  const top3 = entries.slice(0, 3)
  const rest = entries.slice(3)

  return (
    <div>
      {/* 头部控制栏 */}
      <div className="lb-head">
        <div className="sec-title" style={{ margin: 0 }}>
          排行榜 <span className="sub">按本周期获得 XP 排名 · 每 10 分钟刷新</span>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <div className="segmented">
            <button className={period === 'week' ? 'on' : ''} onClick={() => setPeriod('week')}>
              周榜
            </button>
            <button className={period === 'month' ? 'on' : ''} onClick={() => setPeriod('month')}>
              月榜
            </button>
            <button className={period === 'all' ? 'on' : ''} onClick={() => setPeriod('all')}>
              总榜
            </button>
          </div>
          <button className="btn" onClick={handleExportCSV} title="教师 / 管理员视角">
            ⬇ 导出 CSV
          </button>
        </div>
      </div>

      {/* Top 3 领奖台 */}
      <div className="podium">
        {top3.length >= 2 && (
          <PodiumCard entry={top3[1]} rank={2} cls="silver" />
        )}
        {top3.length >= 1 && (
          <PodiumCard entry={top3[0]} rank={1} cls="gold first" />
        )}
        {top3.length >= 3 && (
          <PodiumCard entry={top3[2]} rank={3} cls="bronze" />
        )}
      </div>

      {/* 排行列表 */}
      <div className="card lb-table">
        {rest.map((entry, idx) => (
          <div key={entry.user_id} className={`lb-row ${isMe(entry) ? 'me' : ''}`} style={{ animationDelay: `${idx * 40}ms` }}>
            <span className="lb-rank">{idx + 4}</span>
            <span className="lb-avatar">{entry.name[0]}</span>
            <span className="lb-who">
              <span className="lb-name">{entry.name}</span>
              <span className="lb-id">学号 {entry.user_id.slice(0, 8)}</span>
            </span>
            <span className="lb-xp">
              <span className="xp-hl">{entry.xp.toLocaleString()}</span>
            </span>
            <span className="lb-tier">
              <span className={`tier t${entry.level <= 4 ? 1 : entry.level <= 9 ? 2 : entry.level <= 19 ? 3 : entry.level <= 29 ? 4 : entry.level <= 49 ? 5 : 6}`}>
                {entry.tier_name}
              </span>
            </span>
          </div>
        ))}
        {rest.length === 0 && <div className="muted" style={{ textAlign: 'center', padding: 32 }}>暂无排行数据</div>}
      </div>

      {/* 我的排名悬浮条 */}
      {data.my_rank && (
        <div className="my-rank-bar">
          <span className="my-rank-num">#{data.my_rank}</span>
          <span>我</span>
          <span className="my-rank-xp">
            {entries.find(isMe)?.xp.toLocaleString() ?? '0'} XP · Lv.{entries.find(isMe)?.level ?? 1} {entries.find(isMe)?.tier_name}
          </span>
        </div>
      )}

      <div className="compliance-hint">
        ⚖️ 排行榜展示昵称与 XP，不展示真实姓名与学号；可在「设置 → 隐私」中
        <a onClick={() => alert('原型演示：跳转隐私设置')}>关闭排行榜参与</a>
        （关闭后不影响 XP 与徽章获取）
      </div>
    </div>
  )

  function isMe(entry: LeaderboardEntry): boolean {
    // 简化判断：实际应该对比当前登录用户 ID
    return false
  }

  function handleExportCSV() {
    const rows = [['排名', '昵称', '学号', 'XP', '等级']]
    entries.forEach((e, idx) => {
      rows.push([String(idx + 1), e.name, e.user_id.slice(0, 8), String(e.xp), e.tier_name])
    })
    const csv = '﻿' + rows.map((r) => r.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `lumina-leaderboard-${period}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }
}

function PodiumCard({ entry, rank, cls }: { entry: LeaderboardEntry; rank: number; cls: string }) {
  const medals: Record<string, string> = {
    gold: '🥇',
    silver: '🥈',
    bronze: '🥉',
  }

  return (
    <div className={`card pod ${cls}`}>
      <div className="pod-ring" data-medal={medals[cls.split(' ')[0]]}>
        {entry.name[0]}
      </div>
      <div className="pod-name">{entry.name}</div>
      <div className="pod-xp">{entry.xp.toLocaleString()} XP</div>
      <div className="pod-tier">
        <span className={`tier t${entry.level <= 4 ? 1 : entry.level <= 9 ? 2 : entry.level <= 19 ? 3 : entry.level <= 29 ? 4 : entry.level <= 49 ? 5 : 6}`} style={{ padding: '2px 10px', fontSize: 10.5 }}>
          {entry.tier_name}
        </span>
      </div>
    </div>
  )
}
