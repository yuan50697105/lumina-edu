// Lumina 墨光 · 课程考试中心（D-04）
//  教师：题库管理（题目 CRUD）+ 试卷管理（组卷/发布/关闭/统计/人工评分）
//  学生：可参加试卷列表 + 我的考试状态 + 进入考试
// 路由：/courses/:id/exam
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { del, get, patch, post } from '../api/client'
import type {
  Difficulty,
  ExamPaper,
  ExamPaperQuestion,
  ExamQuestion,
  PaperStats,
  QuestionListResp,
  QuestionType,
} from '../api/types'
import { useAuthStore } from '../store/auth'
import { track } from '../utils/tracker'

const QTYPE_LABEL: Record<string, string> = {
  single: '单选', multiple: '多选', true_false: '判断', short_answer: '简答',
}
const DIFF_LABEL: Record<string, string> = { easy: '易', medium: '中', hard: '难' }
const PAPER_STATUS: Record<string, string> = { draft: '草稿', published: '已发布', closed: '已关闭' }

function emptyForm() {
  return {
    qtype: 'single' as QuestionType,
    title: '',
    options: [
      { key: 'A', text: '' },
      { key: 'B', text: '' },
    ],
    answer: [] as string[],
    score: 5,
    difficulty: 'medium' as Difficulty,
    tags: '',
  }
}

export default function Exam() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const [course, setCourse] = useState<{ id: string; title: string; teacher?: { id: string } } | null>(null)
  const [tab, setTab] = useState<'questions' | 'papers'>('papers')

  useEffect(() => {
    get<{ id: string; title: string; teacher?: { id: string } }>(`/courses/${id}`)
      .then(setCourse)
      .catch(() => setCourse(null))
  }, [id])

  const isTeacher = !!course && !!user && (user.role === 'admin' || course.teacher?.id === user.id)

  return (
    <div>
      <div className="course-head">
        <div>
          <span className="course-code">考试中心</span>
          <h1 className="page-title">{course?.title ?? '课程考试'}</h1>
          <p className="muted">题库 · 试卷 · 在线考试{isTeacher ? ' · 教师管理' : ''}</p>
        </div>
        <button className="btn ghost" onClick={() => navigate(`/courses/${id}`)}>
          返回课程
        </button>
      </div>

      <div className="tabbar">
        {isTeacher ? (
          <>
            <button className={'tab' + (tab === 'questions' ? ' active' : '')} onClick={() => setTab('questions')}>
              题库管理
            </button>
            <button className={'tab' + (tab === 'papers' ? ' active' : '')} onClick={() => setTab('papers')}>
              试卷与考试
            </button>
          </>
        ) : (
          <StudentExams courseId={id} />
        )}
      </div>

      {isTeacher ? (
        tab === 'questions' ? <QuestionManager courseId={id} /> : <PaperManager courseId={id} />
      ) : null}
    </div>
  )
}

// ═══════════════════════════════════════════
// 学生：可参加试卷
// ═══════════════════════════════════════════
function StudentExams({ courseId }: { courseId: string }) {
  const [papers, setPapers] = useState<ExamPaper[]>([])
  const fail = (e: unknown) => alert(e instanceof Error ? e.message : '操作失败')
  const navigate = useNavigate()

  const load = useCallback(() => {
    get<{ code: number; data: ExamPaper[] }>(`/courses/${courseId}/papers`)
      .then((r) => setPapers(r.data ?? []))
      .catch(() => setPapers([]))
  }, [courseId])

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load])

  async function start(p: ExamPaper) {
    try {
      track('exam.attempt_start', { paper_id: p.id, course_id: courseId })
      navigate(`/exam/${p.id}`)
    } catch (e) {
      fail(e)
    }
  }

  return (
    <div>
      <h2 className="section-title">本课程试卷（{papers.length}）</h2>
      {papers.length === 0 && <p className="muted">暂无可参加的考试。</p>}
      {papers.map((p) => {
        const a = p.my_attempt
        const status = a
          ? a.status === 'submitted'
            ? `已提交 · ${a.total_score} 分`
            : '进行中'
          : '未开始'
        return (
          <div key={p.id} className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <b>{p.title}</b>
              <div className="muted">
                {p.question_count} 题 · 满分 {p.total_score} · {p.duration_minutes} 分钟
                {p.description && ` · ${p.description}`}
              </div>
              <span className={'pill' + (a?.status === 'submitted' ? ' ok' : a?.status === 'in_progress' ? '' : '')}>
                {status}
              </span>
            </div>
            <button
              className="btn primary tiny"
              onClick={() => void start(p)}
              disabled={!p.questions?.length && p.question_count === 0}
            >
              {a?.status === 'submitted' ? '查看成绩' : a?.status === 'in_progress' ? '继续考试' : '开始考试'}
            </button>
          </div>
        )
      })}
    </div>
  )
}

// ═══════════════════════════════════════════
// 教师：题库管理
// ═══════════════════════════════════════════
function QuestionManager({ courseId }: { courseId: string }) {
  const [all, setAll] = useState<ExamQuestion[]>([])
  const [editing, setEditing] = useState<ExamQuestion | 'new' | null>(null)
  const [filter, setFilter] = useState<{ qtype: string; difficulty: string }>({ qtype: '', difficulty: '' })

  const load = useCallback(() => {
    get<QuestionListResp>(`/courses/${courseId}/questions`)
      .then((r) => setAll(r.data ?? []))
      .catch(() => setAll([]))
  }, [courseId])

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load])

  const rows = all.filter(
    (q) =>
      (!filter.qtype || q.qtype === filter.qtype) &&
      (!filter.difficulty || q.difficulty === filter.difficulty),
  )

  async function remove(q: ExamQuestion) {
    if (!confirm(`删除题目「${q.title}」？已在试卷中的关联会被移除。`)) return
    try {
      await del(`/questions/${q.id}`)
      track('exam.question_delete', { question_id: q.id })
      setAll(all.filter((x) => x.id !== q.id))
    } catch (e) {
      alert(e instanceof Error ? e.message : '删除失败')
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <h2 className="section-title">题库（{rows.length}）</h2>
        <button className="btn primary tiny" onClick={() => setEditing('new')} data-track="exam-question-new">
          ＋ 新建题目
        </button>
      </div>

      <div className="form-grid" style={{ marginBottom: 10 }}>
        <label className="field">
          <span>题型</span>
          <select value={filter.qtype} onChange={(e) => setFilter({ ...filter, qtype: e.target.value })}>
            <option value="">全部</option>
            {Object.entries(QTYPE_LABEL).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>难度</span>
          <select value={filter.difficulty} onChange={(e) => setFilter({ ...filter, difficulty: e.target.value })}>
            <option value="">全部</option>
            {Object.entries(DIFF_LABEL).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </label>
      </div>

      {editing && (
        <QuestionForm
          courseId={courseId}
          init={editing === 'new' ? null : editing}
          onDone={() => {
            setEditing(null)
            load()
          }}
        />
      )}

      <div className="table">
        {rows.map((q) => (
          <div key={q.id} className="table-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div>
                <span className="pill">{QTYPE_LABEL[q.qtype]}</span>{' '}
                <span className="pill" style={q.difficulty === 'hard' ? { background: '#fdecea', color: '#c0392b' } : undefined}>
                  {DIFF_LABEL[q.difficulty]}
                </span>{' '}
                <b>{q.title}</b>
                <span className="muted"> · {q.score} 分</span>
              </div>
              {q.tags && q.tags.length > 0 && <div className="muted">{(q.tags as string[]).join(' / ')}</div>}
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="btn ghost tiny" onClick={() => setEditing(q)}>编辑</button>
              <button className="btn tiny" onClick={() => void remove(q)}>删除</button>
            </div>
          </div>
        ))}
        {rows.length === 0 && <div className="muted">暂无题目。</div>}
      </div>
    </div>
  )
}

function QuestionForm({ courseId, init, onDone }: { courseId: string; init: ExamQuestion | null; onDone: () => void }) {
  const [f, setF] = useState(() => {
    const base = init
      ? {
          qtype: init.qtype,
          title: init.title,
          options: init.options ? init.options.map((o) => ({ ...o })) : [],
          answer: init.answer ? [...init.answer] : [],
          score: init.score,
          difficulty: init.difficulty,
          tags: (init.tags ?? []).join('，'),
        }
      : emptyForm()
    return base
  })
  const [busy, setBusy] = useState(false)
  const set = (patch: Partial<typeof f>) => setF((x) => ({ ...x, ...patch }))

  const isObjective = f.qtype !== 'short_answer'

  function addOption() {
    const nextKey = String.fromCharCode(65 + f.options.length)
    set({ options: [...f.options, { key: nextKey, text: '' }] })
  }

  function toggleAnswer(key: string) {
    if (f.qtype === 'multiple') {
      set({ answer: f.answer.includes(key) ? f.answer.filter((k) => k !== key) : [...f.answer, key] })
    } else {
      set({ answer: [key] })
    }
  }

  async function save() {
    if (!f.title.trim()) return alert('请填写题干')
    if (isObjective && (!f.options.length || f.answer.length === 0)) return alert('客观题请填写选项并勾选正确答案')
    setBusy(true)
    try {
      const body = {
        qtype: f.qtype,
        title: f.title.trim(),
        options: isObjective ? f.options.filter((o) => o.text.trim()) : null,
        answer: isObjective ? f.answer : null,
        score: f.score,
        difficulty: f.difficulty,
        tags: f.tags ? f.tags.split(/[，,]/).map((t) => t.trim()).filter(Boolean) : [],
      }
      if (init) {
        await patch(`/questions/${init.id}`, body)
        track('exam.question_update', { question_id: init.id })
      } else {
        await post(`/courses/${courseId}/questions`, body)
        track('exam.question_create', { course_id: courseId })
      }
      onDone()
    } catch (e) {
      alert(e instanceof Error ? e.message : '保存失败')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card" style={{ borderColor: 'var(--primary)' }}>
      <div className="form-grid">
        <label className="field">
          <span>题型</span>
          <select value={f.qtype} onChange={(e) => set({ qtype: e.target.value as QuestionType, answer: [] })}>
            {Object.entries(QTYPE_LABEL).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>难度</span>
          <select value={f.difficulty} onChange={(e) => set({ difficulty: e.target.value as Difficulty })}>
            {Object.entries(DIFF_LABEL).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>分值</span>
          <input type="number" min={1} max={100} value={f.score} onChange={(e) => set({ score: +e.target.value })} />
        </label>
        <label className="field">
          <span>标签（逗号分隔）</span>
          <input value={f.tags} onChange={(e) => set({ tags: e.target.value })} placeholder="基础，章节一" />
        </label>
      </div>

      <label className="field" style={{ marginTop: 10 }}>
        <span>题干</span>
        <textarea rows={2} value={f.title} onChange={(e) => set({ title: e.target.value })} placeholder="请输入题目内容…" />
      </label>

      {isObjective ? (
        <div style={{ marginTop: 10 }}>
          <b style={{ fontSize: 13 }}>选项（点击文字行选中为正确答案{f.qtype === 'multiple' ? '，可多选' : ''}）</b>
          {f.options.map((o, i) => (
            <div key={o.key} style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 8 }}>
              <input
                type={f.qtype === 'multiple' ? 'checkbox' : 'radio'}
                checked={f.answer.includes(o.key)}
                onChange={() => toggleAnswer(o.key)}
              />
              <b style={{ width: 20 }}>{o.key}.</b>
              <input className="input" value={o.text} onChange={(e) => {
                const opts = [...f.options]
                opts[i] = { ...opts[i], text: e.target.value }
                set({ options: opts })
              }} placeholder="选项内容" />
              {f.options.length > 2 && (
                <button className="btn tiny" onClick={() => {
                  const opts = f.options.filter((_, idx) => idx !== i)
                  set({ options: opts, answer: f.answer.includes(o.key) ? f.answer.filter((k) => k !== o.key) : f.answer })
                }}>✕</button>
              )}
            </div>
          ))}
          <button className="btn ghost tiny" onClick={addOption}>＋ 添加选项</button>
        </div>
      ) : (
        <div className="muted" style={{ marginTop: 8, fontSize: 13 }}>
          简答题：学生填写文本，提交后由教师人工评分。
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
        <button className="btn primary tiny" onClick={() => void save()} disabled={busy}>{init ? '保存修改' : '创建题目'}</button>
        <button className="btn ghost tiny" onClick={onDone}>取消</button>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════
// 教师：试卷与考试
// ═══════════════════════════════════════════
interface PaperDetailView {
  paper: ExamPaper
  stats: PaperStats | null
}

function PaperManager({ courseId }: { courseId: string }) {
  const [papers, setPapers] = useState<ExamPaper[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<PaperDetailView | null>(null)

  const load = useCallback(() => {
    get<{ code: number; data: ExamPaper[] }>(`/courses/${courseId}/papers`)
      .then((r) => setPapers(r.data ?? []))
      .catch(() => setPapers([]))
  }, [courseId])

  const loadDetail = useCallback(
    (pid: string) => {
      Promise.all([
        get<ExamPaper>(`/papers/${pid}`),
        get<PaperStats>(`/papers/${pid}/stats`).catch(() => null),
      ])
        .then(([paper, stats]) => setDetail({ paper, stats }))
        .catch(() => setDetail(null))
    },
    [],
  )

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (selectedId) loadDetail(selectedId)
    else setDetail(null)
  }, [selectedId, loadDetail])

  async function createPaper() {
    const title = window.prompt('试卷标题')?.trim()
    if (!title) return
    try {
      await post(`/courses/${courseId}/papers`, { title, duration_minutes: 60 })
      track('exam.paper_create', { course_id: courseId })
      load()
    } catch (e) {
      alert(e instanceof Error ? e.message : '创建失败')
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <h2 className="section-title">试卷（{papers.length}）</h2>
        <button className="btn primary tiny" onClick={() => void createPaper()} data-track="exam-paper-new">
          ＋ 新建试卷
        </button>
      </div>

      <div className="form-grid">
        {papers.map((p) => (
          <div
            key={p.id}
            className="card"
            style={{
              cursor: 'pointer',
              borderColor: selectedId === p.id ? 'var(--primary)' : undefined,
              marginTop: 0,
            }}
            onClick={() => setSelectedId(p.id)}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <b>{p.title}</b>
              <span className={'pill' + (p.status === 'published' ? ' ok' : '')}>{PAPER_STATUS[p.status]}</span>
            </div>
            <div className="muted">
              {p.question_count} 题 · 满分 {p.total_score} · {p.duration_minutes} 分钟
            </div>
          </div>
        ))}
        {papers.length === 0 && <p className="muted">暂无试卷。</p>}
      </div>

      {!selectedId && !detail && <p className="muted" style={{ marginTop: 12 }}>选择一张试卷查看组卷、发布与统计。</p>}
      {detail && <PaperDetail courseId={courseId} view={detail} reload={load} reloadDetail={() => loadDetail(selectedId!)} />}
    </div>
  )
}

function PaperDetail({
  courseId,
  view,
  reload,
  reloadDetail,
}: {
  courseId: string
  view: PaperDetailView
  reload: () => void
  reloadDetail: () => void
}) {
  const { paper } = view
  const [banks, setBanks] = useState<ExamQuestion[]>([])
  const [pick, setPick] = useState('')
  const [pickScore, setPickScore] = useState(5)
  const [gen, setGen] = useState({ count: 5, difficulty: '', qtype: '' })
  const [attemptId, setAttemptId] = useState<string | null>(null)

  useEffect(() => {
    get<QuestionListResp>(`/courses/${courseId}/questions`)
      .then((r) => setBanks(r.data ?? []))
      .catch(() => setBanks([]))
  }, [courseId])

  const inPaper = new Set(paper.questions.map((q) => q.question_id))
  const bankPick = banks.filter((q) => !inPaper.has(q.id))

  async function addQuestion() {
    if (!pick) return
    try {
      await post(`/papers/${paper.id}/questions`, { question_id: pick, score: pickScore })
      track('exam.paper_add_question', { paper_id: paper.id })
      reloadDetail()
    } catch (e) {
      alert(e instanceof Error ? e.message : '加入失败')
    }
  }

  async function removeQuestion(pq: ExamPaperQuestion) {
    try {
      await del(`/papers/${paper.id}/questions/${pq.id}`)
      reloadDetail()
    } catch (e) {
      alert(e instanceof Error ? e.message : '移除失败')
    }
  }

  async function generate() {
    try {
      await post(`/papers/${paper.id}/generate`, {
        count: gen.count,
        difficulty: gen.difficulty || undefined,
        qtype_filter: gen.qtype || undefined,
      })
      track('exam.paper_generate', { paper_id: paper.id })
      reloadDetail()
    } catch (e) {
      alert(e instanceof Error ? e.message : '组卷失败')
    }
  }

  async function setPaperStatus(next: 'published' | 'closed') {
    const url = next === 'published' ? `/papers/${paper.id}/publish` : `/papers/${paper.id}/close`
    try {
      await post(url)
      track(`exam.paper_${next === 'published' ? 'publish' : 'close'}`, { paper_id: paper.id })
      reloadDetail()
    } catch (e) {
      alert(e instanceof Error ? e.message : '操作失败')
    }
  }

  async function removePaper() {
    if (!confirm(`删除试卷「${paper.title}」？作答记录将一并删除。`)) return
    try {
      await del(`/papers/${paper.id}`)
      reload()
      setAttemptId(null)
    } catch (e) {
      alert(e instanceof Error ? e.message : '删除失败')
    }
  }

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ margin: 0 }}>
            {paper.title} <span className="muted" style={{ fontSize: 13 }}>（{paper.question_count} 题 · {paper.total_score} 分 · {paper.duration_minutes} 分钟）</span>
          </h3>
          {paper.description && <div className="muted">{paper.description}</div>}
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {paper.status === 'published' && (
            <button className="btn tiny" onClick={() => void setPaperStatus('closed')}>关闭</button>
          )}
          {paper.status !== 'published' && (
            <button className="btn primary tiny" onClick={() => void setPaperStatus('published')} disabled={paper.question_count === 0}>
              发布
            </button>
          )}
          <button className="btn tiny" onClick={() => void removePaper()}>删除</button>
        </div>
      </div>

      <h4 className="muted" style={{ margin: '14px 0 8px' }}>📋 题目列表</h4>
      {paper.questions.map((pq, i) => (
        <div key={pq.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px dashed var(--border)' }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <span className="pill">{QTYPE_LABEL[pq.qtype]}</span>{' '}
            {i + 1}. {pq.title}
            <span className="muted"> · {pq.score} 分</span>
          </div>
          <button className="btn tiny" onClick={() => void removeQuestion(pq)}>移除</button>
        </div>
      ))}
      {paper.questions.length === 0 && <div className="muted">试卷为空，请加题或智能组卷。</div>}

      <div className="form-grid" style={{ marginTop: 14 }}>
        <label className="field">
          <span>从题库加题</span>
          <select value={pick} onChange={(e) => setPick(e.target.value)}>
            <option value="">选择题目…</option>
            {bankPick.map((q) => (
              <option key={q.id} value={q.id}>[{QTYPE_LABEL[q.qtype]}] {q.title}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>分值</span>
          <input type="number" min={1} max={100} value={pickScore} onChange={(e) => setPickScore(+e.target.value)} />
        </label>
        <div className="field">
          <span>&nbsp;</span>
          <button className="btn primary tiny" onClick={() => void addQuestion()} disabled={!pick}>加入</button>
        </div>
      </div>

      <div className="form-grid" style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
        <label className="field">
          <span>智能组卷数量</span>
          <input type="number" min={1} max={50} value={gen.count} onChange={(e) => setGen({ ...gen, count: +e.target.value })} />
        </label>
        <label className="field">
          <span>难度（可选）</span>
          <select value={gen.difficulty} onChange={(e) => setGen({ ...gen, difficulty: e.target.value })}>
            <option value="">不限</option>
            <option value="easy">易</option>
            <option value="medium">中</option>
            <option value="hard">难</option>
          </select>
        </label>
        <label className="field">
          <span>题型（可选）</span>
          <select value={gen.qtype} onChange={(e) => setGen({ ...gen, qtype: e.target.value })}>
            <option value="">不限</option>
            {Object.entries(QTYPE_LABEL).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </label>
        <div className="field">
          <span>&nbsp;</span>
          <button className="btn ghost tiny" onClick={() => void generate()}>✨ 智能组卷</button>
        </div>
      </div>

      <PaperAttempts paperId={paper.id} attemptId={attemptId} onOpen={setAttemptId} />
      <PaperStatsBlock stats={view.stats} />
    </div>
  )
}

function PaperAttempts({
  paperId,
  attemptId,
  onOpen,
}: {
  paperId: string
  attemptId: string | null
  onOpen: (id: string | null) => void
}) {
  const [attempts, setAttempts] = useState<{ id: string; student_name?: string | null; total_score: number; submitted_at?: string | null }[]>([])
  const [answers, setAnswers] = useState<{ question_id: string; answer: Array<string | { text: string }>; correct?: boolean | null; manual_score?: number | null }[] | null>(null)

  useEffect(() => {
    get<{ id: string; student_name?: string | null; total_score: number; submitted_at?: string | null }[]>(`/papers/${paperId}/attempts`)
      .then(setAttempts)
      .catch(() => setAttempts([]))
  }, [paperId])

  useEffect(() => {
    if (!attemptId) {
      setAnswers(null)
      return
    }
    get<{ answers?: typeof answers }>(`/attempts/${attemptId}`)
      .then((r) => setAnswers(r.answers ?? []))
      .catch(() => setAnswers([]))
  }, [attemptId])

  return (
    <div style={{ marginTop: 16 }}>
      <h4 className="muted" style={{ margin: '0 0 8px' }}>📝 提交记录（{attempts.length}）</h4>
      <div className="table">
        {attempts.map((a) => (
          <div key={a.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px dashed var(--border)' }}>
            <span><b>{a.student_name ?? '学生'}</b> <span className="muted">· {a.total_score} 分{attemptId === a.id ? '（查看中）' : ''}</span></span>
            <button className="btn ghost tiny" onClick={() => onOpen(attemptId === a.id ? null : a.id)}>
              {attemptId === a.id ? '收起' : '查看 / 评分'}
            </button>
          </div>
        ))}
        {attempts.length === 0 && <div className="muted">暂无提交。</div>}
      </div>

      {attemptId && <AttemptGrading attemptId={attemptId} answers={answers} onDone={() => onOpen(attemptId)} />}
    </div>
  )
}

function AttemptGrading({
  attemptId,
  answers,
  onDone,
}: {
  attemptId: string
  answers: { question_id: string; answer: Array<string | { text: string }>; correct?: boolean | null; manual_score?: number | null }[] | null
  onDone: () => void
}) {
  if (!answers) return null
  // 简答题人工评分
  const shorts = answers
    .map((a, i) => ({ ...a, idx: i }))
    .filter((a) => a.correct === null)

  return (
    <div className="card" style={{ marginTop: 8, background: 'var(--soft)' }}>
      <h4 style={{ margin: '0 0 8px' }}>答卷与人工评分</h4>
      {answers.map((a, i) => {
        const text = Array.isArray(a.answer)
          ? a.answer.map((v) => (typeof v === 'string' ? v : v.text)).join('，')
          : ''
        return (
          <div key={a.question_id} style={{ padding: '6px 0', borderBottom: '1px dashed var(--border)' }}>
            <span className="muted">第 {i + 1} 题：</span>{text || '—'}
            {a.correct === true && <span className="pill ok">正确</span>}
            {a.correct === false && <span className="pill" style={{ background: '#fdecea', color: '#c0392b' }}>错误</span>}
            {a.manual_score != null && <span className="muted"> · 人工 {a.manual_score} 分</span>}
          </div>
        )
      })}

      {shorts.length > 0 ? (
        shorts.map((s) => (
          <ShortGrade
            key={s.question_id}
            attemptId={attemptId}
            questionId={s.question_id}
            onDone={onDone}
          />
        ))
      ) : (
        <div className="muted">无待评分的主观题。</div>
      )}
    </div>
  )
}

// 主观题人工评分（教师）
function ShortGrade({
  attemptId,
  questionId,
  onDone,
}: {
  attemptId: string
  questionId: string
  onDone: () => void
}) {
  const [score, setScore] = useState(5)
  const [busy, setBusy] = useState(false)
  async function save() {
    setBusy(true)
    try {
      await post(`/attempts/${attemptId}/manual-grade`, { question_id: questionId, score })
      track('exam.manual_grade', { question_id: questionId })
      onDone()
    } catch (e) {
      alert(e instanceof Error ? e.message : '评分失败')
    } finally {
      setBusy(false)
    }
  }
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 6 }}>
      <input type="number" min={0} max={100} className="input" style={{ width: 80 }} value={score} onChange={(e) => setScore(+e.target.value)} />
      <button className="btn primary tiny" onClick={() => void save()} disabled={busy}>提交人工评分</button>
      <span className="muted" style={{ fontSize: 12 }}>（满分上限由试卷定义）</span>
    </div>
  )
}

function PaperStatsBlock({ stats }: { stats: PaperStats | null }) {
  if (!stats) return null
  return (
    <div style={{ marginTop: 16 }}>
      <h4 className="muted" style={{ margin: '0 0 8px' }}>
        📊 统计 · 提交 {stats.submitted_count} 人 · 平均 {stats.average_score} · 最高 {stats.highest_score} · 最低 {stats.lowest_score}
      </h4>
      <div className="table">
        {stats.question_stats.map((s) => (
          <div key={s.question_id} style={{ padding: '6px 0', display: 'flex', alignItems: 'center', gap: 10, borderBottom: '1px dashed var(--border)' }}>
            <span style={{ width: 30 }} className="pill">{QTYPE_LABEL[s.qtype]}</span>
            <span style={{ flex: 1, minWidth: 0, fontSize: 13 }}>{s.title}</span>
            <span style={{ width: 90, fontSize: 12 }} className="muted">
              {s.accuracy == null ? '待人工' : `${Math.round(s.accuracy * 100)}%`}（{s.correct_count}/{s.answered_count}）
            </span>
            <div className="bar-track" style={{ width: 120 }}>
              {s.accuracy != null && <div className="bar-fill" style={{ width: `${s.accuracy * 100}%` }} />}
            </div>
            {s.avg_manual_score != null && <span className="muted" style={{ fontSize: 12 }}>均 {s.avg_manual_score} 分</span>}
          </div>
        ))}
      </div>
    </div>
  )
}