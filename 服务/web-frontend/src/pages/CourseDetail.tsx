import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { del, get, post } from '../api/client'
import type { Chapter, Course, LiveRoom as LiveRoomItem } from '../api/types'
import { useAuthStore } from '../store/auth'
import { track } from '../utils/tracker'

const LIVE_STATUS: Record<string, string> = { scheduled: '未开始', live: '直播中', ended: '已结束' }

export default function CourseDetail() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const [course, setCourse] = useState<Course | null>(null)
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [liveRooms, setLiveRooms] = useState<LiveRoomItem[]>([])
  const [enrolled, setEnrolled] = useState(false)
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState<string | null>(null)

  useEffect(() => {
    ;(async () => {
      try {
        const [c, ch] = await Promise.all([get<Course>(`/courses/${id}`), get<Chapter[]>(`/courses/${id}/chapters`)])
        setCourse(c)
        setChapters(ch ?? [])
        // 我的选课状态
        const mine = (await get<{ course_id: string; status: string }[]>('/courses/me/enrolled').catch(() => [])) as {
          course_id: string
          status: string
        }[]
        setEnrolled(mine.some((m) => m.course_id === id && m.status === 'active'))
      } finally {
        setLoading(false)
      }
    })()
  }, [id])

  useEffect(() => {
    get<LiveRoomItem[]>(`/courses/${id}/live/rooms`)
      .then((r) => setLiveRooms(r ?? []))
      .catch(() => setLiveRooms([]))
  }, [id])

  async function toggleEnroll() {
    try {
      if (enrolled) {
        await del(`/courses/${id}/enroll`)
        track('course.unenroll', { course_id: id })
      } else {
        await post(`/courses/${id}/enroll`)
        track('course.enroll', { course_id: id })
      }
      setEnrolled(!enrolled)
    } catch (e) {
      alert((e as Error).message)
    }
  }

  async function createLive() {
    const title = window.prompt('直播标题（留空自动使用课程名）') ?? ''
    try {
      const r = await post<LiveRoomItem>(`/live/rooms`, { course_id: id, title: title.trim() || undefined })
      track('live.room_create', { course_id: id })
      navigate(`/live/${r.id}`)
    } catch (e) {
      alert((e as Error).message)
    }
  }

  const isTeacher = !!course && !!user && (user.role === 'admin' || course.teacher?.id === user.id)

  if (loading) return <div className="muted">加载中…</div>
  if (!course) return <div className="error">课程不存在</div>

  return (
    <div>
      <div className="course-head">
        <div>
          <span className="course-code">{course.code}</span>
          <h1 className="page-title">{course.title}</h1>
          <p className="muted">
            {course.teacher?.name ?? '—'} · {course.department || '—'} · {course.credits ?? 0} 学分 · {course.semester} ·{' '}
            {course.students_count} 人选课
          </p>
          {course.description && <p>{course.description}</p>}
        </div>
        <button className={`btn ${enrolled ? 'ghost' : 'primary'}`} onClick={toggleEnroll} data-track="enroll-toggle">
          {enrolled ? '退课' : '选课'}
        </button>
      </div>

      <h2 className="section-title">
        直播课堂（{liveRooms.length}）
        {isTeacher && (
          <span className="section-actions">
            <button className="btn primary tiny" onClick={() => void createLive()} data-track="live-create">
              ＋ 创建直播
            </button>
          </span>
        )}
      </h2>
      <div className="live-room-list">
        {liveRooms.map((r) => (
          <div key={r.id} className="live-room-card" onClick={() => navigate(`/live/${r.id}`)} data-track="live-open">
            <span className="course-code">{r.course_title ?? '直播'}</span>
            <b>{r.title}</b>
            <span className={`pill ${r.status === 'live' ? 'ok' : ''}`}>{LIVE_STATUS[r.status]}</span>
            <span className="muted">
              在线 {r.online_count ?? 0} · 累计 {r.viewer_count ?? 0} 人次
              {r.status === 'live' && r.stream_url?.startsWith('http') && ' · 有推流'}
            </span>
          </div>
        ))}
        {liveRooms.length === 0 && <p className="muted">暂无直播安排。</p>}
      </div>

      <h2 className="section-title">课程章节（{chapters.length}）</h2>
      <div className="chapter-list">
        {chapters.map((ch) => (
          <div key={ch.id} className="chapter-item">
            <button className="chapter-head" onClick={() => setOpen(open === ch.id ? null : ch.id)}>
              <span>{ch.order_num}.</span> {ch.title}
            </button>
            {open === ch.id && ch.content && <div className="chapter-body">{ch.content}</div>}
          </div>
        ))}
        {chapters.length === 0 && <p className="muted">暂无章节。</p>}
      </div>
    </div>
  )
}