// ============================================
// Lumina 墨光 · 移动端 API 类型定义
// 与 Web 端 web-frontend/src/api/types.ts 对齐（共享后端契约）
// ============================================

export type Role = 'student' | 'teacher' | 'admin'

export interface User {
  id: string
  student_id?: string | null
  name: string
  email: string
  role: Role
  department?: string | null
  grade?: string | null
  avatar_url?: string | null
  bio?: string | null
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  expires_in: number
  user: User
}

export interface LoginRequest {
  username: string
  password: string
  device?: string
}

export interface TeacherBrief {
  id: string
  name: string
  avatar_url?: string | null
}

export interface Course {
  id: string
  code: string
  title: string
  description?: string | null
  teacher?: TeacherBrief | null
  department?: string | null
  credits?: number | null
  semester: string
  students_count: number
  status: string
}

export interface CourseListResp {
  code: number
  data: Course[]
  pagination: { offset: number; limit: number; total: number; has_more: boolean }
}

export interface Chapter {
  id: string
  course_id: string
  title: string
  content?: string | null
  order_num: number
  resources?: unknown[] | null
}

export interface MyCourseGrade {
  course_id: string
  title: string
  credit?: number | null
  score?: number | null
  grade?: string | null
  semester: string
}

export interface MyGrades {
  gpa?: number | null
  total_credits?: number | null
  course_count: number
  courses: MyCourseGrade[]
}

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export interface ChatEvent {
  type: 'token' | 'error' | 'done'
  content?: string
  message?: string
  conversation_id?: string
  usage?: { prompt_tokens: number; completion_tokens: number }
}

export interface Conversation {
  id: string
  title?: string | null
  model?: string | null
  message_count: number
  total_tokens: number
  updated_at: string
}

export interface ConversationMessage {
  id: string
  role: string
  content?: string | null
  prompt_tokens: number
  completion_tokens: number
  created_at: string
}