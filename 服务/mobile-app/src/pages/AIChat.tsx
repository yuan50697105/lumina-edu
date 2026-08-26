// Lumina 墨光 · 移动端 AI 对话（流式 SSE via XMLHttpRequest）
import { useEffect, useState } from 'react'
import {
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'
import type { NativeStackScreenProps } from '@react-navigation/native-stack'
import { API_BASE } from '../config'
import { useAuthStore } from '../store/auth'
import { track, trackPageView } from '../utils/tracker'
import type { RootStackParamList } from '../navigation'

type Props = NativeStackScreenProps<RootStackParamList, 'AIChat'>

interface Msg {
  role: 'user' | 'assistant'
  content: string
  error?: boolean
  done?: boolean
}

/** RN fetch 不保证流式读取，改用 XMLHttpRequest 增量读 responseText */
function streamChat(
  body: Record<string, unknown>,
  token: string | null,
  on: { token: (s: string) => void; done: () => void; error: (e: Error) => void },
) {
  const xhr = new XMLHttpRequest()
  xhr.open('POST', `${API_BASE}/api/v1/ai/chat`)
  xhr.setRequestHeader('Content-Type', 'application/json')
  if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
  let buf = ''
  xhr.onreadystatechange = () => {
    if (xhr.status !== 200) return
    const text = xhr.responseText
    if (text.length > buf.length) {
      const tail = text.slice(buf.length)
      buf = text
      for (const line of tail.split('\n')) {
        const s = line.trim()
        if (!s.startsWith('data:')) continue
        try {
          const ev = JSON.parse(s.slice(5).trim())
          if (ev.type === 'token') on.token(ev.content ?? '')
          else if (ev.type === 'error') on.error(new Error(ev.message ?? 'AI 出错了'))
          else if (ev.type === 'done') on.done()
        } catch { /* 半包行忽略 */ }
      }
    }
  }
  xhr.onerror = () => on.error(new Error('网络错误'))
  xhr.addEventListener('load', () => {
    if (xhr.status !== 200) {
      let msg = `请求失败 (${xhr.status})`
      try {
        const j = JSON.parse(xhr.responseText)
        msg = j?.detail?.detail ?? j?.detail ?? msg
      } catch { /* ignore */ }
      on.error(new Error(String(msg)))
    }
  })
  xhr.send(JSON.stringify(body))
}

export default function AIChat({ route }: Props) {
  const conversationId = route.params?.conversationId
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const token = useAuthStore((s) => s.token)
  const [prevConvId, setPrevConvId] = useState<string | undefined>(undefined)

  useEffect(() => {
    trackPageView('ai_chat')
    if (conversationId && conversationId !== prevConvId) {
      setPrevConvId(conversationId)
      setBusy(true)
      getMessages(conversationId)
    }
  }, [conversationId])

  function getMessages(id: string) {
    fetch(`${API_BASE}/api/v1/ai/conversations/${id}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.json())
      .then((list: Array<{ role: string; content?: string | null }>) => {
        setMsgs(
          list
            .filter((m) => m.role === 'user' || m.role === 'assistant')
            .map((m) => ({ role: m.role as Msg['role'], content: m.content ?? '', done: true })),
        )
        setBusy(false)
      })
      .catch(() => setBusy(false))
  }

  function send() {
    const text = input.trim()
    if (!text || busy) return
    setInput('')
    setBusy(true)
    setMsgs((h) => [...h, { role: 'user', content: text }, { role: 'assistant', content: '' }])
    track('ai.chat.send', { conversation_id: conversationId, len: text.length })

    let acc = ''
    streamChat(
      { conversation_id: conversationId, message: text, max_tokens: 2048 },
      token,
      {
        token: (s) => {
          acc += s
          setMsgs((h) => {
            const copy = [...h]
            copy[copy.length - 1] = { role: 'assistant', content: acc, done: true }
            return copy
          })
        },
        done: () => {
          track('ai.chat.done', { conversation_id: conversationId, len: acc.length })
          setBusy(false)
        },
        error: (e) => {
          setMsgs((h) => {
            const copy = [...h]
            copy[copy.length - 1] = { role: 'assistant', content: e.message, error: true, done: true }
            return copy
          })
          setBusy(false)
        },
      },
    )
  }

  return (
    <View style={styles.wrap}>
      <FlatList
        style={{ flex: 1 }}
        data={msgs}
        keyExtractor={(_, i) => String(i)}
        contentContainerStyle={{ padding: 16, gap: 10 }}
        renderItem={({ item }) => (
          <View style={[styles.bubble, item.role === 'user' ? styles.userMsg : styles.aiMsg]}>
            <Text style={item.role === 'user' ? styles.userText : item.error ? styles.errorText : styles.aiText}>
              {item.content || '…思考中'}
            </Text>
          </View>
        )}
      />
      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          placeholder="向苏格拉底提问…"
          value={input}
          onChangeText={setInput}
          multiline
        />
        <Pressable style={styles.sendBtn} onPress={send} disabled={busy || !input.trim()}>
          <Text style={styles.sendText}>发送</Text>
        </Pressable>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: '#FAF6EC' },
  bubble: { maxWidth: '82%', borderRadius: 12, padding: 12 },
  userMsg: { alignSelf: 'flex-end', backgroundColor: '#3D46C9' },
  aiMsg: { alignSelf: 'flex-start', backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: '#EEE9DB' },
  userText: { color: '#FFFFFF', fontSize: 15 },
  aiText: { color: '#0F1020', fontSize: 15 },
  errorText: { color: '#E85D3A', fontSize: 15 },
  inputRow: {
    flexDirection: 'row', gap: 10, padding: 12, paddingBottom: 24,
    borderTopWidth: 1, borderTopColor: '#EEE9DB',
  },
  input: {
    flex: 1, minHeight: 44, maxHeight: 100, backgroundColor: '#FFFFFF',
    borderRadius: 10, paddingHorizontal: 14, paddingVertical: 10,
    borderWidth: 1, borderColor: '#D8D4C6',
  },
  sendBtn: {
    backgroundColor: '#7C3AED', borderRadius: 10, paddingHorizontal: 20,
    justifyContent: 'center',
  },
  sendText: { color: '#FFFFFF', fontWeight: '700' },
})