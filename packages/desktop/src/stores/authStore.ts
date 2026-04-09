import { create } from 'zustand'

interface LicenseState {
  license_key: string | null
  device_id: string | null
  is_activated: boolean
  activate: (licenseKey: string, deviceId: string) => void
  deactivate: () => void
}

function getOrCreateDeviceId(): string {
  let id = localStorage.getItem('voxclar_device_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('voxclar_device_id', id)
  }
  return id
}

export const useAuthStore = create<LicenseState>((set) => ({
  license_key: localStorage.getItem('voxclar_license_key'),
  device_id: getOrCreateDeviceId(),
  is_activated: localStorage.getItem('voxclar_license_activated') === 'true',

  activate: (licenseKey, deviceId) => {
    localStorage.setItem('voxclar_license_key', licenseKey)
    localStorage.setItem('voxclar_device_id', deviceId)
    localStorage.setItem('voxclar_license_activated', 'true')
    set({ license_key: licenseKey, device_id: deviceId, is_activated: true })
  },

  deactivate: () => {
    localStorage.removeItem('voxclar_license_key')
    localStorage.removeItem('voxclar_license_activated')
    set({ license_key: null, is_activated: false })
  },
}))
