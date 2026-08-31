// Lumina 墨光 · 协作小组列表（D-02）
// ?course=<id> → 课程小组视图（教师可创建）；否则「我的小组」视图
import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { del, get, post } from '../api/client'
import type { Course, Group } from '../api/types'
import { useAuthStore } from '../store/auth'
import { track } from '../utils/tracker'

export default function Groups() {
  const [params] = useSearchParams()
  const courseId = params.get('course')
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const [groups, setGroups] = useState<Group[]>([])
  const [course, setCourse] = useState<Course | null>(null)
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    const list = courseId
      ? await get<Group[]>(`/courses/${courseId}/groups`)
      : await get<Group[]>(`/groups/me`)
    setGroups(list ?? [])
  }

  useEffect(() => {
    track('collab.group_list', { course_id: courseId ?? undefined })
    load().catch(() => setGroups([]))
    if (courseId) {
      get<Course>(`/courses/${courseId}`)
        .then(setCourse)
        .catch(() => setCourse(null))
    } else {
      setCourse(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId])

  const isCourseTeacher = !!course && (user?.role === 'admin' || course.teacher?.id === user?.id)

  async function createGroup() {
    if (!courseId || !name.trim()) return
    setBusy(true)
    try {
      const g = await post<Group>(`/courses/${courseId}/groups`, { name: name.trim(), description: desc || undefined })
      track('collab.group_create', { group_id: g.id, course_id: courseId })
      setGroups([...groups, g])
      setName('')
      setDesc('')
    } catch (e) {
      alert(e instanceof Error ? e.message : '创建失败，请重试')
    } finally {
      setBusy(false)
    }
  }

  async function join(g: Group) {
    try {
      await post(`/groups/${g.id}/members`)
      track('collab.group_join', { group_id: g.id, course_id: g.course_id })
      await load()
    } catch (e) {
      alert(e instanceof Error ? e.message : '加入失败，请重试')
    }
  }

  async function removeGroup(g: Group) {
    if (!confirm(`删除小组「${g.name}」？项目与讨论将一并删除。`)) return
    try {
      await del(`/groups/${g.id}`)
      setGroups(groups.filter((x) => x.id !== g.id))
    } catch (e) {
      alert(e instanceof Error ? e.message : '删除失败，请重试')
    }
  }

  function canManage(g: Group) {
    return user?.role === 'admin' || course?.teacher?.id === user?.id || user?.id === g.leader_id
  }

  return (
    <div>
      <Link to="/" className="muted" style={{ fontSize: 13 }}>
        ← 返回首页
      </Link>
      <h1 className="page-title">协作小组{course ? ` · ${course.title}` : '（我的）'}</h1>

      {courseId && isCourseTeacher && (
        <div className="card" style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
          <div className="field" style={{ flex: 1 }}>
            <label>小组名称</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="如：第 3 组" />
          </div>
          <div className="field" style={{ flex: 2 }}>
            <label>说明（可选）</label>
            <input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="小组任务 / 研究方向" />
          </div>
          <button className="btn primary" disabled={busy || !name.trim()} onClick={() => void createGroup()}>
            创建小组
          </button>
        </div>
      )}

      {courseId && !isCourseTeacher && (
        <p className="muted">本课程的协作小组，选择感兴趣的加入。</p>
      )}

      {groups.length === 0 && <p className="muted">暂无小组。</p>}
      {groups.map((g) => (
        <div className="card" key={g.id}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0 }}>{g.name}</h3>
            <span className={`pill ${g.is_member ? 'ok' : ''}`}>{g.is_member ? '已加入' : '未加入'}</span>
          </div>
          <p className="muted" style={{ marginTop: 6 }}>
            {g.course_title || '—'} · 组长 {g.leader_name ?? '—'} · {g.member_count} 人 · {g.project_count} 个项目
          </p>
          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            {g.is_member ? (
              <button className="btn primary tiny" onClick={() => navigate(`/groups/${g.id}`)}>
                进入小组
              </button>
            ) : (
              <button className="btn tiny" onClick={() => void join(g)}>
                加入小组
              </button>
            )}
            {canManage(g) && (
              <button className="btn ghost tiny" onClick={() => void removeGroup(g)}>
                删除
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}