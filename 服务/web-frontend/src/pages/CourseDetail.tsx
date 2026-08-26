import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { del, get, post } from '../api/client'
import type { Chapter, Course } from '../api/types'
import { track } from '../utils/tracker'

export default function CourseDetail() {
  const { id = '' } = useParams()
  const [course, setCourse] = useState<Course | null>(null)
  const [chapters, setChapters] = useState<Chapter[]>([])
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