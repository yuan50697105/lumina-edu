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

// ─── 直播课堂（D-01 · V1.1 · 对齐 web-frontend）───
export type LiveRoomStatus = 'scheduled' | 'live' | 'ended'

export interface LiveCallInfo {
  user_id: string
  name: string
  called_at: string
}

export interface LiveRoom {
  id: string
  course_id: string
  course_title?: string | null
  teacher_id: string
  teacher_name?: string | null
  title: string
  status: LiveRoomStatus
  stream_url?: string | null
  viewer_count?: number
  online_count?: number
  active_call?: LiveCallInfo | null
  started_at?: string | null
  ended_at?: string | null
}

export interface LiveMessage {
  id: number
  room_id: string
  user_id?: string | null
  user_name?: string | null
  role?: string | null
  msg_type: string // chat | system | call
  content?: string | null
  created_at: string
}

export interface LiveRaise {
  id: string
  user_id: string
  name?: string | null
  raised_at?: string | null
}

export interface LiveQuizOption {
  key: string
  text: string
}

export interface LiveQuiz {
  id: string
  room_id: string
  teacher_id: string
  question: string
  options: LiveQuizOption[]
  answer?: string | null
  status: string
  created_at?: string | null
  closed_at?: string | null
}

export interface LiveQuizResult {
  quiz_id: string
  question: string
  total: number
  distribution: Record<string, number>
  correct_count?: number | null
  correct_rate?: number | null
}