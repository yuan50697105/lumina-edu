import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { post } from '../api/client'
import type { TokenResponse } from '../api/types'
import { useAuthStore } from '../store/auth'
import { track } from '../utils/tracker'

interface RegisterPayload {
  name: string
  email: string
  password: string
  student_id?: string
  role: string
  device: string
}

export default function Login() {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [studentId, setStudentId] = useState('')
  const [role, setRole] = useState('student')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)
  const setSession = useAuthStore((s) => s.setSession)
  const navigate = useNavigate()

  async function doLogin() {
    const tr = await post<TokenResponse>('/auth/login', {
      username: username.trim(),
      password,
      device: 'web',
    })
    setSession(tr)
    track('auth.login', { role: tr.user.role })
    navigate('/', { replace: true })
  }

  async function doRegister() {
    const payload: RegisterPayload = {
      name: name.trim(),
      email: email.trim(),
      password,
      role,
      device: 'web',
    }
    if (studentId.trim()) payload.student_id = studentId.trim()
    const tr = await post<TokenResponse>('/auth/register', payload)
    setSession(tr)
    track('user.register', { role: tr.user.role })
    navigate('/', { replace: true })
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setErr('')
    setLoading(true)
    try {
      if (mode === 'login') await doLogin()
      else await doRegister()
    } catch (ex) {
      setErr((ex as Error).message)
      track(mode === 'login' ? 'auth.login_fail' : 'user.register_fail', {
        reason: (ex as Error).message,
      })
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

        <div className="seg" role="tablist">
          <button
            type="button"
            className={mode === 'login' ? 'on' : ''}
            onClick={() => { setMode('login'); setErr('') }}
          >
            登录
          </button>
          <button
            type="button"
            className={mode === 'register' ? 'on' : ''}
            onClick={() => { setMode('register'); setErr('') }}
          >
            注册
          </button>
        </div>

        <form onSubmit={onSubmit}>
          {mode === 'register' && (
            <>
              <label className="field">
                姓名
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="请输入真实姓名"
                  autoComplete="name"
                  required
                />
              </label>
              <label className="field">
                邮箱
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@lumina.edu"
                  autoComplete="email"
                  required
                />
              </label>
              <label className="field">
                学号 / 工号
                <input
                  value={studentId}
                  onChange={(e) => setStudentId(e.target.value)}
                  placeholder="如 20260001（可选）"
                />
              </label>
              <label className="field">
                身份
                <select value={role} onChange={(e) => setRole(e.target.value)}>
                  <option value="student">学生</option>
                  <option value="teacher">教师</option>
                </select>
              </label>
            </>
          )}

          {mode === 'login' && (
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
          )}

          <label className="field">
            密码
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={mode === 'register' ? '至少 8 位' : '••••••••'}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            />
          </label>
          {err && <p className="error">{err}</p>}
          <button className="btn primary block" disabled={loading} data-track={mode === 'login' ? '登录' : '注册'}>
            {loading ? '提交中…' : mode === 'login' ? '登录' : '创建账号'}
          </button>
        </form>

        <p className="hint">
          演示账号：student@lumina.edu / Demo@2026（学生）· teacher@lumina.edu / Demo@2026（教师）· admin@lumina.edu / Demo@2026（管理员）
        </p>
      </div>
    </div>
  )
}