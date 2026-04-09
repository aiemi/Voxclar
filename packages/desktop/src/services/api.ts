/**
 * API service -- Lifetime version.
 * Only license activation/verification endpoints.
 */

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  const licenseKey = localStorage.getItem('voxclar_license_key')
  if (licenseKey) headers['X-License-Key'] = licenseKey
  Object.assign(headers, options.headers as Record<string, string>)

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }))
    throw new Error(err.error || err.detail || res.statusText)
  }

  return res.json()
}

export const api = {
  // License activation (first run)
  activateLicense: (licenseKey: string, deviceId: string, deviceName: string) =>
    request<{ valid: boolean; license_key?: string; version?: string; error?: string }>('/payments/license/activate', {
      method: 'POST',
      body: JSON.stringify({ license_key: licenseKey, device_id: deviceId, device_name: deviceName }),
    }),

  // License verification (subsequent runs)
  verifyLicense: (licenseKey: string, deviceId: string) =>
    request<{ valid: boolean; license_key?: string; reason?: string }>('/payments/license/verify', {
      method: 'POST',
      body: JSON.stringify({ license_key: licenseKey, device_id: deviceId }),
    }),
}
