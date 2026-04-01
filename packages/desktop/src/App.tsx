import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/hooks/useAuth'
import { useEngine } from '@/hooks/useEngine'
import Sidebar from '@/components/Sidebar'
import TitleBar from '@/components/TitleBar'
import Dashboard from '@/pages/Dashboard'
import Meeting from '@/pages/Meeting'
import Profile from '@/pages/Profile'
import Subscription from '@/pages/Subscription'
import Settings from '@/pages/Settings'
import CaptionOverlay from '@/components/CaptionOverlay'

function AuthenticatedApp() {
  useEngine()

  return (
    <div className="flex h-screen bg-imeet-black">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TitleBar />
        <main className="flex-1 overflow-y-auto p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/meeting" element={<Meeting />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/subscription" element={<Subscription />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

function LoginPage() {
  const { t } = useTranslation()
  const { login, register } = useAuth()
  const [isRegister, setIsRegister] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    const form = e.target as HTMLFormElement
    const email = (form.elements.namedItem('email') as HTMLInputElement).value
    const password = (form.elements.namedItem('password') as HTMLInputElement).value

    try {
      if (isRegister) {
        const username = (form.elements.namedItem('username') as HTMLInputElement).value
        const referral = (form.elements.namedItem('referral') as HTMLInputElement)?.value
        await register(email, username, password, referral || undefined)
      } else {
        await login(email, password)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-screen bg-imeet-black">
      {/* Frameless window drag area */}
      <div className="drag-region h-10 flex-shrink-0" />

      <div className="flex-1 flex items-center justify-center">
        <div className="w-[420px]">
          {/* Logo */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold mb-2">
              <span className="text-imeet-gold">Vox</span><span className="text-white">clar</span>
            </h1>
            <p className="text-imeet-text-muted text-sm">
              AI-Powered Interview Assistant
            </p>
          </div>

          {/* Card */}
          <div className="bg-imeet-panel rounded-[12px] p-8 border border-imeet-border shadow-[0_4px_6px_rgba(0,0,0,0.1)]">
            <h2 className="text-lg font-semibold text-center mb-6">
              {isRegister ? t('auth.register') : t('auth.login')}
            </h2>

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-2.5 rounded-lg mb-4">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-3">
              {isRegister && (
                <input
                  name="username"
                  type="text"
                  placeholder={t('auth.username')}
                  required
                  className="input-field w-full"
                />
              )}
              <input
                name="email"
                type="email"
                placeholder={t('auth.email')}
                required
                className="input-field w-full"
              />
              <input
                name="password"
                type="password"
                placeholder={t('auth.password')}
                required
                minLength={6}
                className="input-field w-full"
              />
              {isRegister && (
                <input
                  name="referral"
                  type="text"
                  placeholder="Referral Code (optional)"
                  className="input-field w-full"
                />
              )}
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-imeet-gold text-black font-bold py-3 rounded-lg hover:bg-imeet-gold-hover active:scale-[0.98] transition-all disabled:opacity-50 mt-2"
              >
                {loading ? t('common.loading') : isRegister ? t('auth.register') : t('auth.login')}
              </button>
            </form>

            <div className="mt-5 pt-4 border-t border-imeet-border text-center">
              <p className="text-sm text-imeet-text-muted">
                {isRegister ? t('auth.has_account') : t('auth.no_account')}{' '}
                <button
                  onClick={() => { setIsRegister(!isRegister); setError('') }}
                  className="text-imeet-gold hover:text-imeet-gold-hover font-medium"
                >
                  {isRegister ? t('auth.login') : t('auth.register')}
                </button>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  const { isAuthenticated } = useAuth()

  return (
    <Routes>
      <Route path="/caption" element={<CaptionOverlay />} />
      <Route path="*" element={isAuthenticated ? <AuthenticatedApp /> : <LoginPage />} />
    </Routes>
  )
}
