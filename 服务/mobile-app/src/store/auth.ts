// ============================================
// Lumina 墨光 · 移动端认证状态（Zustand + AsyncStorage）
// ============================================
import AsyncStorage from '@react-native-async-storage/async-storage'
import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import type { TokenResponse, User } from '../api/types'

interface AuthState {
  token: string | null
  user: User | null
  hydrated: boolean
  setSession: (tr: TokenResponse) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      hydrated: false,
      setSession: (tr) => set({ token: tr.access_token, user: tr.user, hydrated: true }),
      logout: () => set({ token: null, user: null, hydrated: true }),
    }),
    {
      name: 'lumina-mobile-auth',
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (s) => ({ token: s.token, user: s.user }),
    },
  ),
)