// ============================================
// Lumina 墨光 · 认证状态（Zustand）
// token + user 持久化 localStorage
// ============================================
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { TokenResponse, User } from '../api/types'

interface AuthState {
  token: string | null
  user: User | null
  setSession: (tr: TokenResponse) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setSession: (tr) => set({ token: tr.access_token, user: tr.user }),
      logout: () => set({ token: null, user: null }),
    }),
    { name: 'lumina-auth' },
  ),
)