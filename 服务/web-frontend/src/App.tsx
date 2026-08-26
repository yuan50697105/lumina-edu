import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuthStore } from './store/auth'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import CourseDetail from './pages/CourseDetail'
import AIChat from './pages/AIChat'
import Grades from './pages/Grades'
import AdminModels from './pages/AdminModels'
import type { ReactNode } from 'react'

function Protected({ children }: { children: ReactNode }) {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="courses/:id" element={<CourseDetail />} />
        <Route path="ai" element={<AIChat />} />
        <Route path="grades" element={<Grades />} />
        <Route path="admin/models" element={<AdminModels />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}