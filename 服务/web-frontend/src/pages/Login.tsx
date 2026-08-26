import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { post } from '../api/client'
import type { TokenResponse } from '../api/types'
import { useAuthStore } from '../store/auth'
import { track } from '../utils/tracker'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)
  const setSession = useAuthStore((s) => s.setSession)
  const navigate = useNavigate()

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setErr('')
    setLoading(true)
    try {
      const tr = await post<TokenResponse>('/auth/login', {
        username: username.trim(),
        password,
        device: 'web',
      })
      setSession(tr)
      track('auth.login', { role: tr.user.role })
      navigate('/', { replace: true })
    } catch (ex) {
      setErr((ex as Error).message)
      track('auth.login_fail', { reason: (ex as Error).message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="brand login-brand">
          <span className="brand-mark">墨</span>
          <span className="brand-name">Lumina 墨光</span>
        </div>
        <p className="login-sub">面向高校师生的教学协作平台</p>
        <form onSubmit={onSubmit}>
          <label className="field">
            学号 / 邮箱
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="2023010001 或 user@lumina.edu"
              autoComplete="username"
              autoFocus
            />
          </label>
          <label className="field">
            密码
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </label>
          {err && <p className="error">{err}</p>}
          <button className="btn primary block" disabled={loading} data-track="登录">
            {loading ? '登录中…' : '登录'}
          </button>
        </form>
        <p className="hint">
          演示账号：林清 linqing@lumina.edu / Student@123（学生）· wjg@lumina.edu / Teacher@123（教师）· admin@lumina.edu / Admin@123456（管理员）
        </p>
      </div>
    </div>
  )
}