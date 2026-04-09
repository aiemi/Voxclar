import { useState, useEffect } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { api } from '@/services/api'
import { Key, Shield, Loader2 } from 'lucide-react'

export default function Setup() {
  const { activate, license_key, device_id, is_activated } = useAuthStore()
  const [inputKey, setInputKey] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [verifying, setVerifying] = useState(false)

  // Auto-verify on mount if already activated
  useEffect(() => {
    if (is_activated && license_key && device_id) {
      setVerifying(true)
      api.verifyLicense(license_key, device_id)
        .then((res) => {
          if (!res.valid) {
            // License no longer valid
            useAuthStore.getState().deactivate()
            setError(res.reason || 'License is no longer valid. Please re-enter your license key.')
          }
        })
        .catch(() => {
          // Offline -- allow through (already activated)
        })
        .finally(() => setVerifying(false))
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleActivate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputKey.trim()) return

    setError('')
    setLoading(true)

    try {
      const deviceName = `${navigator.platform || 'Desktop'} - ${navigator.userAgent.slice(0, 30)}`
      const res = await api.activateLicense(inputKey.trim(), device_id!, deviceName)

      if (res.valid) {
        activate(inputKey.trim(), device_id!)
      } else {
        setError(res.error || 'Invalid license key. Please check and try again.')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Activation failed. Please check your connection.')
    } finally {
      setLoading(false)
    }
  }

  if (verifying) {
    return (
      <div className="flex flex-col h-screen bg-imeet-black items-center justify-center">
        <Loader2 size={32} className="text-imeet-gold animate-spin mb-4" />
        <p className="text-imeet-text-muted text-sm">Verifying license...</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-imeet-black">
      {/* Frameless window drag area */}
      <div className="drag-region h-10 flex-shrink-0" />

      <div className="flex-1 overflow-y-auto flex items-center justify-center py-6">
        <div className="w-full max-w-[420px] px-4 sm:px-0 my-auto">
          {/* Logo */}
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold mb-2 font-brand">
              <span className="text-imeet-gold">Vox</span><span className="text-white">clar</span>
            </h1>
            <p className="text-imeet-text-muted text-sm">
              Lifetime Edition
            </p>
          </div>

          {/* Activation Card */}
          <div className="bg-[#1a1a1a]/80 backdrop-blur-2xl rounded-[20px_20px_4px_20px] p-5 sm:p-8 border border-white/[0.08] shadow-[0_20px_60px_rgba(0,0,0,0.3)]">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <Key size={20} className="text-purple-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold">Activate License</h2>
                <p className="text-xs text-imeet-text-muted">Enter your lifetime license key to get started</p>
              </div>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-2.5 rounded-lg mb-4">
                {error}
              </div>
            )}

            <form onSubmit={handleActivate} className="space-y-4">
              <div>
                <input
                  type="text"
                  value={inputKey}
                  onChange={(e) => setInputKey(e.target.value.toUpperCase())}
                  placeholder="XXXX-XXXX-XXXX-XXXX"
                  className="input-field w-full text-center text-lg tracking-wider font-mono"
                  autoFocus
                />
                <p className="text-[11px] text-imeet-text-muted mt-2 text-center">
                  Check your purchase confirmation email for the license key
                </p>
              </div>

              <button
                type="submit"
                disabled={loading || !inputKey.trim()}
                className="w-full bg-purple-500 text-white font-bold py-3 rounded-lg hover:bg-purple-400 active:scale-[0.98] transition-all disabled:opacity-50"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 size={16} className="animate-spin" />
                    Activating...
                  </span>
                ) : (
                  'Activate'
                )}
              </button>
            </form>

            {/* Device info */}
            <div className="mt-6 pt-4 border-t border-white/[0.06]">
              <div className="flex items-center gap-2 text-xs text-imeet-text-muted">
                <Shield size={12} />
                <span>Device ID: {device_id?.slice(0, 8)}...</span>
              </div>
              <p className="text-[10px] text-white/20 mt-1">
                This license is bound to your device. Contact support to transfer.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
