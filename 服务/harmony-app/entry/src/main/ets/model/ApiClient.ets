// ============================================
// Lumina 墨光 · 鸿蒙客户端 · API 客户端
// 与 mobile-app/src/api/client.ts 同契约
// ============================================
import { http } from '@kit.NetworkKit';
import { API_BASE, LoginResponse, Course, LiveRoom, LearningPath, Video, UserXP, CheckInResult, Badge, Notification, User } from '../common/constants';

export class ApiError extends Error {
  status: number;
  code?: string;
  constructor(status: number, message: string, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

// 全局 token 管理（鸿蒙无 Zustand，用模块变量）
let accessToken: string | null = null;
let currentUser: User | null = null;

export function getToken(): string | null {
  return accessToken;
}

export function setToken(token: string | null): void {
  accessToken = token;
}

export function getUser(): User | null {
  return currentUser;
}

export function setUser(user: User | null): void {
  currentUser = user;
}

interface RequestOptions {
  method?: string;
  body?: Object;
  auth?: boolean;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, auth = true } = opts;
  const url = `${API_BASE}/api/v1${path}`;

  const httpRequest = http.createHttp();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (auth && accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }

  try {
    const response = await httpRequest.request(url, {
      method: method === 'GET' ? http.RequestMethod.GET :
              method === 'POST' ? http.RequestMethod.POST :
              method === 'PUT' ? http.RequestMethod.PUT :
              method === 'DELETE' ? http.RequestMethod.DELETE :
              http.RequestMethod.PATCH,
      header: headers,
      extraData: body ? JSON.stringify(body) : undefined,
      connectTimeout: 15000,
      readTimeout: 15000,
    });

    if (response.responseCode === 401 && auth) {
      setToken(null);
      setUser(null);
      throw new ApiError(401, '登录已过期');
    }
    if (response.responseCode === 204) {
      return undefined as T;
    }
    if (response.responseCode < 200 || response.responseCode >= 300) {
      let msg = `请求失败 (${response.responseCode})`;
      try {
        const j = JSON.parse(response.result as string);
        if (typeof j.detail === 'string') msg = j.detail;
        else if (j.detail?.detail) msg = j.detail.detail;
      } catch (e) { /* ignore */ }
      throw new ApiError(response.responseCode, msg);
    }

    return JSON.parse(response.result as string) as T;
  } finally {
    httpRequest.destroy();
  }
}

// 便捷方法
export const api = {
  get: <T>(p: string, auth = true) => request<T>(p, { auth }),
  post: <T>(p: string, body?: Object, auth = true) => request<T>(p, { method: 'POST', body, auth }),
  put: <T>(p: string, body?: Object, auth = true) => request<T>(p, { method: 'PUT', body, auth }),
  del: <T>(p: string, auth = true) => request<T>(p, { method: 'DELETE', auth }),

  // 认证
  async login(email: string, password: string): Promise<LoginResponse> {
    const form = new URLSearchParams();
    form.append('username', email);
    form.append('password', password);
    // OAuth2 password flow (form-urlencoded)
    const url = `${API_BASE}/api/v1/auth/login`;
    const httpRequest = http.createHttp();
    try {
      const resp = await httpRequest.request(url, {
        method: http.RequestMethod.POST,
        header: { 'Content-Type': 'application/x-www-form-urlencoded' },
        extraData: form.toString(),
      });
      const data = JSON.parse(resp.result as string) as LoginResponse;
      setToken(data.access_token);
      setUser(data.user);
      return data;
    } finally {
      httpRequest.destroy();
    }
  },

  logout(): void {
    setToken(null);
    setUser(null);
  },

  // 课程
  listCourses: () => api.get<Course[]>('/courses'),
  getCourse: (id: string) => api.get<Course>(`/courses/${id}`),

  // 直播
  listLiveRooms: (courseId: string) => api.get<LiveRoom[]>(`/courses/${courseId}/live-rooms`),
  createLiveRoom: (courseId: string, title: string) =>
    api.post<LiveRoom>(`/courses/${courseId}/live-rooms`, { title }),

  // 学习广场（D-06）
  listLearningPaths: () => api.get<LearningPath[]>('/learning/paths'),
  getUserXP: () => api.get<UserXP>('/learning/xp'),
  checkIn: () => api.post<CheckInResult>('/checkin'),
  listBadges: () => api.get<Badge[]>('/learning/badges'),

  // 视频（D-08）
  listVideos: () => api.get<Video[]>('/videos'),
  getVideo: (id: string) => api.get<Video>(`/videos/${id}`),

  // 通知
  listNotifications: () => api.get<Notification[]>('/notifications'),

  // 用户
  getMe: () => api.get<User>('/users/me'),
};
