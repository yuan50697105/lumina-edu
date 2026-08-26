// ============================================
// Lumina 墨光 · 前端 API 类型定义
// 与各微服务 OpenAPI 对齐
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

// ─── AI 网关（运营端模型池）───
export type ApiStyle = 'openai' | 'anthropic' | 'gemini'

export interface AiProvider {
  id: string
  name: string
  display_name: string
  description?: string | null
  endpoint_base?: string | null
  enabled: boolean
  monthly_quota?: number | null
  used_quota?: number | null
}

export interface AiModel {
  id: string
  provider_id: string
  provider_name?: string | null
  model_name: string
  display_name: string
  task_types: string[]
  enabled: boolean
  priority: number
  cost_per_1k_tokens?: number | null
  max_tokens: number
  openai_compatible: boolean
  api_style?: ApiStyle | null
}

export interface ModelCreate {
  provider_name: string
  model_name: string
  display_name: string
  task_types: string[]
  priority?: number
  cost_per_1k_tokens?: number | string
  max_tokens?: number
  api_style?: ApiStyle
}

// ─── AI 对话 ───
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