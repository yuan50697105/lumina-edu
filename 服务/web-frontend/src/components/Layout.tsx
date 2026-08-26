import { useEffect } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth'
import { track } from '../utils/tracker'

const NAV = [
  { to: '/', label: '首页' },
  { to: '/ai', label: 'AI 导师' },
  { to: '/grades', label: '成绩单' },
]

export default function Layout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()

  // 页面访问埋点
  useEffect(() => {
    track('page.view', { page: location.pathname })
  }, [location.pathname])

  function onLogout() {
    track('auth.logout')
    logout()
    navigate('/login')
  }

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">墨</span>
          <span className="brand-name">Lumina 墨光</span>
        </div>
        <nav className="main-nav">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === '/'}
              className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}
              data-track={`nav:${n.label}`}
            >
              {n.label}
            </NavLink>
          ))}
          {user?.role === 'admin' && (
            <NavLink
              to="/admin/models"
              className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}
              data-track="nav:模型池"
            >
              模型池
            </NavLink>
          )}
        </nav>
        <div className="topbar-right">
          <span className="user-chip">
            <span className="user-avatar">{user?.name?.slice(0, 1) ?? '?'}</span>
            {user?.name}
            <em>{user?.role === 'student' ? '学生' : user?.role === 'teacher' ? '教师' : '管理员'}</em>
          </span>
          <button className="btn ghost" onClick={onLogout} data-track="退出登录">
            退出
          </button>
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
      <footer className="footer">Lumina 墨光 · 教学协作平台 · 教育 · AI 赋能</footer>
    </div>
  )
}