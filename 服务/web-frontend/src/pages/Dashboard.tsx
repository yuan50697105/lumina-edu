import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { get, post } from '../api/client'
import type { Course, CourseListResp, NotificationItem, UnreadCount } from '../api/types'
import { track } from '../utils/tracker'

interface EnrolledResp {
  course_id: string
  course: Course
  status: string
}

export default function Dashboard() {
  const [courses, setCourses] = useState<Course[]>([])
  const [enrolled, setEnrolled] = useState<Course[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    ;(async () => {
      try {
        const [list, mine] = await Promise.all([
          get<CourseListResp>('/courses?limit=24'),
          get<EnrolledResp[]>('/courses/me/enrolled').catch(() => []),
        ])
        setCourses(list.data ?? [])
        setEnrolled(mine.filter((m) => m.status === 'active').map((m) => m.course))
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  if (loading) return <div className="muted">加载中…</div>

  const mineIds = new Set(enrolled.map((c) => c.id))
  const plaza = courses.filter((c) => !mineIds.has(c.id))

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 className="page-title" style={{ marginBottom: 0 }}>
          首页
        </h1>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <NotificationBell />
          <Link to="/groups" className="btn ghost tiny">
            协作小组
          </Link>
        </div>
      </div>

      <section>
        <h2 className="section-title">我的课程（{enrolled.length}）</h2>
        {enrolled.length === 0 && <p className="muted">尚未选课，去课程广场逛逛吧。</p>}
        <div className="course-grid">
          {enrolled.map((c) => (
            <CourseCard key={c.id} c={c} mine />
          ))}
        </div>
      </section>

      <section>
        <h2 className="section-title">课程广场</h2>
        <div className="course-grid">
          {plaza.map((c) => (
            <CourseCard key={c.id} c={c} />
          ))}
          {plaza.length === 0 && <p className="muted">暂无可选课程。</p>}
        </div>
      </section>
    </div>
  )
}

// ─── 消息通知铃铛（D-03）───
function NotificationBell() {
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<NotificationItem[]>([])
  const [unread, setUnread] = useState(0)
  const navigate = useNavigate()

  async function refresh(pullList: boolean) {
    try {
      const counts = await get<UnreadCount>('/notifications/my/unread-count')
      setUnread(counts?.unread_count ?? 0)
      if (pullList) {
        const list = await get<NotificationItem[]>('/notifications/my?limit=20')
        setItems(list ?? [])
      }
    } catch {
      /* 通知服务不可用时静默 */
    }
  }

  useEffect(() => {
    refresh(false)
    const timer = setInterval(() => refresh(false), 30_000)
    return () => clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function toggle() {
    const next = !open
    setOpen(next)
    if (next) {
      track('notif.view', {})
      const [
        counts,
        list,
      ] = await Promise.all([
        get<UnreadCount>('/notifications/my/unread-count'),
        get<NotificationItem[]>('/notifications/my?limit=20'),
      ])
      setUnread(counts?.unread_count ?? 0)
      setItems(list ?? [])
    }
  }

  async function markRead(id: string) {
    await post(`/notifications/my/${id}/read`, {})
    track('notif.read', { id })
    refresh(true)
  }

  async function markAll() {
    await post('/notifications/my/read-all', {})
    track('notif.read_all', {})
    refresh(true)
  }

  function go(n: NotificationItem) {
    if (n.ref_type === 'course' && n.ref_id) navigate(`/courses/${n.ref_id}`)
    else if (n.ref_type === 'live_room' && n.ref_id) navigate(`/live/${n.ref_id}`)
    setOpen(false)
  }

  function timeText(iso: string) {
    const d = new Date(iso)
    return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  }

  return (
    <div className="notif">
      <button
        type="button"
        className="btn ghost tiny notif-bell"
        onClick={toggle}
        data-track="通知"
        aria-label="消息通知"
      >
        🔔
        {unread > 0 && <span className="notif-badge">{unread > 99 ? '99+' : unread}</span>}
      </button>

      {open && (
        <div className="notif-panel">
          <div className="notif-head">
            <b>消息通知</b>
            {unread > 0 && (
              <button type="button" className="link-like" onClick={markAll}>
                全部已读
              </button>
            )}
          </div>
          {items.length === 0 ? (
            <p className="muted notif-empty">暂无消息</p>
          ) : (
            <ul className="notif-list">
              {items.map((n) => (
                <li
                  key={n.id}
                  className={n.is_read ? '' : 'unread'}
                  onClick={() => {
                    if (!n.is_read) markRead(n.id)
                    go(n)
                  }}
                >
                  <div className="notif-title">{n.title}</div>
                  {n.content && <div className="notif-content">{n.content}</div>}
                  <span className="notif-time">{timeText(n.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

function CourseCard({ c, mine }: { c: Course; mine?: boolean }) {
  return (
    <Link to={`/courses/${c.id}`} className={`course-card`}>
      <div className="course-code">{c.code}</div>
      <h3>{c.title}</h3>
      <p className="muted">
        {c.teacher?.name ?? '—'} · {c.credits ?? 0} 学分 · {c.semester}
      </p>
      <p className="course-desc">{c.description || ''}</p>
      <div className="course-meta">
        <span>{mine ? '已选课' : `${c.students_count} 人`}</span>
        <span className={`pill ${c.status === 'published' ? 'ok' : ''}`}>{c.status === 'published' ? '已发布' : c.status}</span>
      </div>
    </Link>
  )
}