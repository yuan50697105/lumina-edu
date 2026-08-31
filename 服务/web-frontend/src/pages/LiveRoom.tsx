// ============================================
// Lumina 墨光 · 直播课堂房间页（D-01 · V1.1）
// 观看/举手/聊天/点名/答题 · 轮询实时（after_id 增量）
// 教师控制台与学员互动面板按角色渲染
// ============================================
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Hls from 'hls.js'
import { get, post, put } from '../api/client'
import type {
  LiveCallInfo,
  LiveMessage,
  LiveQuizResult,
  LiveRaise,
  LiveRoom,
} from '../api/types'
import { useAuthStore } from '../store/auth'
import { track } from '../utils/tracker'

const POLL_MSG_MS = 2500 // 消息增量轮询
const POLL_ROOM_MS = 5000 // 房间状态轮询

interface QuizBroadcast {
  type: 'quiz'
  quiz_id: string
  question: string
  options?: { key: string; text: string }[]
  status: string
}

function parseJsonMessage<T extends { type?: string }>(content: unknown, expectType: string): T | null {
  if (typeof content !== 'string') return null
  try {
    const j = JSON.parse(content) as T
    if (j && j.type === expectType) return j
  } catch {
    /* 纯文本系统消息 */
  }
  return null
}

function parseCall(content: unknown): LiveCallInfo | null {
  if (typeof content !== 'string') return null
  try {
    const j = JSON.parse(content) as LiveCallInfo
    if (j && j.user_id && j.name) return j
  } catch {
    /* ignore */
  }
  return null
}

const STATUS_LABEL: Record<string, string> = {
  scheduled: '未开始',
  live: '直播中',
  ended: '已结束',
}

export default function LiveRoomPage() {
  const { roomId = '' } = useParams()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)

  const [room, setRoom] = useState<LiveRoom | null>(null)
  const [loading, setLoading] = useState(true)
  const [joined, setJoined] = useState(false)
  const [messages, setMessages] = useState<LiveMessage[]>([])
  const [input, setInput] = useState('')
  const [raises, setRaises] = useState<LiveRaise[]>([])
  const [quiz, setQuiz] = useState<QuizBroadcast | null>(null)
  const [myChoice, setMyChoice] = useState<string | null>(null)
  const [quizResult, setQuizResult] = useState<LiveQuizResult | null>(null)
  const [showQuizForm, setShowQuizForm] = useState(false)
  const [quizQ, setQuizQ] = useState('')
  const [quizAnswer, setQuizAnswer] = useState('')
  const [options, setOptions] = useState(['', '', '', ''])
  const [call, setCall] = useState<LiveCallInfo | null>(null)
  const [raisedMe, setRaisedMe] = useState(false)
  const [msgError, setMsgError] = useState('')
  const [busy, setBusy] = useState('')

  const lastIdRef = useRef(0)
  const joinedRef = useRef(false)

  const isTeacher = !!user && !!room && (user.role === 'admin' || user.id === room.teacher_id)
  const isLive = room?.status === 'live'
  const isEnded = room?.status === 'ended'
  const called = call && call.user_id === user?.id

  // ─── 数据拉取 ───
  const loadRoom = useCallback(async () => {
    try {
      const r = await get<LiveRoom>(`/live/rooms/${roomId}`)
      setRoom(r)
      setCall(r.active_call ?? null)
    } catch {
      /* 轮询静默 */
    } finally {
      setLoading(false)
    }
  }, [roomId])

  const join = useCallback(async () => {
    try {
      await post(`/live/rooms/${roomId}/join`)
      joinedRef.current = true
      setJoined(true)
    } catch (e) {
      alert((e as Error).message)
      navigate('/') // 越权/课程不存在 → 回首页
    }
  }, [roomId, navigate])

  const leave = useCallback(async () => {
    try {
      await post(`/live/rooms/${roomId}/leave`)
    } catch {
      /* ignore */
    }
    joinedRef.current = false
    setJoined(false)
  }, [roomId])

  const pollMessages = useCallback(async () => {
    if (!joinedRef.current) return
    try {
      const msgs = await get<LiveMessage[]>(
        `/live/rooms/${roomId}/messages?after_id=${lastIdRef.current}&limit=100`,
      )
      if (msgs.length) {
        lastIdRef.current = msgs[msgs.length - 1].id
        setMessages((prev) => [...prev, ...msgs])
        for (const m of msgs) {
          if (m.msg_type === 'call') {
            const c = parseCall(m.content)
            if (c) setCall(c)
          } else if (m.msg_type === 'system') {
            const q = parseJsonMessage<QuizBroadcast>(m.content, 'quiz')
            if (q) {
              if (q.status === 'active') {
                setQuiz(q)
                setMyChoice(null)
                setQuizResult(null)
              } else if (q.status === 'closed') {
                setQuiz((prev) => (prev && prev.quiz_id === q.quiz_id ? { ...prev, status: 'closed' } : prev))
              }
            }
          }
        }
      }
    } catch {
      /* 静默等待下轮 */
    }
  }, [roomId])

  const pollRoom = useCallback(async () => {
    try {
      const r = await get<LiveRoom>(`/live/rooms/${roomId}`)
      setRoom(r)
      setCall(r.active_call ?? null)
    } catch {
      /* 静默 */
    }
  }, [roomId])

  // ─── 生命周期：加载 → 自动入会 → 开启轮询 ───
  useEffect(() => {
    void (async () => {
      await loadRoom()
      await join() // 幂等出席（可重入）
      setLoading(false)
    })()
    return () => {
      joinedRef.current = false
      void post(`/live/rooms/${roomId}/leave`).catch(() => undefined)
    }
  }, [roomId]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!joined) return
    const t1 = setInterval(() => void pollMessages(), POLL_MSG_MS)
    const t2 = setInterval(() => void pollRoom(), POLL_ROOM_MS)
    void pollMessages()
    return () => {
      clearInterval(t1)
      clearInterval(t2)
    }
  }, [joined, pollMessages, pollRoom])

  // 教师额外轮询举手队列
  useEffect(() => {
    if (!joined || !isTeacher) return
    const t = setInterval(async () => {
      try {
        const r = await get<LiveRaise[]>(`/live/rooms/${roomId}/raises`)
        setRaises(r ?? [])
      } catch {
        /* ignore */
      }
    }, POLL_ROOM_MS)
    return () => clearInterval(t)
  }, [joined, isTeacher, roomId])

  // 进入埋点（服务端 live.join 已埋，前端仅记录会话既入）
  useEffect(() => {
    track('live.room_view', { room_id: roomId })
  }, [roomId])

  // ─── 动作 ───
  async function sendMessage() {
    const content = input.trim()
    if (!content || isEnded) return
    try {
      await post(`/live/rooms/${roomId}/messages`, { msg_type: 'chat', content })
      setInput('')
    } catch (e) {
      setMsgError((e as Error).message)
    }
  }

  async function toggleRaise() {
    if (!joined) return alert('请先加入直播')
    setBusy('raise')
    const next = !raisedMe
    try {
      await put(`/live/rooms/${roomId}/raise`, { active: next })
      setRaisedMe(next)
    } catch (e) {
      alert((e as Error).message)
    } finally {
      setBusy('')
    }
  }

  async function startLive() {
    try {
      const r = await post<LiveRoom>(`/live/rooms/${roomId}/start`)
      setRoom(r)
    } catch (e) {
      alert((e as Error).message)
    }
  }

  async function endLive() {
    if (!confirm('确定结束直播？')) return
    try {
      await post(`/live/rooms/${roomId}/end`)
      const r = await get<LiveRoom>(`/live/rooms/${roomId}`)
      setRoom(r)
    } catch (e) {
      alert((e as Error).message)
    }
  }

  async function randomCall() {
    setBusy('call')
    try {
      await post(`/live/rooms/${roomId}/call`, { user_id: null })
    } catch (e) {
      alert((e as Error).message)
    } finally {
      setBusy('')
    }
  }

  async function respondCall() {
    try {
      await post(`/live/rooms/${roomId}/call/respond`)
      setCall(null)
    } catch (e) {
      alert((e as Error).message)
    }
  }

  async function publishQuiz() {
    const question = quizQ.trim()
    const opts = options
      .map((t, i) => ({ key: String.fromCharCode(65 + i), text: t.trim() }))
      .filter((o) => o.text)
    if (!question) return alert('请输入题目')
    if (opts.length < 2) return alert('至少两个选项')
    if (quizAnswer && !opts.some((o) => o.key === quizAnswer)) return alert('正确答案必须在选项中')
    try {
      await post(`/live/rooms/${roomId}/quizzes`, {
        question,
        options: opts,
        answer: quizAnswer || null,
      })
      setShowQuizForm(false)
      setQuizQ('')
      setQuizAnswer('')
      setOptions(['', '', '', ''])
    } catch (e) {
      alert((e as Error).message)
    }
  }

  async function submitChoice(key: string) {
    if (!quiz || quiz.status !== 'active') return
    try {
      await post(`/live/rooms/${roomId}/quizzes/${quiz.quiz_id}/answer`, { choice: key })
      setMyChoice(key)
    } catch (e) {
      alert((e as Error).message)
    }
  }

  async function closeQuiz() {
    if (!quiz) return
    try {
      await post(`/live/rooms/${roomId}/quizzes/${quiz.quiz_id}/close`)
      const res = await get<LiveQuizResult>(`/live/rooms/${roomId}/quizzes/${quiz.quiz_id}/result`)
      setQuizResult(res)
    } catch (e) {
      alert((e as Error).message)
    }
  }

  const myRaised = raisedMe

  if (loading && !room) return <div className="muted">加载直播间…</div>
  if (!room) return <div className="error">直播间不存在或无权访问</div>

  return (
    <div className="live-page">
      <div className="live-head">
        <div>
          <span className="course-code">{room.course_title ?? '课堂直播'}</span>
          <h1 className="page-title">{room.title}</h1>
          <p className="muted">
            {room.teacher_name ?? '教师'} · 状态{' '}
            <span className={`pill ${room.status === 'live' ? 'ok' : ''}`}>{STATUS_LABEL[room.status]}</span> ·{' '}
            在线 {room.online_count ?? 0} · 累计 {room.viewer_count ?? 0} 人次
            {room.started_at && ` · 开播 ${new Date(room.started_at).toLocaleTimeString('zh-CN')}`}
          </p>
        </div>
        <div className="live-actions">
          {joined ? (
            <button className="btn ghost" onClick={leave} data-track="live:leave">
              退出直播
            </button>
          ) : (
            <button className="btn primary" onClick={() => void join()} data-track="live:rejoin">
              重新加入
            </button>
          )}
          {isTeacher && !isLive && !isEnded && (
            <button className="btn primary" onClick={startLive} data-track="live:start">
              开播
            </button>
          )}
          {isTeacher && isLive && (
            <button className="btn ghost" onClick={endLive} data-track="live:end">
              结束直播
            </button>
          )}
        </div>
      </div>

      <div className="live-layout">
        {/* ── 左：视频 + 讲师控制 ── */}
        <div className="live-main">
          <LivePlayer url={room.stream_url} status={room.status} title={room.title} />

          <div className="live-stats">
            <span className="pill">👁 {room.viewer_count ?? 0} 观看</span>
            <span className={`pill ${isLive ? 'ok' : ''}`}>
              {isLive ? '🟢 直播中' : isEnded ? '⚪ 已结束' : '🕐 未开始'}
            </span>
            {call && <span className="pill">🎯 点名：{call.name}</span>}
          </div>

          {isTeacher ? (
            <TeacherPanel
              room={room}
              raises={raises}
              quiz={quiz}
              quizResult={quizResult}
              busy={busy}
              showQuizForm={showQuizForm}
              quizQ={quizQ}
              quizAnswer={quizAnswer}
              demoOptions={options}
              setShowQuizForm={setShowQuizForm}
              setQuizQ={setQuizQ}
              setQuizAnswer={setQuizAnswer}
              setDemoOptions={setOptions}
              onRandomCall={() => void randomCall()}
              onCloseQuiz={() => void closeQuiz()}
              onPublishQuiz={() => void publishQuiz()}
              onClearResult={() => setQuizResult(null)}
            />
          ) : (
            <div className="live-student-bar">
              <button
                className={`btn ${myRaised ? 'primary' : 'ghost'}`}
                onClick={() => void toggleRaise()}
                disabled={busy === 'raise' || isEnded}
                data-track="live:raise"
              >
                {myRaised ? '已举手（点击取消）' : '举手'}
              </button>
              {called ? (
                <button className="btn primary" onClick={() => void respondCall()} data-track="live:call_respond">
                  🙋 应答点名
                </button>
              ) : (
                <span className="muted">{isEnded ? '直播已结束' : '老师点名时可举手示意'}</span>
              )}
            </div>
          )}

          {msgError && <p className="error">{msgError}</p>}
        </div>

        {/* ── 右：聊天 ── */}
        <div className="live-chat">
          <div className="conv-head">互动消息</div>
          <div className="chat-stream">
            <div className="msgs">
              {messages.map((m) => (
                <MessageBubble key={m.id} msg={m} mine={m.user_id === user?.id} />
              ))}
              {messages.length === 0 && <p className="muted center">暂无消息，说点什么吧</p>}
            </div>
          </div>
          <div className="chat-input">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  void sendMessage()
                }
              }}
              placeholder={isEnded ? '直播已结束' : '发条消息…'}
              disabled={isEnded}
            />
            <button className="btn primary tiny" onClick={() => void sendMessage()} disabled={isEnded} data-track="live:chat">
              发送
            </button>
          </div>
        </div>
      </div>

      {/* ── 学生作答浮层 ── */}
      {!isTeacher && quiz && quiz.status === 'active' && (
        <div className="live-modal">
          <div className="modal-card">
            <h3>📝 {quiz.question}</h3>
            <div className="modal-options">
              {quiz.options?.map((o) => (
                <button
                  key={o.key}
                  className={`chip ${myChoice === o.key ? 'on' : ''}`}
                  disabled={!!myChoice}
                  onClick={() => void submitChoice(o.key)}
                  data-track="live:quiz_answer"
                >
                  <b>{o.key}.</b> {o.text}
                </button>
              ))}
            </div>
            {myChoice && <p className="muted">已提交选择 {myChoice} ✓（可等老师公布结果）</p>}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── 子组件：直播播放器 ───
function LivePlayer({ url, status, title }: { url?: string | null; status: string; title: string }) {
  const ref = useRef<HTMLVideoElement>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    const v = ref.current
    if (!v || status !== 'live' || !url || url.startsWith('mock://')) {
      setErr('')
      return
    }
    if (/^https?:\/\//.test(url)) {
      if (Hls.isSupported()) {
        const hls = new Hls()
        hls.loadSource(url)
        hls.attachMedia(v)
        hls.on(Hls.Events.ERROR, (_e, data) => {
          if (data.fatal) setErr('流加载失败（媒体服务器未接入或未推流）')
        })
        return () => hls.destroy()
      } else if (v.canPlayType('application/vnd.apple.mpegurl')) {
        v.src = url
        return () => {
          v.removeAttribute('src')
        }
      } else {
        setErr('当前浏览器不支持 HLS 播放')
      }
    }
  }, [url, status])

  return (
    <div className="live-player">
      <video ref={ref} playsInline controls className="live-video" />
      {status === 'live' && url?.startsWith('mock://') && (
        <div className="live-placeholder">
          <div className="live-radar">●</div>
          <p>🔴 直播信号占位</p>
          <p className="muted">{title} · 媒体服务器接入后在此播放画面</p>
        </div>
      )}
      {status === 'scheduled' && <div className="live-placeholder"><p>🕐 直播未开始</p></div>}
      {status === 'ended' && <div className="live-placeholder"><p>⚪ 直播已结束</p></div>}
      {err && <div className="live-placeholder"><p className="error">{err}</p></div>}
    </div>
  )
}

// ─── 教师面板 ───
function TeacherPanel(props: {
  room: LiveRoom
  raises: LiveRaise[]
  quiz: QuizBroadcast | null
  quizResult: LiveQuizResult | null
  busy: string
  showQuizForm: boolean
  quizQ: string
  quizAnswer: string
  demoOptions: string[]
  setShowQuizForm: (v: boolean) => void
  setQuizQ: (v: string) => void
  setQuizAnswer: (v: string) => void
  setDemoOptions: (v: string[]) => void
  onRandomCall: () => void
  onCloseQuiz: () => void
  onPublishQuiz: () => void
  onClearResult: () => void
}) {
  const {
    room, raises, quiz, quizResult, busy, showQuizForm,
    quizQ, quizAnswer, demoOptions,
    setShowQuizForm, setQuizQ, setQuizAnswer, setDemoOptions,
    onRandomCall, onCloseQuiz, onPublishQuiz, onClearResult,
  } = props

  return (
    <div className="teacher-panel">
      <div className="panel-row">
        <button className="btn ghost" onClick={onRandomCall} disabled={busy === 'call'} data-track="live:call">
          🎯 随机点名{room.active_call ? `（当前：${room.active_call.name}）` : ''}
        </button>
        <button className="btn ghost" onClick={() => setShowQuizForm(!showQuizForm)} data-track="live:quiz_start">
          📝 {quiz && quiz.status === 'active' ? '答题进行中' : '发起答题'}
        </button>
        {quiz && quiz.status === 'active' && (
          <button className="btn primary" onClick={onCloseQuiz} data-track="live:quiz_close">
            关闭作答并统计
          </button>
        )}
      </div>

      {showQuizForm && (
        <div className="quiz-form">
          <div className="field">
            <span>题目</span>
            <input value={quizQ} onChange={(e) => setQuizQ(e.target.value)} placeholder="如：下列哪个是正确答案？" />
          </div>
          <div className="quiz-opts-grid">
            {demoOptions.map((t, i) => (
              <div key={i} className="field">
                <span>选项 {String.fromCharCode(65 + i)}</span>
                <input value={t} onChange={(e) => { const n = [...demoOptions]; n[i] = e.target.value; setDemoOptions(n) }} placeholder={`选项 ${String.fromCharCode(65 + i)} 文本`} />
              </div>
            ))}
          </div>
          <div className="field">
            <span>正确答案（留空则不判对错）</span>
            <input value={quizAnswer} onChange={(e) => setQuizAnswer(e.target.value.toUpperCase())} placeholder="A / B / C / D" maxLength={1} />
          </div>
          <div className="panel-row">
            <button className="btn primary" onClick={onPublishQuiz} data-track="live:quiz_publish">
              发布答题
            </button>
            <button className="btn ghost" onClick={() => setShowQuizForm(false)}>取消</button>
          </div>
        </div>
      )}

      {quizResult && (
        <div className="quiz-result">
          <h3>答题统计 · {quizResult.question}</h3>
          <p className="muted">共 {quizResult.total} 人作答
            {quizResult.correct_rate != null && ` · 正确率 ${(quizResult.correct_rate * 100).toFixed(0)}%`}
          </p>
          <div className="result-bars">
            {Object.entries(quizResult.distribution).map(([k, n]) => (
              <div key={k} className="result-bar">
                <span className="mono">{k}</span>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${(n / Math.max(1, quizResult.total)) * 100}%` }} />
                </div>
                <span className="mono">{n}</span>
              </div>
            ))}
            {quizResult.total === 0 && <p className="muted">暂无作答记录</p>}
          </div>
          <button className="btn tiny ghost" onClick={onClearResult}>收起</button>
        </div>
      )}

      {quiz && quiz.status === 'active' && (
        <div className="quiz-live">
          <h3>📝 进行中：{quiz.question}</h3>
          <div className="chips">
            {quiz.options?.map((o) => (
              <span key={o.key} className="chip">
                <b>{o.key}.</b> {o.text}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="raise-queue">
        <h3>举手队列（{raises.length}）</h3>
        <div className="raise-list">
          {raises.map((r) => (
            <span key={r.id} className="raise-item">
              <span className="user-avatar">{r.name?.slice(0, 1) ?? '?'}</span>
              {r.name ?? '学员'}
            </span>
          ))}
          {raises.length === 0 && <span className="muted">暂无人举手</span>}
        </div>
        {raises.length > 0 && (
          <div className="raise-bars">
            {raises.slice(-3).map((r) => (
              <div key={r.id} className="raise-alert">
                🙋 <b>{r.name}</b> 举手了
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── 消息气泡 ───
function MessageBubble({ msg, mine }: { msg: LiveMessage; mine: boolean }) {
  if (msg.msg_type === 'system') {
    const quizMsg = parseJsonMessage<QuizBroadcast>(msg.content, 'quiz')
    if (quizMsg) {
      return (
        <div className="msg-system">
          {quizMsg.status === 'active'
            ? `📝 老师发布了答题：${quizMsg.question}`
            : `📊 答题结束：${quizMsg.question}`}
        </div>
      )
    }
    return <div className="msg-system">🔔 {msg.content}</div>
  }
  if (msg.msg_type === 'call') {
    const c = parseCall(msg.content)
    return <div className="msg-system call">🎤 点名：{c?.name ?? ''}</div>
  }
  return (
    <div className={`bubble ${mine ? 'mine' : 'peer'}`}>
      <small className="muted">{mine ? '我' : msg.user_name ?? '学员'}</small>
      <div>{msg.content}</div>
    </div>
  )
}