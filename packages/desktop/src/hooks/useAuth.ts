import { useCallback } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { api } from '@/services/api'

export function useAuth() {
  const { login: storeLogin, logout: storeLogout, isAuthenticated, user } = useAuthStore()

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await api.login(email, password)
    const user = await api.getCurrentUser(tokens.access_token)
    storeLogin(user, tokens.access_token, tokens.refresh_token)
  }, [storeLogin])

  const register = useCallback(async (email: string, username: string, password: string, referralCode?: string) => {
    const tokens = await api.register(email, username, password, referralCode)
    const user = await api.getCurrentUser(tokens.access_token)
    storeLogin(user, tokens.access_token, tokens.refresh_token)
  }, [storeLogin])

  const logout = useCallback(() => {
    storeLogout()
  }, [storeLogout])

  return { login, register, logout, isAuthenticated, user }
}
