// Lumina 墨光 · 小组协作详情（D-02）
// Tabs：看板（列 + 卡片，简单按钮拖拽）/ 组内讨论 / 共享文件
import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { BASE, del, get, patch, post, upload } from '../api/client'
import type { Board, CollabProject, Group, KanbanCard, SharedFile, Topic } from '../api/types'
import { useAuthStore } from '../store/auth'
import { track } from '../utils/tracker'

type Tab = 'kanban' | 'discuss' | 'files'
const TABS: Tab[] = ['kanban', 'discuss', 'files']
const TAB_NAME: Record<Tab, string> = { kanban: '项目看板', discuss: '组内讨论', files: '共享文件' }
const KB = 1024
const fmtSize = (n: number) =>
  n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB` : n >= KB ? `${(n / KB).toFixed(0)} KB` : `${n} B`

export default function GroupDetail() {
  const { id = '' } = useParams()
  const user = useAuthStore((s) => s.user)
  const [group, setGroup] = useState<Group | null>(null)
  const [tab, setTab] = useState<Tab>('kanban')
  const [err, setErr] = useState('')

  // 看板
  const [projects, setProjects] = useState<CollabProject[]>([])
  const [projectId, setProjectId] = useState('')
  const [board, setBoard] = useState<Board | null>(null)
  const [colTitle, setColTitle] = useState('')

  // 讨论
  const [topics, setTopics] = useState<Topic[]>([])
  const [tTitle, setTTitle] = useState('')
  const [tContent, setTContent] = useState('')
  const [replying, setReplying] = useState('')
  const [replyText, setReplyText] = useState('')

  // 文件
  const [files, setFiles] = useState<SharedFile[]>([])

  const loadGroup = useCallback(async () => {
    setGroup(await get<Group>(`/groups/${id}`))
  }, [id])
  const loadProjects = useCallback(async () => {
    setProjects((await get<CollabProject[]>(`/groups/${id}/projects`).catch(() => [])) ?? [])
  }, [id])
  const loadBoard = useCallback(async () => {
    if (!projectId) {
      setBoard(null)
      return
    }
    setBoard(await get<Board>(`/projects/${projectId}/board`).catch(() => null))
  }, [projectId])
  const loadTopics = useCallback(async () => {
    setTopics((await get<Topic[]>(`/groups/${id}/topics`).catch(() => [])) ?? [])
  }, [id])
  const loadFiles = useCallback(async () => {
    setFiles((await get<SharedFile[]>(`/groups/${id}/files`).catch(() => [])) ?? [])
  }, [id])

  useEffect(() => {
    track('collab.group_view', { group_id: id })
    loadGroup().catch((e) => setErr(e instanceof Error ? e.message : '加载失败'))
    loadProjects().catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  useEffect(() => {
    if (tab === 'discuss') loadTopics().catch(() => {})
    if (tab === 'files') loadFiles().catch(() => {})
  }, [tab, loadTopics, loadFiles])

  useEffect(() => {
    track('collab.project_open', { project_id: projectId })
    loadBoard().catch(() => {})
  }, [projectId, loadBoard])

  const isMember = !!group?.is_member
  const canEdit = !!group && (isMember || user?.role === 'admin')

  async function join() {
    try {
      await post(`/groups/${id}/members`)
      track('collab.group_join', { group_id: id })
      await loadGroup()
    } catch (e) {
      alert(e instanceof Error ? e.message : '加入失败')
    }
  }

  async function createProject() {
    const title = prompt('项目名称', '')
    if (!title || !title.trim()) return
    try {
      const p = await post<CollabProject>(`/groups/${id}/projects`, { title: title.trim() })
      track('collab.project_create', { project_id: p.id, group_id: id })
      await loadProjects()
      setProjectId(p.id)
    } catch (e) {
      alert(e instanceof Error ? e.message : '创建项目失败')
    }
  }

  async function addColumn() {
    if (!projectId || !colTitle.trim()) return
    try {
      await post(`/projects/${projectId}/columns`, { title: colTitle.trim() })
      track('collab.column_add', { project_id: projectId })
      setColTitle('')
      await loadBoard()
    } catch (e) {
      alert(e instanceof Error ? e.message : '新建列失败')
    }
  }

  async function addCard(colId: string) {
    const title = prompt('任务卡片', '')
    if (!title || !title.trim()) return
    try {
      const c = await post<KanbanCard>(`/columns/${colId}/cards`, { title: title.trim() })
      track('collab.card_create', { card_id: c.id })
      await loadBoard()
    } catch (e) {
      alert(e instanceof Error ? e.message : '新建卡片失败')
    }
  }

  async function moveCard(card: KanbanCard, dir: 1 | -1) {
    const cols = board?.columns ?? []
    const ci = cols.findIndex((c) => c.id === card.column_id)
    const target = cols[ci + dir]
    if (!target) return
    try {
      await patch(`/cards/${card.id}`, { column_id: target.id })
      track('collab.card_move', { card_id: card.id, column_id: target.id, project_id: projectId })
      await loadBoard()
    } catch (e) {
      alert(e instanceof Error ? e.message : '移动卡片失败')
    }
  }

  async function deleteCard(cardId: string) {
    if (!confirm('删除该卡片？')) return
    try {
      await del(`/cards/${cardId}`)
      await loadBoard()
    } catch (e) {
      alert(e instanceof Error ? e.message : '删除失败')
    }
  }

  async function deleteColumn(colId: string) {
    if (!confirm('删除该列及其全部卡片？')) return
    try {
      await del(`/columns/${colId}`)
      await loadBoard()
    } catch (e) {
      alert(e instanceof Error ? e.message : '删除失败')
    }
  }

  async function createTopic() {
    if (!tTitle.trim()) return
    try {
      await post(`/groups/${id}/topics`, { title: tTitle.trim(), content: tContent || undefined })
      track('collab.topic_create', { group_id: id })
      setTTitle('')
      setTContent('')
      await loadTopics()
    } catch (e) {
      alert(e instanceof Error ? e.message : '发帖失败')
    }
  }

  async function addReply(topicId: string) {
    if (!replyText.trim()) return
    try {
      await post(`/topics/${topicId}/replies`, { content: replyText.trim() })
      track('collab.reply_create', { topic_id: topicId, group_id: id })
      setReplyText('')
      setReplying('')
      await loadTopics()
    } catch (e) {
      alert(e instanceof Error ? e.message : '回复失败')
    }
  }

  async function doUpload(file?: File) {
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    try {
      await upload(`/groups/${id}/files`, fd)
      track('collab.file_upload', { filename: file.name, size: file.size })
      await loadFiles()
    } catch (e) {
      alert(e instanceof Error ? e.message : '上传失败')
    }
  }

  async function download(f: SharedFile) {
    const token = useAuthStore.getState().token
    try {
      const resp = await fetch(`${BASE}/files/${f.id}/download`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!resp.ok) throw new Error(`下载失败 (${resp.status})`)
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = f.filename
      a.click()
      URL.revokeObjectURL(url)
      track('collab.file_download', { filename: f.filename })
    } catch (e) {
      alert(e instanceof Error ? e.message : '下载失败')
    }
  }

  const cols = board?.columns ?? []

  return (
    <div>
      <Link to={group?.course_id ? `/groups?course=${group.course_id}` : '/groups'} className="muted" style={{ fontSize: 13 }}>
        ← 返回小组
      </Link>
      <h1 className="page-title">{group?.name ?? '小组协作'}</h1>
      <p className="muted">
        {group?.course_title ?? ''} · 组长 {group?.leader_name ?? '—'} · {group?.member_count ?? 0} 人 ·{' '}
        {group?.members.map((m) => m.name).join('、') || '—'}
      </p>
      {!isMember && (
        <button className="btn primary tiny" onClick={() => void join()}>
          加入小组
        </button>
      )}
      {err && <p style={{ color: 'crimson' }}>{err}</p>}

      <div style={{ display: 'flex', gap: 8, margin: '16px 0' }}>
        {TABS.map((t) => (
          <button key={t} className={tab === t ? 'btn primary tiny' : 'btn ghost tiny'} onClick={() => setTab(t)}>
            {TAB_NAME[t]}
          </button>
        ))}
      </div>

      {tab === 'kanban' && (
        <>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 12 }}>
            <select
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              style={{ maxWidth: 260 }}
              className="input"
            >
              <option value="">— 选择项目 —</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                </option>
              ))}
            </select>
            {canEdit && (
              <button className="btn ghost tiny" onClick={() => void createProject()}>
                ＋ 新建项目
              </button>
            )}
          </div>

          {!projectId && <p className="muted">选择一个项目查看看板。</p>}
          {projectId && cols.length === 0 && <p className="muted">看板还没有列，右侧新建。</p>}

          {projectId && (
            <div style={{ display: 'flex', gap: 12, overflowX: 'auto', paddingBottom: 8, alignItems: 'flex-start' }}>
              {cols.map((col, ci) => (
                <div
                  key={col.id}
                  style={{ background: '#f6f2e6', borderRadius: 10, padding: 10, width: 220, minWidth: 220 }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <b>{col.title}</b>
                    {canEdit && (
                      <button className="btn ghost tiny" onClick={() => void deleteColumn(col.id)}>
                        ×
                      </button>
                    )}
                  </div>
                  {col.cards.map((card) => (
                    <div
                      key={card.id}
                      style={{
                        background: '#fff',
                        border: '1px solid var(--border)',
                        borderRadius: 8,
                        padding: 10,
                        marginTop: 8,
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <b style={{ fontSize: 13 }}>{card.title}</b>
                        {canEdit && (
                          <button className="btn ghost tiny" onClick={() => void deleteCard(card.id)}>
                            ×
                          </button>
                        )}
                      </div>
                      {card.assignee_name && (
                        <div className="muted" style={{ fontSize: 12 }}>
                          @{card.assignee_name}
                        </div>
                      )}
                      {canEdit && (
                        <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                          <button className="btn ghost tiny" disabled={ci === 0} onClick={() => void moveCard(card, -1)}>
                            ◀ 左移
                          </button>
                          <button
                            className="btn ghost tiny"
                            disabled={ci === cols.length - 1}
                            onClick={() => void moveCard(card, 1)}
                          >
                            右移 ▶
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                  {canEdit && (
                    <button className="btn ghost tiny" style={{ marginTop: 10 }} onClick={() => void addCard(col.id)}>
                      ＋ 任务卡片
                    </button>
                  )}
                </div>
              ))}
              {canEdit && (
                <div style={{ width: 180, background: '#faf6ec', borderRadius: 10, padding: 10, border: '1px dashed var(--border)' }}>
                  <input
                    style={{ width: '100%' }}
                    className="input"
                    placeholder="新列名称"
                    value={colTitle}
                    onChange={(e) => setColTitle(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && void addColumn()}
                  />
                  <button className="btn tiny" style={{ marginTop: 8, width: '100%' }} onClick={() => void addColumn()}>
                    ＋ 新建列
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {tab === 'discuss' && (
        <>
          {topics.map((t) => (
            <div className="card" key={t.id}>
              <h3 style={{ margin: 0, fontSize: 16 }}>
                {t.title} <span className="muted" style={{ fontWeight: 400 }}>· {t.author_name}</span>
              </h3>
              {t.content && <p className="muted">{t.content}</p>}
              {t.replies?.map((r) => (
                <div key={r.id} style={{ borderLeft: '2px solid var(--border)', paddingLeft: 10, marginTop: 8, fontSize: 14 }}>
                  <b>{r.author_name}</b>：{r.content}
                </div>
              ))}
              {replying === t.id ? (
                <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                  <input
                    className="input"
                    style={{ flex: 1 }}
                    value={replyText}
                    placeholder="回复…"
                    onChange={(e) => setReplyText(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && void addReply(t.id)}
                  />
                  <button className="btn primary tiny" onClick={() => void addReply(t.id)}>
                    发送
                  </button>
                  <button className="btn ghost tiny" onClick={() => setReplying('')}>
                    取消
                  </button>
                </div>
              ) : (
                <button className="btn ghost tiny" style={{ marginTop: 8 }} onClick={() => setReplying(t.id)}>
                  回复{t.reply_count > 0 ? `（${t.reply_count}）` : ''}
                </button>
              )}
            </div>
          ))}
          {topics.length === 0 && <p className="muted">暂无讨论。</p>}
          {canEdit && (
            <div className="card">
              <div className="field">
                <label>新讨论主题</label>
                <input className="input" value={tTitle} onChange={(e) => setTTitle(e.target.value)} placeholder="如：本周分工确认" />
              </div>
              <div className="field">
                <label>内容（可选）</label>
                <textarea className="input" rows={2} value={tContent} onChange={(e) => setTContent(e.target.value)} />
              </div>
              <button className="btn primary tiny" disabled={!tTitle.trim()} onClick={() => void createTopic()}>
                发表主题
              </button>
            </div>
          )}
        </>
      )}

      {tab === 'files' && (
        <>
          {canEdit && (
            <div className="card" style={{ padding: 12 }}>
              <label className="btn primary tiny" style={{ display: 'inline-block', cursor: 'pointer' }}>
                ＋ 上传文件
                <input type="file" style={{ display: 'none' }} onChange={(e) => void doUpload(e.target.files?.[0])} />
              </label>
            </div>
          )}
          {files.map((f) => (
            <div className="card" key={f.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 12 }}>
              <div>
                <b>{f.filename}</b>
                <div className="muted" style={{ fontSize: 12 }}>
                  {fmtSize(f.size)} · {f.uploader_name ?? '—'} · {new Date(f.created_at).toLocaleString()}
                </div>
              </div>
              <button className="btn ghost tiny" onClick={() => void download(f)}>
                下载
              </button>
            </div>
          ))}
          {files.length === 0 && <p className="muted">暂无共享文件。</p>}
        </>
      )}
    </div>
  )
}