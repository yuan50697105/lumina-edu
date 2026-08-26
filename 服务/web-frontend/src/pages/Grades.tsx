import { useEffect, useState } from 'react'
import { get } from '../api/client'
import type { MyGrades as MyGradesT } from '../api/types'

export default function Grades() {
  const [data, setData] = useState<MyGradesT | null>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    get<MyGradesT>('/grades/me')
      .then(setData)
      .catch((e) => setErr((e as Error).message))
  }, [])

  if (err) return <div className="error">成绩单加载失败：{err}</div>
  if (!data) return <div className="muted">加载中…</div>

  return (
    <div>
      <h1 className="page-title">我的成绩单</h1>
      <div className="gpa-row">
        <div className="gpa-card">
          <span className="gpa-num">{data.gpa ?? '—'}</span>
          <span className="muted">加权 GPA</span>
        </div>
        <div className="gpa-card">
          <span className="gpa-num">{data.total_credits ?? 0}</span>
          <span className="muted">总学分</span>
        </div>
        <div className="gpa-card">
          <span className="gpa-num">{data.course_count}</span>
          <span className="muted">课程门数</span>
        </div>
      </div>

      <table className="table">
        <thead>
          <tr>
            <th>课程</th>
            <th>学分</th>
            <th>分数</th>
            <th>等级</th>
            <th>学期</th>
          </tr>
        </thead>
        <tbody>
          {data.courses.map((c) => (
            <tr key={c.course_id}>
              <td>{c.title}</td>
              <td>{c.credit ?? 0}</td>
              <td>{c.score ?? '—'}</td>
              <td>
                <span className={`letter ${(c.grade ?? '').toLowerCase()}`}>{c.grade ?? '—'}</span>
              </td>
              <td>{c.semester}</td>
            </tr>
          ))}
          {data.courses.length === 0 && (
            <tr>
              <td colSpan={5} className="muted">
                暂无成绩记录
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}