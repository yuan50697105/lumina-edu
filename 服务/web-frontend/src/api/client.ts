// ============================================
// Lumina 墨光 · 前端 API 客户端
// fetch 封装 · JWT 注入 · 401 跳登录
// ============================================
import { useAuthStore } from '../store/auth'

export const BASE = '/api/v1'

export class ApiError extends Error {
  status: number
  code?: string
  constructor(status: number, message: string, code?: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

interface RequestOptions {
  method?: string
  body?: unknown
  headers?: Record<string, string>
  auth?: boolean
  signal?: AbortSignal
}

export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {}, auth = true, signal } = opts
  const final: Record<string, string> = {
    'Content-Type': 'application/json',
    ...headers,
  }
  if (auth) {
    const token = useAuthStore.getState().token
    if (token) final.Authorization = `Bearer ${token}`
  }

  const resp = await fetch(`${BASE}${path}`, {
    method,
    headers: final,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  })

  if (resp.status === 401 && auth) {
    useAuthStore.getState().logout()
    window.location.href = '/login'
    throw new ApiError(401, '登录已过期')
  }
  if (!resp.ok) {
    let msg = `请求失败 (${resp.status})`
    let code: string | undefined
    try {
      const j = await resp.json()
      const d = j.detail
      if (typeof d === 'string') msg = d
      else if (d?.detail) msg = d.detail
      code = d?.code ?? j?.code
    } catch { /* ignore */ }
    throw new ApiError(resp.status, msg, code)
  }
  if (resp.status === 204) return undefined as T
  return (await resp.json()) as T
}

export const get = <T>(p: string, o?: RequestOptions) => request<T>(p, { ...o, method: 'GET' })
export const post = <T>(p: string, body?: unknown, o?: RequestOptions) =>
  request<T>(p, { ...o, method: 'POST', body })
export const patch = <T>(p: string, body?: unknown, o?: RequestOptions) =>
  request<T>(p, { ...o, method: 'PATCH', body })
export const put = <T>(p: string, body?: unknown, o?: RequestOptions) =>
  request<T>(p, { ...o, method: 'PUT', body })
export const del = <T>(p: string, o?: RequestOptions) => request<T>(p, { ...o, method: 'DELETE' })