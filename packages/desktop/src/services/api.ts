import type { User, Meeting, UserStats, Transaction } from '@/types'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (token) headers['Authorization'] = `Bearer ${token}`
  // Explicit headers override localStorage token (important for register flow)
  Object.assign(headers, options.headers as Record<string, string>)

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })

  if (res.status === 401) {
    // Try refresh
    const refreshToken = localStorage.getItem('refresh_token')
    if (refreshToken) {
      const refreshRes = await fetch(`${BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (refreshRes.ok) {
        const tokens = await refreshRes.json()
        localStorage.setItem('access_token', tokens.access_token)
        localStorage.setItem('refresh_token', tokens.refresh_token)
        headers['Authorization'] = `Bearer ${tokens.access_token}`
        const retryRes = await fetch(`${BASE_URL}${path}`, { ...options, headers })
        if (!retryRes.ok) throw new Error(await retryRes.text())
        return retryRes.json()
      }
    }
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    throw new Error('Unauthorized')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || res.statusText)
  }

  return res.json()
}

export const api = {
  // Auth
  login: (email: string, password: string) =>
    request<{ access_token: string; refresh_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, username: string, password: string, referralCode?: string) =>
    request<{ access_token: string; refresh_token: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, username, password, referral_code: referralCode }),
    }),

  sendVerificationCode: (email: string, username: string, password: string, referralCode?: string) =>
    request<{ message: string; email: string }>('/auth/send-code', {
      method: 'POST',
      body: JSON.stringify({ email, username, password, referral_code: referralCode }),
    }),

  verifyCode: (email: string, code: string) =>
    request<{ access_token: string; refresh_token: string }>('/auth/verify-code', {
      method: 'POST',
      body: JSON.stringify({ email, code }),
    }),

  // Users
  getCurrentUser: (token?: string) => {
    const headers: Record<string, string> = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    return request<User>('/users/me', { headers })
  },

  getUserStats: () => request<UserStats>('/users/me/stats'),

  // Meetings
  createMeeting: (data: { title?: string; meeting_type: string; language: string; prep_notes?: string }) =>
    request<Meeting>('/meetings', { method: 'POST', body: JSON.stringify(data) }),

  listMeetings: (skip = 0, limit = 20) =>
    request<{ meetings: Meeting[]; total: number }>(`/meetings?skip=${skip}&limit=${limit}`),

  getMeeting: (id: string) => request<Meeting>(`/meetings/${id}`),

  endMeeting: (id: string) =>
    request<Meeting>(`/meetings/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status: 'completed' }),
    }),

  // Payments
  getPlans: () => request<Array<{
    id: string; name: string; tier: string; price: number;
    price_type: string; minutes: number; features: string[]
  }>>('/payments/plans'),

  createCheckout: (planId: string) =>
    request<{ checkout_url: string }>('/payments/checkout', {
      method: 'POST',
      body: JSON.stringify({ plan_id: planId }),
    }),

  createPortal: () =>
    request<{ portal_url: string }>('/payments/portal', { method: 'POST' }),

  activateLicense: (deviceId: string, deviceName: string) =>
    request<{ valid: boolean; license_key?: string; version?: string }>('/payments/license/activate', {
      method: 'POST',
      body: JSON.stringify({ device_id: deviceId, device_name: deviceName }),
    }),

  verifyLicense: (deviceId: string) =>
    request<{ valid: boolean; license_key?: string; reason?: string }>('/payments/license/verify', {
      method: 'POST',
      body: JSON.stringify({ device_id: deviceId }),
    }),

  // API Key
  getApiKey: () => request<{ api_key: string | null }>('/payments/api-key'),

  generateApiKey: () =>
    request<{ api_key: string }>('/payments/api-key/generate', { method: 'POST' }),

  // Referrals
  getInviteCode: () => request<{ invite_code: string }>('/referrals/my-code'),

  getReferralStats: () => request<{ invite_code: string; total_referred: number; total_rewards_minutes: number }>('/referrals/stats'),

  getTransactions: (skip = 0, limit = 50) =>
    request<{ transactions: Transaction[]; total: number }>(`/payments/transactions?skip=${skip}&limit=${limit}`),

  // Cloud data fetch
  getTranscripts: (meetingId: string) =>
    request<{ transcripts: Array<{ speaker: string; text: string; timestamp_ms: number; is_question: boolean }>; total: number }>(
      `/meetings/${meetingId}/transcripts`
    ),

  getAnswers: (meetingId: string) =>
    request<{ answers: Array<{ question_text: string; answer_text: string; question_type: string; model_used?: string }>; total: number }>(
      `/meetings/${meetingId}/answers`
    ),

  // Sync (cloud data)
  syncMeetingRecord: (data: {
    meeting_id: string; transcripts: Array<{ speaker: string; text: string; timestamp_ms: number; is_question: boolean }>;
    answers: Array<{ question_text: string; answer_text: string; question_type: string; model_used?: string }>;
    summary?: string;
  }) =>
    request<{ synced: boolean }>('/meetings/sync', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}
