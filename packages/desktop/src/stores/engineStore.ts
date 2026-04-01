import { create } from 'zustand'

type EngineStatus = 'disconnected' | 'connecting' | 'ready' | 'running' | 'error'

interface EngineState {
  status: EngineStatus
  errorMessage: string | null
  platform: string | null
  updateStatus: (status: EngineStatus, details?: Record<string, unknown>) => void
  setError: (message: string) => void
  clearError: () => void
}

export const useEngineStore = create<EngineState>((set) => ({
  status: 'disconnected',
  errorMessage: null,
  platform: null,

  updateStatus: (status, details) =>
    set({
      status,
      platform: (details?.platform as string) || null,
      errorMessage: status === 'error' ? (details?.message as string) || 'Unknown error' : null,
    }),

  setError: (message) => set({ status: 'error', errorMessage: message }),
  clearError: () => set({ errorMessage: null }),
}))
