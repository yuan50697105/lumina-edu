// Lumina 墨光 · 在线考试作答页（D-04）
//  学生：开始考试 → 逐题作答（单选/多选/判断/简答）→ 提交自动评分 → 查看得分
// 路由：/exam/:paperId
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { get, post } from '../api/client'
import type { AnswerValue, ExamAttempt, ExamPaper, ExamPaperQuestion, StartAttempt } from '../api/types'
import { track } from '../utils/tracker'

const QTYPE_LABEL: Record<string, string> = { single: '单选题', multiple: '多选题', true_false: '判断题', short_answer: '简答题' }

export default function ExamTaking() {
  const { paperId = '' } = useParams()
  const navigate = useNavigate()
  const [run, setRun] = useState<StartAttempt | null>(null)
  const [result, setResult] = useState<ExamAttempt | null>(null)
  const [courseId, setCourseId] = useState('')
  const [obj, setObj] = useState<Record<string, string[]>>({})     // 客观题：题号 → 选项
  const [short, setShort] = useState<Record<string, string>>({})   // 简答题：题号 → 文本
  const [deleting, setDeleting] = useState(false)
  const [started, setStarted] = useState(false)

  const load = useCallback(async () => {
    // 试卷信息（拿课程与返回入口）
    const paper = await get<ExamPaper>(`/papers/${paperId}`)
    setCourseId(paper.course_id)
    // 已提交 → 成绩
    const me = await get<{ my_attempt: ExamAttempt | null }>(`/papers/${paperId}/attempt/me`)
    if (me.my_attempt?.status === 'submitted') {
      setResult(me.my_attempt)
      return
    }
    // 未开始 / 进行中 → start（幂等，进行中返回原 attempt + 题目）
    const r = await post<StartAttempt>(`/papers/${paperId}/start`)
    setRun(r)
    setStarted(true)
  }, [paperId])

  useEffect(() => {
    track('exam.attempt_view', { paper_id: paperId })
    load().catch((e) => alert(e instanceof Error ? e.message : '加载失败'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paperId])

  function toggleOption(q: ExamPaperQuestion, key: string) {
    const cur = obj[q.question_id] ?? []
    if (q.qtype === 'multiple') {
      setObj({ ...obj, [q.question_id]: cur.includes(key) ? cur.filter((k) => k !== key) : [...cur, key] })
    } else {
      setObj({ ...obj, [q.question_id]: [key] })
    }
  }

  async function submit() {
    if (!run) return
    if (!confirm('确认提交作答？提交后不可修改。')) return
    setDeleting(true)
    try {
      const answers = run.questions.map((q): { question_id: string; answer: AnswerValue[] } => {
        if (q.qtype === 'short_answer') {
          return { question_id: q.question_id, answer: [{ text: short[q.question_id] ?? '' }] }
        }
        return { question_id: q.question_id, answer: obj[q.question_id] ?? [] }
      })
      const r = await post<ExamAttempt>(`/papers/${paperId}/submit`, { answers })
      track('exam.attempt_submit', { paper_id: paperId, score: r.total_score })
      setResult(r)
      setRun(null)
    } catch (e) {
      alert(e instanceof Error ? e.message : '提交失败，请重试')
    } finally {
      setDeleting(false)
    }
  }

  if (result) {
    const avg = result.question_count ? result.total_score / result.question_count : 0
    return (
      <div className="card" style={{ maxWidth: 720, margin: '40px auto' }}>
        <h1 className="page-title" style={{ fontSize: 24 }}>考试完成</h1>
        <p className="muted">{result.paper_title ?? '试卷'}</p>
        <div style={{ display: 'flex', gap: 30, margin: '18px 0' }}>
          <ScoreBox label="客观题" value={result.auto_score} />
          <ScoreBox label="主观题（人工）" value={result.manual_score} />
          <ScoreBox label="总分" value={result.total_score} hl={avg >= 0.6} />
        </div>
        {(result.answers ?? []).map((a, i) => {
          const text = (a.answer ?? []).map((v) => (typeof v === 'string' ? v : v.text)).join('，')
          const isShort = a.correct === null
          return (
            <div key={a.question_id} style={{ padding: '8px 0', borderBottom: '1px dashed var(--border)', fontSize: 14 }}>
              <span className="pill">{isShort ? '简答' : '客观'}</span>{' '}
              第 {i + 1} 题：{text || '未作答'}
              {a.correct === true && <span className="pill ok" style={{ marginLeft: 8 }}>正确</span>}
              {a.correct === false && <span className="pill" style={{ marginLeft: 8, background: '#fdecea', color: '#c0392b' }}>错误</span>}
              {a.manual_score != null && <span className="muted"> · 人工 {a.manual_score} 分</span>}
              {isShort && a.manual_score == null && <span className="muted"> · 待教师评分</span>}
            </div>
          )
        })}
        <button className="btn ghost" style={{ marginTop: 16 }} onClick={() => navigate(courseId ? `/courses/${courseId}` : '/')}>
          返回课程
        </button>
      </div>
    )
  }

  if (!run || !started) return <div className="muted">加载考试中…</div>

  return (
    <div style={{ maxWidth: 720, margin: '0 auto' }}>
      <div className="course-head" style={{ borderBottom: '1px solid var(--border)', paddingBottom: 14 }}>
        <div>
          <h1 className="page-title" style={{ fontSize: 24, marginBottom: 4 }}>{run.questions.length} 道题 · {run.duration_minutes} 分钟</h1>
          {run.end_at && <span className="muted">截止：{new Date(run.end_at).toLocaleString()}</span>}
        </div>
      </div>

      {run.questions.map((q, i) => (
        <div key={q.id} className="card">
          <div className="muted" style={{ fontSize: 12 }}>{QTYPE_LABEL[q.qtype]} · {q.score} 分</div>
          <b style={{ fontSize: 15 }}>{i + 1}. {q.title}</b>

          {q.qtype === 'short_answer' ? (
            <textarea
              className="input"
              rows={3}
              style={{ width: '100%', marginTop: 8 }}
              value={short[q.question_id] ?? ''}
              onChange={(e) => setShort({ ...short, [q.question_id]: e.target.value })}
              placeholder="请输入你的答案…"
            />
          ) : (
            <div style={{ marginTop: 10, display: 'grid', gap: 8 }}>
              {(q.options ?? []).map((opt) => {
                const active = (obj[q.question_id] ?? []).includes(opt.key)
                return (
                  <label
                    key={opt.key}
                    style={{
                      display: 'flex', gap: 8, alignItems: 'center', padding: '9px 12px',
                      border: `1px solid ${active ? 'var(--primary)' : 'var(--border)'}`,
                      borderRadius: 8, background: active ? 'var(--soft)' : '#fff', cursor: 'pointer',
                    }}
                  >
                    <input
                      type={q.qtype === 'multiple' ? 'checkbox' : 'radio'}
                      checked={active}
                      onChange={() => toggleOption(q, opt.key)}
                    />
                    <span>{opt.key}. {opt.text}</span>
                  </label>
                )
              })}
            </div>
          )}
        </div>
      ))}

      <div style={{ textAlign: 'right', margin: '16px 0 40px' }}>
        <button className="btn primary" onClick={() => void submit()} disabled={deleting}>
          {deleting ? '提交中…' : '提交作答'}
        </button>
      </div>
    </div>
  )
}

function ScoreBox({ label, value, hl }: { label: string; value: number; hl?: boolean }) {
  return (
    <div>
      <div style={{ fontSize: 26, fontWeight: 700, color: hl ? 'var(--ok)' : undefined }}>{value}</div>
      <div className="muted" style={{ fontSize: 12 }}>{label}</div>
    </div>
  )
}