// ============================================
// Lumina 墨光 · 移动端直播课堂房间页（D-01 · V1.1）
// 观看 / 举手 / 聊天 / 点名 / 答题 · after_id 轮询（对齐 web-frontend/src/pages/LiveRoom.tsx）
// 教师控制台与学员互动面板按角色渲染；HLS 用 expo-video 原生播放（/media 同源反代需拼 API_BASE）
// ============================================
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ActivityIndicator,
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'
import { useVideoPlayer, VideoView } from 'expo-video'
import type { NativeStackScreenProps } from '@react-navigation/native-stack'
import { get, post, put } from '../api/client'
import type {
  LiveCallInfo,
  LiveMessage,
  LiveQuizResult,
  LiveRaise,
  LiveRoom,
} from '../api/types'
import { API_BASE } from '../config'
import { useAuthStore } from '../store/auth'
import { track, trackClick, trackPageView } from '../utils/tracker'
import type { RootStackParamList } from '../navigation'

const POLL_MSG_MS = 2500   // 消息增量轮询
const POLL_ROOM_MS = 5000  // 房间状态轮询

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

const STATUS_LABEL: Record<string, string> = { scheduled: '未开始', live: '直播中', ended: '已结束' }

type Props = NativeStackScreenProps<RootStackParamList, 'LiveRoom'>

export default function LiveRoomPage({ route, navigation }: Props) {
  const { roomId } = route.params
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

  useEffect(() => {
    navigation.setOptions({ title: room?.title ?? '直播课堂' })
  }, [room?.title, navigation])

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
      Alert.alert('无法加入', e instanceof Error ? e.message : '直播无权访问或不存在')
      navigation.goBack() // 越权/课程不存在 → 返回
    }
  }, [roomId, navigation])

  const leave = useCallback(async () => {
    try {
      await post(`/live/rooms/${roomId}/leave`)
    } catch {
      /* ignore */
    }
    joinedRef.current = false
    setJoined(false)
    navigation.goBack()
  }, [roomId, navigation])

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
    trackPageView('live_room')
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
      setMsgError(e instanceof Error ? e.message : '发送失败')
    }
  }

  async function toggleRaise() {
    if (!joined) return Alert.alert('提示', '请先加入直播')
    trackClick('live:raise')
    setBusy('raise')
    const next = !raisedMe
    try {
      await put(`/live/rooms/${roomId}/raise`, { active: next })
      setRaisedMe(next)
    } catch (e) {
      Alert.alert('操作失败', e instanceof Error ? e.message : '请重试')
    } finally {
      setBusy('')
    }
  }

  async function startLive() {
    trackClick('live:start')
    try {
      const r = await post<LiveRoom>(`/live/rooms/${roomId}/start`)
      setRoom(r)
    } catch (e) {
      Alert.alert('开播失败', e instanceof Error ? e.message : '请重试')
    }
  }

  function confirmEndLive() {
    Alert.alert('结束直播', '确定结束直播？', [
      { text: '取消', style: 'cancel' },
      {
        text: '结束',
        style: 'destructive',
        onPress: () => {
          void (async () => {
            trackClick('live:end')
            try {
              await post(`/live/rooms/${roomId}/end`)
              const r = await get<LiveRoom>(`/live/rooms/${roomId}`)
              setRoom(r)
            } catch (e) {
              Alert.alert('操作失败', e instanceof Error ? e.message : '请重试')
            }
          })()
        },
      },
    ])
  }

  async function randomCall() {
    trackClick('live:call')
    setBusy('call')
    try {
      await post(`/live/rooms/${roomId}/call`, { user_id: null })
    } catch (e) {
      Alert.alert('点名失败', e instanceof Error ? e.message : '请重试')
    } finally {
      setBusy('')
    }
  }

  async function respondCall() {
    trackClick('live:call_respond')
    try {
      await post(`/live/rooms/${roomId}/call/respond`)
      setCall(null)
    } catch (e) {
      Alert.alert('操作失败', e instanceof Error ? e.message : '请重试')
    }
  }

  async function submitChoice(key: string) {
    if (!quiz || quiz.status !== 'active') return
    trackClick('live:quiz_answer')
    try {
      await post(`/live/rooms/${roomId}/quizzes/${quiz.quiz_id}/answer`, { choice: key })
      setMyChoice(key)
    } catch (e) {
      Alert.alert('提交失败', e instanceof Error ? e.message : '请重试')
    }
  }

  async function publishQuiz() {
    const question = quizQ.trim()
    const opts = options
      .map((t, i) => ({ key: String.fromCharCode(65 + i), text: t.trim() }))
      .filter((o) => o.text)
    if (!question) return Alert.alert('提示', '请输入题目')
    if (opts.length < 2) return Alert.alert('提示', '至少两个选项')
    if (quizAnswer && !opts.some((o) => o.key === quizAnswer)) return Alert.alert('提示', '正确答案必须在选项中')
    trackClick('live:quiz_publish')
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
      Alert.alert('发布失败', e instanceof Error ? e.message : '请重试')
    }
  }

  async function closeQuiz() {
    if (!quiz) return
    trackClick('live:quiz_close')
    try {
      await post(`/live/rooms/${roomId}/quizzes/${quiz.quiz_id}/close`)
      const res = await get<LiveQuizResult>(`/live/rooms/${roomId}/quizzes/${quiz.quiz_id}/result`)
      setQuizResult(res)
    } catch (e) {
      Alert.alert('操作失败', e instanceof Error ? e.message : '请重试')
    }
  }

  if (loading && !room) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color="#3D46C9" />
        <Text style={styles.muted}>加载直播间…</Text>
      </View>
    )
  }
  if (!room) {
    return (
      <View style={styles.center}>
        <Text style={styles.error}>直播间不存在或无权访问</Text>
      </View>
    )
  }

  const streamSource = resolveVideoSource(room.stream_url, room.status)

  return (
    <KeyboardAvoidingView style={styles.wrap} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      {/* ── 头部信息 ── */}
      <View style={styles.head}>
        <View style={{ flex: 1 }}>
          <Text style={styles.code}>{room.course_title ?? '课堂直播'}</Text>
          <Text style={styles.title} numberOfLines={1}>{room.title}</Text>
          <Text style={styles.meta}>
            {room.teacher_name ?? '教师'} · {STATUS_LABEL[room.status]} · 在线 {room.online_count ?? 0}
          </Text>
        </View>
        {isTeacher && !isLive && !isEnded && (
          <Pressable style={styles.btnPrimary} onPress={() => void startLive()}>
            <Text style={styles.btnPrimaryText}>开播</Text>
          </Pressable>
        )}
        {isTeacher && isLive && (
          <Pressable style={styles.btnGhost} onPress={confirmEndLive}>
            <Text style={styles.btnText}>结束</Text>
          </Pressable>
        )}
        {!isTeacher && (
          <Pressable style={styles.btnGhost} onPress={() => void leave()}>
            <Text style={styles.btnText}>退出</Text>
          </Pressable>
        )}
      </View>

      <ScrollView style={{ flex: 1 }} contentContainerStyle={{ padding: 16, paddingBottom: 8 }}>
        {/* ── 视频区 ── */}
        <VideoBox source={streamSource} status={room.status} title={room.title} />

        <View style={styles.statRow}>
          <Text style={styles.pill}>👁 {room.viewer_count ?? 0} 观看</Text>
          <Text style={[styles.pill, isLive && styles.pillLive]}>{isLive ? '🟢 直播中' : isEnded ? '⚪ 已结束' : '🕐 未开始'}</Text>
          {call && <Text style={styles.pill}>🎯 点名：{call.name}</Text>}
        </View>

        {call && !isTeacher && (
          <Pressable style={styles.callBanner} onPress={() => void respondCall()}>
            <Text style={styles.callText}>🙋 老师点名「{call.name}」→ 应答</Text>
          </Pressable>
        )}

        {/* ── 教师控制台 ── */}
        {isTeacher && (
          <TeacherPanel
            room={room}
            raises={raises}
            quiz={quiz}
            quizResult={quizResult}
            busy={busy}
            showQuizForm={showQuizForm}
            quizQ={quizQ}
            quizAnswer={quizAnswer}
            options={options}
            setShowQuizForm={setShowQuizForm}
            setQuizQ={setQuizQ}
            setQuizAnswer={setQuizAnswer}
            setOptions={setOptions}
            onRandomCall={() => void randomCall()}
            onCloseQuiz={() => void closeQuiz()}
            onPublishQuiz={() => void publishQuiz()}
            onClearResult={() => setQuizResult(null)}
          />
        )}

        {/* ── 学生互动栏 ── */}
        {!isTeacher && (
          <View style={styles.studentBar}>
            <Pressable
              style={[raisedMe ? styles.btnPrimary : styles.btnGhost, { flex: 1 }]}
              onPress={() => void toggleRaise()}
              disabled={busy === 'raise' || isEnded}
            >
              <Text style={raisedMe ? styles.btnPrimaryText : styles.btnText}>
                {raisedMe ? '已举手（点取消）' : '举手'}
              </Text>
            </Pressable>
            {!call && (
              <Text style={[styles.muted, { flex: 1.2, textAlign: 'center' }]}>
                {isEnded ? '直播已结束' : '老师点名时可举手示意'}
              </Text>
            )}
          </View>
        )}

        {msgError && <Text style={styles.error}>{msgError}</Text>}
      </ScrollView>

      {/* ── 聊天区 ── */}
      <View style={styles.chatWrap}>
        <Text style={styles.chatHead}>互动消息</Text>
        <FlatList
          style={{ flex: 1 }}
          contentContainerStyle={{ paddingHorizontal: 12, paddingVertical: 8, gap: 6 }}
          data={messages}
          inverted
          keyExtractor={(m) => String(m.id)}
          renderItem={({ item }) => <MessageBubble msg={item} mine={item.user_id === user?.id} />}
          ListEmptyComponent={<Text style={[styles.muted, { textAlign: 'center' }]}>暂无消息，说点什么吧</Text>}
        />
        <View style={styles.chatInputRow}>
          <TextInput
            style={styles.chatInput}
            value={input}
            onChangeText={setInput}
            placeholder={isEnded ? '直播已结束' : '发条消息…'}
            editable={!isEnded}
            onSubmitEditing={() => void sendMessage()}
            returnKeyType="send"
          />
          <Pressable style={styles.sendBtn} onPress={() => void sendMessage()} disabled={isEnded}>
            <Text style={styles.sendText}>发送</Text>
          </Pressable>
        </View>
      </View>

      {/* ── 学生作答浮层 ── */}
      {!isTeacher && quiz && quiz.status === 'active' && (
        <QuestionModal
          quiz={quiz}
          myChoice={myChoice}
          onSubmit={submitChoice}
        />
      )}
    </KeyboardAvoidingView>
  )
}

// ─── 视频地址解析 ───
function resolveVideoSource(url?: string | null, status?: string): string | null {
  if (status !== 'live' || !url || url.startsWith('mock://')) return null
  if (url.startsWith('/media')) return `${API_BASE}${url}` // 开发演示同源反代
  return url
}

// ─── 视频播放器（expo-video · 原生 HLS） ───
function VideoBox({ source, status, title }: { source: string | null; status: string; title: string }) {
  const player = useVideoPlayer(null, (p) => {
    p.loop = false
  })
  const [err, setErr] = useState('')

  // HLS 源变化时加载新流（开播 / 切流）；空源暂停
  useEffect(() => {
    if (!source) {
      player.pause()
      return
    }
    try {
      player.replace(source)
    } catch {
      setErr('流加载失败（媒体服务器未接入或未推流）')
    }
  }, [player, source])

  return (
    <View style={styles.videoBox}>
      {source ? (
        <VideoView player={player} style={styles.video} contentFit="contain" nativeControls />
      ) : (
        <View style={styles.placeholder}>
          {status === 'live' && <Text style={styles.phLive}>🔴 直播信号占位</Text>}
          {status === 'scheduled' && <Text>🕐 直播未开始</Text>}
          {status === 'ended' && <Text>⚪ 直播已结束</Text>}
          <Text style={styles.muted}>{title} · 媒体服务器接入后在此播放画面</Text>
        </View>
      )}
      {err && <Text style={[styles.error, { position: 'absolute', bottom: 8, left: 12 }]}>{err}</Text>}
    </View>
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
  options: string[]
  setShowQuizForm: (v: boolean) => void
  setQuizQ: (v: string) => void
  setQuizAnswer: (v: string) => void
  setOptions: (v: string[]) => void
  onRandomCall: () => void
  onCloseQuiz: () => void
  onPublishQuiz: () => void
  onClearResult: () => void
}) {
  const {
    room, raises, quiz, quizResult, busy, showQuizForm,
    quizQ, quizAnswer, options,
    setShowQuizForm, setQuizQ, setQuizAnswer, setOptions,
    onRandomCall, onCloseQuiz, onPublishQuiz, onClearResult,
  } = props

  return (
    <View style={styles.teacherPanel}>
      <View style={styles.panelRow}>
        <Pressable style={styles.btnGhost} onPress={onRandomCall} disabled={busy === 'call'}>
          <Text style={styles.btnText}>
            🎯 随机点名{room.active_call ? `（当前：${room.active_call.name}）` : ''}
          </Text>
        </Pressable>
        <Pressable style={styles.btnGhost} onPress={() => setShowQuizForm(!showQuizForm)}>
          <Text style={styles.btnText}>{quiz && quiz.status === 'active' ? '📝 答题进行中' : '📝 发起答题'}</Text>
        </Pressable>
        {quiz && quiz.status === 'active' && (
          <Pressable style={styles.btnPrimary} onPress={onCloseQuiz}>
            <Text style={styles.btnPrimaryText}>关闭并统计</Text>
          </Pressable>
        )}
      </View>

      {showQuizForm && (
        <View style={styles.quizForm}>
          <Text style={styles.fieldLabel}>题目</Text>
          <TextInput style={styles.input} value={quizQ} onChangeText={setQuizQ} placeholder="如：下列哪个是正确答案？" />
          {options.map((t, i) => (
            <View key={i} style={styles.optRow}>
              <Text style={styles.fieldLabel}>选项 {String.fromCharCode(65 + i)}</Text>
              <TextInput
                style={[styles.input, { flex: 1 }]}
                value={t}
                onChangeText={(v) => { const n = [...options]; n[i] = v; setOptions(n) }}
                placeholder={`选项 ${String.fromCharCode(65 + i)} 文本`}
              />
            </View>
          ))}
          <Text style={styles.fieldLabel}>正确答案（留空则不判对错）</Text>
          <TextInput
            style={styles.input}
            value={quizAnswer}
            onChangeText={(v) => setQuizAnswer(v.toUpperCase())}
            placeholder="A / B / C / D"
            maxLength={1}
            autoCapitalize="characters"
          />
          <View style={styles.panelRow}>
            <Pressable style={styles.btnPrimary} onPress={onPublishQuiz}>
              <Text style={styles.btnPrimaryText}>发布答题</Text>
            </Pressable>
            <Pressable style={styles.btnGhost} onPress={() => setShowQuizForm(false)}>
              <Text style={styles.btnText}>取消</Text>
            </Pressable>
          </View>
        </View>
      )}

      {quizResult && (
        <View style={styles.quizResult}>
          <Text style={styles.subTitle}>📊 答题统计 · {quizResult.question}</Text>
          <Text style={styles.muted}>
            共 {quizResult.total} 人作答
            {quizResult.correct_rate != null && ` · 正确率 ${(quizResult.correct_rate * 100).toFixed(0)}%`}
          </Text>
          {Object.entries(quizResult.distribution).map(([k, n]) => (
            <View key={k} style={styles.resultRow}>
              <Text style={styles.mono}>{k}</Text>
              <View style={styles.barTrack}>
                <View style={[styles.barFill, { width: `${(n / Math.max(1, quizResult.total)) * 100}%` as `${number}%` }]} />
              </View>
              <Text style={styles.mono}>{n}</Text>
            </View>
          ))}
          {quizResult.total === 0 && <Text style={styles.muted}>暂无作答记录</Text>}
          <Pressable onPress={onClearResult}>
            <Text style={styles.link}>收起</Text>
          </Pressable>
        </View>
      )}

      <View style={styles.raiseQueue}>
        <Text style={styles.subTitle}>🙋 举手队列（{raises.length}）</Text>
        <View style={styles.raiseRow}>
          {raises.map((r) => (
            <View key={r.id} style={styles.raiseChip}>
              <Text style={styles.raiseChipText}>{r.name ?? '学员'}</Text>
            </View>
          ))}
          {raises.length === 0 && <Text style={styles.muted}>暂无人举手</Text>}
        </View>
      </View>
    </View>
  )
}

// ─── 学生作答浮层 ───
function QuestionModal({
  quiz, myChoice, onSubmit,
}: {
  quiz: QuizBroadcast
  myChoice: string | null
  onSubmit: (key: string) => Promise<void>
}) {
  return (
    <Modal transparent animationType="fade" visible>
      <View style={styles.modalMask}>
        <View style={styles.modalCard}>
          <Text style={styles.subTitle}>📝 {quiz.question}</Text>
          {quiz.options?.map((o) => (
            <Pressable
              key={o.key}
              style={[styles.optBtn, myChoice === o.key && styles.optBtnOn]}
              disabled={!!myChoice}
              onPress={() => void onSubmit(o.key)}
            >
              <Text style={[styles.optBtnText, myChoice === o.key && styles.optBtnTextOn]}>
                <Text style={{ fontWeight: '800' }}>{o.key}.</Text> {o.text}
              </Text>
            </Pressable>
          ))}
          {myChoice && <Text style={styles.muted}>已提交选择 {myChoice} ✓（可等老师公布结果）</Text>}
        </View>
      </View>
    </Modal>
  )
}

// ─── 消息气泡 ───
function MessageBubble({ msg, mine }: { msg: LiveMessage; mine: boolean }) {
  if (msg.msg_type === 'system') {
    const quizMsg = parseJsonMessage<QuizBroadcast>(msg.content, 'quiz')
    if (quizMsg) {
      return (
        <View style={styles.msgSystem}>
          <Text style={styles.msgSystemText}>
            {quizMsg.status === 'active' ? `📝 老师发布了答题：${quizMsg.question}` : `📊 答题结束：${quizMsg.question}`}
          </Text>
        </View>
      )
    }
    return (
      <View style={styles.msgSystem}>
        <Text style={styles.msgSystemText}>🔔 {msg.content}</Text>
      </View>
    )
  }
  if (msg.msg_type === 'call') {
    const c = parseCall(msg.content)
    return (
      <View style={styles.msgSystem}>
        <Text style={styles.msgSystemText}>🎤 点名：{c?.name ?? ''}</Text>
      </View>
    )
  }
  return (
    <View style={[styles.bubble, mine ? styles.bubbleMine : styles.bubblePeer]}>
      <Text style={styles.bubbleName}>{mine ? '我' : msg.user_name ?? '学员'}</Text>
      <Text style={styles.bubbleText}>{msg.content}</Text>
    </View>
  )
}

// ─── 样式（Lumina 设计体系 token） ───
const c = { paper: '#FAF6EC', ink: '#0F1020', cobalt: '#3D46C9', highlighter: '#F5B800', growth: '#2A7F4F', ai: '#7C3AED', line: '#EEE9DB', muted: '#6B6E85' }

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: c.paper },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: c.paper },
  head: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 16, paddingBottom: 8 },
  code: { color: c.cobalt, fontSize: 12, fontWeight: '700' },
  title: { color: c.ink, fontSize: 20, fontWeight: '800', marginTop: 2 },
  meta: { color: c.muted, fontSize: 12, marginTop: 4 },
  btnPrimary: { backgroundColor: c.cobalt, borderRadius: 8, paddingHorizontal: 16, paddingVertical: 10, alignItems: 'center' },
  btnPrimaryText: { color: c.paper, fontSize: 14, fontWeight: '700' },
  btnGhost: { backgroundColor: 'transparent', borderRadius: 8, borderWidth: 1, borderColor: c.line, paddingHorizontal: 14, paddingVertical: 10, alignItems: 'center' },
  btnText: { color: c.ink, fontSize: 14, fontWeight: '600' },
  videoBox: { aspectRatio: 16 / 9, borderRadius: 12, overflow: 'hidden', backgroundColor: '#000' },
  video: { width: '100%', height: '100%' },
  placeholder: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 6 },
  phLive: { color: '#F5B800', fontWeight: '800', fontSize: 16 },
  statRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 10 },
  pill: { backgroundColor: '#fff', borderColor: c.line, borderWidth: 1, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4, fontSize: 12, color: c.ink, overflow: 'hidden' },
  pillLive: { color: c.growth, fontWeight: '700' },
  callBanner: { backgroundColor: c.highlighter, borderRadius: 10, padding: 12, marginTop: 10 },
  callText: { color: c.ink, fontWeight: '800', fontSize: 14 },
  studentBar: { flexDirection: 'row', alignItems: 'center', gap: 12, marginTop: 12 },
  teacherPanel: { marginTop: 12, gap: 10 },
  panelRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, alignItems: 'center' },
  quizForm: { backgroundColor: '#fff', borderRadius: 10, borderWidth: 1, borderColor: c.line, padding: 12, gap: 6 },
  fieldLabel: { fontSize: 12, color: c.muted, fontWeight: '600', marginTop: 4 },
  input: { borderWidth: 1, borderColor: c.line, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 8, fontSize: 14, color: c.ink, backgroundColor: '#fff' },
  optRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  quizResult: { backgroundColor: '#fff', borderRadius: 10, borderWidth: 1, borderColor: c.line, padding: 12, gap: 6 },
  subTitle: { fontSize: 15, fontWeight: '800', color: c.ink },
  resultRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  barTrack: { flex: 1, height: 10, backgroundColor: c.line, borderRadius: 5, overflow: 'hidden' },
  barFill: { height: '100%', backgroundColor: c.cobalt, borderRadius: 5 },
  mono: { fontFamily: 'monospace', fontSize: 12, color: c.ink, minWidth: 18 },
  link: { color: c.cobalt, fontWeight: '700', fontSize: 13, marginTop: 4 },
  raiseQueue: { marginTop: 4, gap: 8 },
  raiseRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  raiseChip: { backgroundColor: '#fff', borderRadius: 8, borderWidth: 1, borderColor: c.line, paddingHorizontal: 10, paddingVertical: 6 },
  raiseChipText: { fontSize: 13, color: c.ink },
  chatWrap: { height: 210, borderTopWidth: 1, borderTopColor: c.line, backgroundColor: '#fff' },
  chatHead: { paddingHorizontal: 12, paddingTop: 8, fontSize: 12, fontWeight: '700', color: c.muted },
  chatInputRow: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 10, borderTopWidth: 1, borderTopColor: c.line },
  chatInput: { flex: 1, borderWidth: 1, borderColor: c.line, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 8, fontSize: 14, color: c.ink },
  sendBtn: { backgroundColor: c.cobalt, borderRadius: 8, paddingHorizontal: 16, paddingVertical: 9 },
  sendText: { color: '#fff', fontSize: 14, fontWeight: '700' },
  bubble: { alignSelf: 'flex-start', maxWidth: '80%', borderRadius: 10, paddingHorizontal: 10, paddingVertical: 6 },
  bubbleMine: { alignSelf: 'flex-end', backgroundColor: c.cobalt, borderBottomRightRadius: 2 },
  bubblePeer: { backgroundColor: '#F0EDE0', borderBottomLeftRadius: 2 },
  bubbleName: { fontSize: 10, color: c.muted, marginBottom: 2 },
  bubbleText: { fontSize: 14, color: c.ink },
  msgSystem: { alignSelf: 'center', backgroundColor: 'rgba(245,184,0,0.18)', borderRadius: 999, paddingHorizontal: 12, paddingVertical: 4, marginVertical: 2 },
  msgSystemText: { fontSize: 12, color: c.ink },
  modalMask: { flex: 1, backgroundColor: 'rgba(15,16,32,0.5)', alignItems: 'center', justifyContent: 'center', padding: 24 },
  modalCard: { width: '100%', backgroundColor: c.paper, borderRadius: 16, padding: 20, gap: 10 },
  optBtn: { borderWidth: 1, borderColor: c.line, borderRadius: 10, padding: 12, backgroundColor: '#fff' },
  optBtnOn: { backgroundColor: c.cobalt, borderColor: c.cobalt },
  optBtnText: { fontSize: 15, color: c.ink },
  optBtnTextOn: { color: '#fff' },
  error: { color: '#B3261E', fontSize: 13, marginTop: 6 },
  muted: { color: c.muted, fontSize: 13 },
})