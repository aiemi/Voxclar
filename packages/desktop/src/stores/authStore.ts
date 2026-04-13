import { create } from 'zustand'
import type { User } from '@/types'

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  // Epoch ms — while Date.now() is below this, AuthenticatedApp polls the
  // /users/me endpoint every ~3 s instead of every 60 s so the UI catches
  // Stripe-webhook-driven updates moments after payment completes.
  aggressive_refresh_until: number
  login: (user: User, accessToken: string, refreshToken: string) => void
  logout: () => void
  updateUser: (updates: Partial<User>) => void
  setTokens: (accessToken: string, refreshToken: string) => void
  startAggressiveRefresh: (durationMs?: number) => void
  stopAggressiveRefresh: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: localStorage.getItem('access_token'),
  refreshToken: localStorage.getItem('refresh_token'),
  isAuthenticated: !!localStorage.getItem('access_token'),
  aggressive_refresh_until: 0,

  login: (user, accessToken, refreshToken) => {
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('refresh_token', refreshToken)
    set({ user, accessToken, refreshToken, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false })
  },

  updateUser: (updates) =>
    set((state) => ({
      user: state.user ? { ...state.user, ...updates } : null,
    })),

  setTokens: (accessToken, refreshToken) => {
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('refresh_token', refreshToken)
    set({ accessToken, refreshToken })
  },

  startAggressiveRefresh: (durationMs = 5 * 60 * 1000) => {
    set({ aggressive_refresh_until: Date.now() + durationMs })
  },

  stopAggressiveRefresh: () => {
    set({ aggressive_refresh_until: 0 })
  },
}))
