import { useEffect, useRef, useState } from 'react'
import { get, post } from '../api/client'
import type { ChatEvent, Conversation, ConversationMessage } from '../api/types'
import { track } from '../utils/tracker'
import type { ReactNode } from 'react'

interface LocalMsg {
  role: 'user' | 'assistant'
  content: string
  error?: boolean
}

export default function AIChat() {
  const [convs, setConvs] = useState<Conversation[]>([])
  const [current, setCurrent] = useState<string | null>(null)
  const [convHistory, setConvHistory] = useState<LocalMsg[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    get<Conversation[]>('/ai/conversations?limit=30')
      .then((list) => setConvs(list ?? []))
      .catch(() => {})
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [convHistory])

  async function loadConversation(id: string) {
    const msgs = (await get<ConversationMessage[]>(`/ai/conversations/${id}`).catch(() => [])) ?? []
    setCurrent(id)
    setConvHistory(
      msgs.filter((m) => m.role === 'user' || m.role === 'assistant').map((m) => ({
        role: m.role as 'user' | 'assistant',
        content: m.content ?? '',
      })),
    )
  }

  async function send() {
    const text = input.trim()
    if (!text || busy) return
    setInput('')
    setBusy(true)
    setConvHistory((h) => [...h, { role: 'user', content: text }])
    setConvHistory((h) => [...h, { role: 'assistant', content: '', error: false }])

    track('ai.chat.send', { conversation_id: current, len: text.length })

    const tokens = useAuthStoreToken()
    try {
      const resp = await fetch('/api/v1/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(tokens ? { Authorization: `Bearer ${tokens}` } : {}),
        },
        body: JSON.stringify({
          conversation_id: current,
          message: text,
          max_tokens: 2048,
        }),
      })
      if (!resp.ok || !resp.body) {
        const j = await resp.json().catch(() => ({}))
        const detail = typeof j?.detail === 'string' ? j.detail : j?.detail?.detail ?? JSON.stringify(j)
        throw new Error(`对话失败 (${resp.status})：${detail}`)
      }

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop() ?? ''
        for (const line of lines) {
          const s = line.trim()
          if (!s.startsWith('data:')) continue
          const data = s.slice(5).trim()
          if (!data) continue
          let ev: ChatEvent
          try {
            ev = JSON.parse(data) as ChatEvent
          } catch {
            continue
          }
          if (ev.type === 'token') {
            updateAssistant(ev.content ?? '')
          } else if (ev.type === 'done') {
            if (ev.conversation_id) setCurrent(ev.conversation_id)
            // 刷新会话列表
            get<Conversation[]>('/ai/conversations?limit=30')
              .then((list) => setConvs(list ?? []))
              .catch(() => {})
            track('ai.chat.done', { conversation_id: ev.conversation_id })
          } else if (ev.type === 'error') {
            updateAssistantError(ev.message ?? 'AI 回复出错')
          }
        }
      }
    } catch (e) {
      updateAssistantError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  function useAuthStoreToken(): string | null {
    try {
      const raw = localStorage.getItem('lumina-auth')
      return raw ? (JSON.parse(raw)?.state?.token ?? null) : null
    } catch {
      return null
    }
  }

  // 追加/更新正在生成的最后一条 assistant 消息
  function updateAssistant(append: string) {
    setConvHistory((h) => {
      const next = [...h]
      const last = next[next.length - 1]
      if (last?.role === 'assistant') {
        next[next.length - 1] = { ...last, content: last.content + append }
      } else {
        next.push({ role: 'assistant', content: append })
      }
      return next
    })
  }

  function updateAssistantError(message: string) {
    setConvHistory((h) => {
      const next = [...h]
      const last = next[next.length - 1]
      if (last?.role === 'assistant') {
        next[next.length - 1] = { ...last, error: true, content: last.content || message }
      } else {
        next.push({ role: 'assistant', content: message, error: true })
      }
      return next
    })
  }

  function newConv() {
    setCurrent(null)
    setConvHistory([])
  }

  const bubbles: ReactNode[] = convHistory.map((m, i) => (
    <div key={i} className={`bubble ${m.role}${m.error ? ' error' : ''}`}>
      {m.content === '' && m.role === 'assistant' && !busy ? '（等待回复…）' : m.content}
    </div>
  ))

  return (
    <div className="chat-layout">
      <aside className="conv-side">
        <div className="conv-head">
          <span>对话历史</span>
          <button className="btn tiny" onClick={newConv} data-track="chat:new">
            新对话
          </button>
        </div>
        <div className="conv-list">
          {convs.map((c) => (
            <button
              key={c.id}
              className={`conv-item${current === c.id ? ' active' : ''}`}
              onClick={() => loadConversation(c.id)}
              title={`${c.message_count} 条 · ${c.total_tokens} tokens`}
            >
              <b>{c.title ?? '（无标题）'}</b>
              <small>{c.model ?? ''}</small>
            </button>
          ))}
          {convs.length === 0 && <p className="muted">暂无历史</p>}
        </div>
      </aside>
      <div className="chat-main">
        <div className="chat-stream">
          <p className="muted center">🎓 苏格拉底导师 —— 不会直接给答案，而是引导你思考</p>
          <div className="msgs">
            {bubbles}
            <div ref={endRef} />
          </div>
        </div>
        <div className="chat-input">
          <textarea
            value={input}
            rows={2}
            placeholder="这个积分怎么解？按 Enter 发送，Shift+Enter 换行"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                void send()
              }
            }}
          />
          <button className="btn primary" disabled={busy || !input.trim()} onClick={() => void send()} data-track="chat:send">
            {busy ? '思考中…' : '发送'}
          </button>
        </div>
      </div>
    </div>
  )
}