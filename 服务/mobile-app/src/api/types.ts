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

// ─── D-06 · 自主学习与闯关奖励 ───

export interface LearningPath {
  id: string
  title: string
  description?: string | null
  category: string
  difficulty: string
  cover_emoji?: string | null
  cover_gradient?: string | null
  total_nodes: number
  total_xp: number
  learner_count: number
  progress_pct?: number | null
  created_at: string
}

export interface LearningPathNode {
  id: string
  path_id: string
  sequence: number
  node_type: 'reading' | 'video' | 'quiz' | 'challenge'
  title: string
  description?: string | null
  duration_min?: number | null
  xp_reward: number
  status: 'locked' | 'current' | 'done'
  xp_earned: number
  completed_at?: string | null
}

export interface UserXP {
  user_id: string
  total_xp: number
  level: number
  streak_days: number
  last_checkin_date?: string | null
  xp_to_next_level: number
  level_progress_pct: number
}

export interface CheckInResult {
  success: boolean
  message: string
  xp_awarded: number
  streak_days: number
  already_checked: boolean
}

export interface CheckInDay {
  date: string
  checked: boolean
  xp: number
}

export interface CheckInCalendar {
  days: CheckInDay[]
  total_checked: number
  current_streak: number
}

export interface Badge {
  id: string
  code: string
  name: string
  description?: string | null
  icon: string
  condition_type: string
  condition_value: number
  earned: boolean
  earned_at?: string | null
}

export interface Challenge {
  id: string
  node_id?: string | null
  title: string
  description?: string | null
  time_limit_min?: number | null
  question_count: number
  max_attempts: number
  pass_score: number
  xp_reward: number
  attempts_left: number
}

export interface ChallengeQuestion {
  index: number
  q: string
  options: string[]
}

export interface ChallengeStart {
  challenge_id: string
  title: string
  time_limit_min?: number | null
  questions: ChallengeQuestion[]
  attempt_id: string
}

export interface ChallengeSubmit {
  attempt_id: string
  answers: { index: number; answer: string }[]
}

export interface ChallengeAnswerReview {
  index: number
  q: string
  your_answer: string | null
  correct_answer: string
  is_correct: boolean
}

export interface ChallengeResult {
  attempt_id: string
  score: number
  passed: boolean
  xp_earned: number
  correct_count: number
  total_count: number
  answers_review: ChallengeAnswerReview[]
}

export interface LeaderboardEntry {
  rank: number
  user_id: string
  name: string
  avatar_emoji?: string | null
  total_xp: number
  level: number
  streak_days: number
}

export interface Leaderboard {
  entries: LeaderboardEntry[]
  my_rank?: number | null
  total_users: number
}

export interface LearningStats {
  total_xp: number
  level: number
  streak_days: number
  paths_completed: number
  paths_total: number
  badges_earned: number
  badges_total: number
  challenges_passed: number
  videos_watched: number
  videos_total: number
}

// ─── D-08 · 教学视频与录播回放 ───

export interface Video {
  id: string
  course_id?: string | null
  title: string
  description?: string | null
  category?: string | null
  tags?: string[] | null
  duration_sec: number
  duration_display?: string | null
  video_url?: string | null
  thumbnail_url?: string | null
  cover_emoji?: string | null
  cover_gradient?: string | null
  view_count: number
  progress_pct: number
  created_at: string
}

export interface VideoChapter {
  id: string
  video_id: string
  sequence: number
  title: string
  start_sec: number
  start_display?: string | null
}

export interface VideoNote {
  id: string
  video_id: string
  timestamp_sec: number
  timestamp_display?: string | null
  content: string
  created_at: string
}

export interface VideoDetail extends Video {
  chapters: VideoChapter[]
  notes: VideoNote[]
}

export interface VideoNoteCreate {
  video_id: string
  timestamp_sec: number
  content: string
}

export interface VideoWatchHistory {
  video_id: string
  title: string
  cover_emoji?: string | null
  cover_gradient?: string | null
  duration_sec: number
  duration_display?: string | null
  watched_sec: number
  progress_pct: number
  last_watched_at: string
}

export interface VideoProgress {
  video_id: string
  watched_sec: number
  total_sec: number
}