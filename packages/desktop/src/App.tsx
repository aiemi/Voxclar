import { useState, useEffect, Fragment } from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Eye, EyeOff, Mail } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { useAuthStore } from '@/stores/authStore'
import { api } from '@/services/api'
import { useEngine } from '@/hooks/useEngine'
import Sidebar from '@/components/Sidebar'
import TitleBar from '@/components/TitleBar'
import Dashboard from '@/pages/Dashboard'
import Meeting from '@/pages/Meeting'
import Profile from '@/pages/Profile'
import Subscription from '@/pages/Subscription'
import Settings from '@/pages/Settings'
import MeetingRecord from '@/pages/MeetingRecord'
import TermsOfService from '@/pages/TermsOfService'
import PrivacyPolicy from '@/pages/PrivacyPolicy'
import SecurityPolicy from '@/pages/SecurityPolicy'
import CaptionOverlay from '@/components/CaptionOverlay'

function AuthenticatedApp() {
  useEngine()
  const storeLogout = useAuthStore((s) => s.logout)
  const storeLogin = useAuthStore((s) => s.login)
  const stopAggressiveRefresh = useAuthStore((s) => s.stopAggressiveRefresh)

  // Keep user data in sync with the server:
  //   1. On mount (also validates the token — bad token → force logout)
  //   2. Normally every 60 s
  //   3. Whenever the window regains focus (user Alt-Tabs back)
  //   4. Every 3 s while aggressive_refresh_until is in the future — set
  //      by Subscription.tsx when the user kicks off a Stripe checkout so
  //      the new tier/balance appears within seconds of the webhook.
  useEffect(() => {
    let mounted = true
    let interval: ReturnType<typeof setInterval> | null = null

    const refreshUser = async (forceLogoutOnError: boolean) => {
      try {
        const user = await api.getCurrentUser()
        if (!mounted) return
        const token = localStorage.getItem('access_token')
        const refresh = localStorage.getItem('refresh_token')
        if (token && refresh) {
          storeLogin(user, token, refresh)
        }
        const until = useAuthStore.getState().aggressive_refresh_until
        if (until && Date.now() > until) stopAggressiveRefresh()
      } catch {
        if (forceLogoutOnError && mounted) storeLogout()
      }
    }

    const scheduleNext = () => {
      if (interval) clearInterval(interval)
      const aggressive = Date.now() < useAuthStore.getState().aggressive_refresh_until
      const period = aggressive ? 3_000 : 60_000
      interval = setInterval(() => {
        refreshUser(false)
        const stillAggressive = Date.now() < useAuthStore.getState().aggressive_refresh_until
        if (stillAggressive !== aggressive) scheduleNext()
      }, period)
    }

    // Kick off aggressive polling the moment Subscription.tsx sets the flag.
    const unsubscribe = useAuthStore.subscribe((state, prev) => {
      if (state.aggressive_refresh_until !== prev.aggressive_refresh_until) {
        refreshUser(false)
        scheduleNext()
      }
    })

    refreshUser(true)  // initial load — validate token
    scheduleNext()

    const onFocus = () => refreshUser(false)
    window.addEventListener('focus', onFocus)

    return () => {
      mounted = false
      if (interval) clearInterval(interval)
      unsubscribe()
      window.removeEventListener('focus', onFocus)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

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
            <Route path="/records" element={<MeetingRecord />} />
            <Route path="/terms" element={<TermsOfService />} />
            <Route path="/privacy" element={<PrivacyPolicy />} />
            <Route path="/security" element={<SecurityPolicy />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

function LoginPage() {
  const { t } = useTranslation()
  const { login } = useAuth()
  const storeLogin = useAuthStore((s) => s.login)
  const [isRegister, setIsRegister] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [username, setUsername] = useState('')
  const [referral, setReferral] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [agreedTerms, setAgreedTerms] = useState(false)

  // Verification code step
  const [codeSent, setCodeSent] = useState(false)
  const [verifyCode, setVerifyCode] = useState('')
  const [showTermsMore, setShowTermsMore] = useState(false)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')

    if (!isRegister) {
      // Login flow — unchanged
      setLoading(true)
      try {
        await login(email, password)
      } catch (err) {
        setError(err instanceof Error ? err.message : t('auth.auth_failed'))
      } finally {
        setLoading(false)
      }
      return
    }

    // Register flow — two steps
    if (!codeSent) {
      // Step 1: Validate & send code
      if (password !== confirmPassword) {
        setError(t('auth.password_mismatch'))
        return
      }
      if (!agreedTerms) {
        setError(t('auth.agree_required'))
        return
      }
      setLoading(true)
      try {
        await api.sendVerificationCode(email, username, password, referral || undefined)
        setCodeSent(true)
      } catch (err) {
        setError(err instanceof Error ? err.message : t('auth.auth_failed'))
      } finally {
        setLoading(false)
      }
    } else {
      // Step 2: Verify code & complete registration
      setLoading(true)
      try {
        const tokens = await api.verifyCode(email, verifyCode)
        const user = await api.getCurrentUser(tokens.access_token)
        storeLogin(user, tokens.access_token, tokens.refresh_token)
      } catch (err) {
        setError(err instanceof Error ? err.message : t('auth.invalid_code'))
      } finally {
        setLoading(false)
      }
    }
  }

  const handleResend = async () => {
    setError('')
    setLoading(true)
    try {
      await api.sendVerificationCode(email, username, password, referral || undefined)
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : t('auth.auth_failed'))
    } finally {
      setLoading(false)
    }
  }

  const toggleMode = () => {
    setIsRegister(!isRegister)
    setError('')
    setEmail('')
    setPassword('')
    setConfirmPassword('')
    setUsername('')
    setReferral('')
    setShowPassword(false)
    setShowConfirm(false)
    setAgreedTerms(false)
    setCodeSent(false)
    setVerifyCode('')
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
              {t('app.tagline')}
            </p>
          </div>

          {/* Card */}
          <div className="bg-[#1a1a1a]/80 backdrop-blur-2xl rounded-[20px_20px_4px_20px] p-5 sm:p-8 border border-white/[0.08] shadow-[0_20px_60px_rgba(0,0,0,0.3)]">
            <h2 className="text-lg font-semibold text-center mb-6">
              {isRegister ? t('auth.register') : t('auth.login')}
            </h2>

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm px-4 py-2.5 rounded-lg mb-4">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-3">
              {isRegister && codeSent ? (
                /* Step 2: Verification code input */
                <>
                  <div className="text-center py-3">
                    <div className="w-12 h-12 rounded-full bg-imeet-gold/10 flex items-center justify-center mx-auto mb-3">
                      <Mail size={22} className="text-imeet-gold" />
                    </div>
                    <p className="text-sm text-imeet-text-muted mb-1">{t('auth.code_sent')}</p>
                    <p className="text-xs text-white/40">{email}</p>
                  </div>
                  <input
                    type="text"
                    value={verifyCode}
                    onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder={t('auth.code_placeholder')}
                    required
                    maxLength={6}
                    className="input-field w-full text-center text-xl sm:text-2xl tracking-[0.3em] sm:tracking-[0.5em] font-mono"
                    autoFocus
                  />
                  <button
                    type="submit"
                    disabled={loading || verifyCode.length !== 6}
                    className="w-full bg-imeet-gold text-black font-bold py-3 rounded-lg hover:bg-imeet-gold-hover active:scale-[0.98] transition-all disabled:opacity-50 mt-2"
                  >
                    {loading ? t('auth.verifying') : t('auth.verify_code')}
                  </button>
                  <button
                    type="button"
                    onClick={handleResend}
                    disabled={loading}
                    className="w-full text-sm text-imeet-text-muted hover:text-imeet-gold transition-colors disabled:opacity-50"
                  >
                    {t('auth.resend_code')}
                  </button>
                </>
              ) : (
                /* Login or Register Step 1 */
                <>
                  {isRegister && (
                    <input
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder={t('auth.username')}
                      required
                      className="input-field w-full"
                    />
                  )}
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={t('auth.email')}
                    required
                    className="input-field w-full"
                  />
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder={t('auth.password')}
                      required
                      minLength={6}
                      className="input-field w-full pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-imeet-text-muted hover:text-white transition-colors"
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {isRegister && (
                    <>
                      <div className="relative">
                        <input
                          type={showConfirm ? 'text' : 'password'}
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          placeholder={t('auth.confirm_password')}
                          required
                          minLength={6}
                          className="input-field w-full pr-10"
                        />
                        <button
                          type="button"
                          onClick={() => setShowConfirm(!showConfirm)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-imeet-text-muted hover:text-white transition-colors"
                        >
                          {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                        </button>
                      </div>
                      <input
                        type="text"
                        value={referral}
                        onChange={(e) => setReferral(e.target.value)}
                        placeholder={t('auth.referral_placeholder')}
                        className="input-field w-full"
                      />
                      <label className="flex items-start gap-2.5 cursor-pointer pt-1">
                        <input
                          type="checkbox"
                          checked={agreedTerms}
                          onChange={(e) => setAgreedTerms(e.target.checked)}
                          className="mt-0.5 w-4 h-4 rounded border-imeet-border accent-imeet-gold flex-shrink-0"
                        />
                        <span className="text-xs text-imeet-text-muted leading-relaxed">
                          {t('auth.agree_text')}{' '}
                          <Link to="/terms" className="text-imeet-gold hover:underline">{t('auth.terms')}</Link>
                          ,{' '}
                          <Link to="/privacy" className="text-imeet-gold hover:underline">{t('auth.privacy')}</Link>
                          {' '}{t('auth.agree_and')}{' '}
                          <Link to="/security" className="text-imeet-gold hover:underline">{t('auth.security')}</Link>
                          .{' '}
                          {!showTermsMore ? (
                            <button type="button" onClick={() => setShowTermsMore(true)} className="text-imeet-gold hover:underline">more</button>
                          ) : (
                            <span className="text-white/30">{t('auth.disclaimer')}</span>
                          )}
                        </span>
                      </label>
                    </>
                  )}
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-imeet-gold text-black font-bold py-3 rounded-lg hover:bg-imeet-gold-hover active:scale-[0.98] transition-all disabled:opacity-50 mt-2"
                  >
                    {loading
                      ? (isRegister ? t('auth.sending_code') : t('common.loading'))
                      : (isRegister ? t('auth.send_code') : t('auth.login'))
                    }
                  </button>
                </>
              )}
            </form>

            <div className="mt-5 pt-4 border-t border-imeet-border text-center">
              <p className="text-sm text-imeet-text-muted">
                {isRegister ? t('auth.has_account') : t('auth.no_account')}{' '}
                <button
                  onClick={toggleMode}
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

function LegalPage({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col h-screen bg-imeet-black">
      <div className="drag-region h-10 flex-shrink-0" />
      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  )
}

export default function App() {
  const { isAuthenticated } = useAuth()

  return (
    <Routes>
      <Route path="/caption" element={<CaptionOverlay />} />
      <Route path="/terms" element={<LegalPage><TermsOfService /></LegalPage>} />
      <Route path="/privacy" element={<LegalPage><PrivacyPolicy /></LegalPage>} />
      <Route path="/security" element={<LegalPage><SecurityPolicy /></LegalPage>} />
      <Route path="*" element={isAuthenticated ? <AuthenticatedApp /> : <LoginPage />} />
    </Routes>
  )
}
