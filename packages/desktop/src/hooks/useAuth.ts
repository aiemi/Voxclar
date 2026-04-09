/**
 * useAuth -- Lifetime version. Just exposes license state.
 */
import { useAuthStore } from '@/stores/authStore'

export function useAuth() {
  const { is_activated, license_key, device_id, deactivate } = useAuthStore()

  return {
    isAuthenticated: is_activated,
    license_key,
    device_id,
    logout: deactivate,
  }
}
