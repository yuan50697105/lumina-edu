// ============================================
// Lumina 墨光 · 埋点 SDK
// 页面访问 / 元素点击 → POST /api/v1/events（2.10 收集服务消费）
// fire-and-forget：失败不阻塞业务
// ============================================
import { BASE } from '../api/client'

const ENDPOINT = `${BASE}/events`
const SESSION_KEY = 'lumina_session_id'
const EVENT_QUEUE_KEY = 'lumina_events_pending'

function uid(): string {
  const c = crypto as unknown as { randomUUID?: () => string }
  return c.randomUUID ? c.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function sessionId(): string {
  let s = localStorage.getItem(SESSION_KEY)
  if (!s) {
    s = uid()
    localStorage.setItem(SESSION_KEY, s)
  }
  return s
}

export function currentUserId(): string | null {
  try {
    const raw = localStorage.getItem('lumina-auth')
    if (!raw) return null
    return (JSON.parse(raw)?.state?.user?.id ?? null) as string | null
  } catch {
    return null
  }
}

export interface TrackProps {
  [k: string]: unknown
}

export function track(eventName: string, props: TrackProps = {}) {
  const body = {
    event_name: eventName,
    user_id: currentUserId(),
    session_id: sessionId(),
    page_url: window.location.href,
    properties: props,
  }
  const payload = JSON.stringify(body)

  // 优先 sendBeacon（页面卸载不丢事件），失败回退 fetch keepalive，再失败排队重试
  try {
    if (navigator.sendBeacon) {
      const blob = new Blob([payload], { type: 'application/json' })
      if (navigator.sendBeacon(ENDPOINT, blob)) return
    }
  } catch { /* fallthrough */ }

  try {
    void fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: payload,
      keepalive: true,
    }).catch(() => enqueue(payload))
  } catch {
    enqueue(payload)
  }
}

function enqueue(payload: string) {
  try {
    const q = JSON.parse(localStorage.getItem(EVENT_QUEUE_KEY) ?? '[]') as string[]
    q.push(payload)
    localStorage.setItem(EVENT_QUEUE_KEY, JSON.stringify(q.slice(-50)))
  } catch { /* ignore */ }
}

export function flushPending() {
  try {
    const q = JSON.parse(localStorage.getItem(EVENT_QUEUE_KEY) ?? '[]') as string[]
    if (!q.length) return
    localStorage.removeItem(EVENT_QUEUE_KEY)
    for (const p of q) {
      void fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: p,
        keepalive: true,
      }).catch(() => enqueue(p))
    }
  } catch { /* ignore */ }
}

// ─── 全局点击埋点：data-track="按钮名" ───
export function initClickTracking() {
  window.addEventListener(
    'click',
    (e) => {
      const el = (e.target as HTMLElement | null)?.closest?.('[data-track]')
      const label = el?.getAttribute('data-track')
      if (label) track('element.click', { label })
    },
    true, // capture，保证先于业务 handler
  )
}