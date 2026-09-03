// ============================================
// Lumina 墨光 · 鸿蒙客户端 · 常量定义
// 设计系统 · API 地址 · 颜色 · 字体
// ============================================

// API 地址（生产替换为正式域名）
export const API_BASE: string = 'http://127.0.0.1:8080';

// Lumina 设计系统颜色
export const Colors = {
  paper: '#FAF6EC',       // 宣纸色（主背景）
  ink: '#0F1020',         // 墨色（主文字）
  ink2: '#6B6C7A',        // 次文字
  ink3: '#A8A9B8',        // 弱文字
  cobalt: '#3D46C9',      // 钴蓝（品牌强调）
  cobaltLight: '#E8EAFB', // 钴蓝浅
  highlighter: '#F5B800', // 荧光黄（签名效果）
  warning: '#E85D3A',     // 警示红
  success: '#2A7F4F',     // 成长绿
  aiPurple: '#7C3AED',    // AI 紫
  divider: '#E8E4D8',     // 分隔线
  cardBg: '#FFFFFF',      // 卡片背景
};

// Lumina 字体大小
export const FontSize = {
  xs: 11,
  sm: 12,
  base: 14,
  md: 16,
  lg: 18,
  xl: 22,
  xxl: 28,
  display: 34,
};

// 间距
export const Spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
};

// 圆角
export const Radius = {
  sm: 6,
  md: 10,
  lg: 14,
  xl: 20,
};

// 通用类型定义（对齐 mobile-app types.ts）
export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  student_id?: string;
  avatar_url?: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface Course {
  id: string;
  code: string;
  title: string;
  description?: string;
  teacher_name?: string;
  cover_url?: string;
  credits?: number;
  term?: string;
}

export interface LiveRoom {
  id: string;
  course_id: string;
  title: string;
  status: string;  // idle | live | ended
  stream_url?: string;
  started_at?: string;
  teacher_name?: string;
  attendee_count?: number;
}

export interface LearningPath {
  id: string;
  title: string;
  description?: string;
  category: string;
  difficulty: string;
  node_count?: number;
}

export interface Video {
  id: string;
  title: string;
  course_id?: string;
  cover_url?: string;
  duration_sec: number;
  view_count: number;
  published: boolean;
}

export interface UserXP {
  user_id: string;
  total_xp: number;
  level: number;
  streak_days: number;
}

export interface CheckInResult {
  success: boolean;
  xp_awarded: number;
  new_streak: number;
  already_checked_in: boolean;
}

export interface Badge {
  id: string;
  name: string;
  icon: string;
  description: string;
  earned_at?: string;
}

export interface Notification {
  id: string;
  title: string;
  body: string;
  type: string;
  read: boolean;
  created_at: string;
}
