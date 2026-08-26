// ============================================
// Lumina 墨光 · 移动端埋点 SDK
// 契约与 Web 端 tracker.ts 一致：POST /api/v1/events（event_tracking 表）
// RN 无 sendBeacon/localStorage：
//   - 上报用 fetch keepalive 语义（fetch 无缓存）；
//   - 失败进内存队列，下次上报前 flush（进程内重试）。
// ============================================
import { API_BASE } from '../config'
import { useAuthStore } from '../store/auth'

let sessionId: string | null = null

function uuid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}

function getSessionId(): string {
  if (!sessionId) sessionId = uuid()
  return sessionId
}

// 待重试队列（进程内）
let pending: Array<Record<string, unknown>> = []

function currentUserId(): string | null {
  return useAuthStore.getState().user?.id ?? null
}

async function send(payload: Record<string, unknown>): Promise<boolean> {
  try {
    const resp = await fetch(`${API_BASE}/api/v1/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    return resp.status === 202        // fire-and-forget 语义
  } catch {
    return false
  }
}

export function track(eventName: string, props: Record<string, unknown> = {}) {
  const payload: Record<string, unknown> = {
    event_name: eventName,
    user_id: currentUserId(),         // 后端若带 JWT 会以 token 覆盖，游客可空
    session_id: getSessionId(),
    properties: props,
  }
  // 先 flush 排队里的旧事件，再发当前
  const chain = [...pending, payload]
  pending = []
  void (async () => {
    for (const ev of chain) {
      const ok = await send(ev)
      if (!ok) pending.push(ev)       // 失败下一轮再试
    }
  })()
}

/** 页面浏览事件：路由变化时调用（对齐 Web 端 page.view） */
export function trackPageView(pageName: string) {
  track('page.view', { page: pageName })
}

/** 元素点击事件：手动埋点（Web 端有全局 capture，RN 由组件显式调用） */
export function trackClick(element: string, props: Record<string, unknown> = {}) {
  track('element.click', { element, ...props })
}

export { getSessionId }