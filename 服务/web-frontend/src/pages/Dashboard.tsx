import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { get } from '../api/client'
import type { Course, CourseListResp } from '../api/types'

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
      <h1 className="page-title">首页</h1>

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