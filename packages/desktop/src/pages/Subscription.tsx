import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { api } from '@/services/api'
import {
  Check, Crown, Star, Zap, Timer, Gift, Copy, CheckCircle, Users,
  ShieldCheck, Plus, ExternalLink, CreditCard, Infinity, Cpu,
} from 'lucide-react'

const electronAPI = (window as unknown as { electronAPI?: {
  openExternal: (url: string) => void
} }).electronAPI

function openUrl(url: string) {
  if (electronAPI?.openExternal) {
    electronAPI.openExternal(url)
  } else {
    window.open(url, '_blank')
  }
}

export default function Subscription() {
  const { t } = useTranslation()
  const user = useAuthStore((s) => s.user)
  const currentTier = user?.subscription_tier || 'free'
  const [copied, setCopied] = useState(false)
  const [loading, setLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [inviteCode, setInviteCode] = useState('------')
  const [referralStats, setReferralStats] = useState({ total_referred: 0, total_rewards_minutes: 0 })

  useEffect(() => {
    api.getInviteCode().then((res) => setInviteCode(res.invite_code)).catch(() => {})
    api.getReferralStats().then((res) => setReferralStats(res)).catch(() => {})
  }, [])

  const PLANS = [
    {
      id: 'free', name: t('subscription.plan_free'), tier: 'free',
      price: 0, priceLabel: '$0', period: '', icon: Zap,
      minutes: t('subscription.plan_free_min'),
      features: [t('subscription.plan_free_feat1'), t('subscription.plan_free_feat2'), t('subscription.plan_free_feat3')],
    },
    {
      id: 'standard', name: t('subscription.plan_standard'), tier: 'standard',
      price: 19.99, priceLabel: '$19.99', period: '/mo', icon: Star,
      minutes: t('subscription.plan_std_min'), popular: true,
      features: [t('subscription.plan_std_feat1'), t('subscription.plan_std_feat2'), t('subscription.plan_std_feat3'), t('subscription.plan_std_feat4'), t('subscription.plan_std_feat5'), t('subscription.plan_std_feat6')],
    },
    {
      id: 'pro', name: t('subscription.plan_pro'), tier: 'pro',
      price: 49.99, priceLabel: '$49.99', period: '/mo', icon: Crown,
      minutes: t('subscription.plan_pro_min'),
      features: [t('subscription.plan_pro_feat1'), t('subscription.plan_pro_feat2'), t('subscription.plan_pro_feat3'), t('subscription.plan_pro_feat4'), t('subscription.plan_pro_feat5'), t('subscription.plan_pro_feat6'), t('subscription.plan_pro_feat7'), t('subscription.plan_pro_feat8')],
    },
    {
      id: 'lifetime', name: t('subscription.plan_lifetime'), tier: 'lifetime',
      price: 299, priceLabel: '$299', period: ` ${t('subscription.once')}`, icon: ShieldCheck,
      minutes: t('subscription.plan_lt_min'),
      features: [t('subscription.plan_lt_feat1'), t('subscription.plan_lt_feat2'), t('subscription.plan_lt_feat3'), t('subscription.plan_lt_feat4'), t('subscription.plan_lt_feat5'), t('subscription.plan_lt_feat6')],
    },
  ]

  const totalMinutes = (user?.points_balance ?? 0) + (user?.topup_balance ?? 0)

  const copyCode = () => {
    navigator.clipboard.writeText(inviteCode)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleSubscribe = async (planId: string) => {
    if (planId === 'free') return
    setLoading(planId)
    setError(null)
    try {
      const { checkout_url } = await api.createCheckout(planId)
      openUrl(checkout_url)
    } catch (err: any) {
      setError(err?.message || 'Failed to connect to server. Please try again.')
    } finally {
      setLoading(null)
    }
  }

  const handleManageBilling = async () => {
    setError(null)
    try {
      const { portal_url } = await api.createPortal()
      openUrl(portal_url)
    } catch (err: any) {
      setError(err?.message || 'Failed to open billing portal.')
    }
  }

  const handleAsrTopUp = async () => {
    setLoading('asr_topup')
    setError(null)
    try {
      const { checkout_url } = await api.createCheckout('asr_topup')
      openUrl(checkout_url)
    } catch (err: any) {
      setError(err?.message || 'Failed to create checkout.')
    } finally {
      setLoading(null)
    }
  }

  const handleTopUp = async () => {
    setLoading('topup')
    setError(null)
    try {
      const { checkout_url } = await api.createCheckout('topup')
      openUrl(checkout_url)
    } catch (err: any) {
      setError(err?.message || 'Failed to create checkout.')
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-imeet-gold mb-2">{t('subscription.title')}</h2>
        {currentTier === 'lifetime' ? (
          <div className="flex items-center justify-center gap-2">
            <ShieldCheck size={20} className="text-purple-400" />
            <span className="text-lg text-purple-400 font-bold">∞ {t('subscription.lifetime_label')}</span>
          </div>
        ) : (
          <div className="flex items-center justify-center gap-4">
            <div className="flex items-center gap-2">
              <Timer size={20} className="text-imeet-gold" />
              <span className="text-lg">
                <span className="text-imeet-gold font-bold">{user?.points_balance ?? 10}</span>
                <span className="text-imeet-text-secondary ml-1">{t('subscription.subscription_min')}</span>
              </span>
            </div>
            {(user?.topup_balance ?? 0) > 0 && (
              <div className="flex items-center gap-2">
                <Plus size={16} className="text-green-400" />
                <span className="text-lg">
                  <span className="text-green-400 font-bold">{user?.topup_balance}</span>
                  <span className="text-imeet-text-secondary ml-1">{t('subscription.boost_min')}</span>
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-sm text-red-400 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 ml-3">✕</button>
        </div>
      )}

      {/* Plans Grid */}
      <div className="grid grid-cols-4 gap-4">
        {PLANS.map((plan) => {
          const isCurrent = currentTier === plan.tier
          const Icon = plan.icon
          const isLifetime = plan.id === 'lifetime'

          return (
            <div
              key={plan.id}
              className={`relative bg-imeet-panel rounded-[20px_4px_20px_20px] p-5 border-2 transition-all hover:-translate-y-1 ${
                plan.popular
                  ? 'border-imeet-gold shadow-[0_0_20px_rgba(255,215,0,0.1)]'
                  : isCurrent
                    ? 'border-imeet-gold/50'
                    : isLifetime
                      ? 'border-purple-500/40 hover:border-purple-400/60'
                      : 'border-imeet-border hover:border-imeet-border-light'
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="bg-imeet-gold text-black text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider">
                    {t('subscription.popular')}
                  </span>
                </div>
              )}

              {isLifetime && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="bg-purple-500 text-white text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider">
                    {t('subscription.best_value')}
                  </span>
                </div>
              )}

              <div className="text-center mb-4">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center mx-auto mb-3 ${
                  isLifetime ? 'bg-purple-500/10' : 'bg-imeet-gold/10'
                }`}>
                  <Icon size={20} className={isLifetime ? 'text-purple-400' : 'text-imeet-gold'} />
                </div>
                <h3 className={`text-lg font-bold ${isLifetime ? 'text-purple-400' : 'text-imeet-gold'}`}>
                  {plan.name}
                </h3>
                <div className="mt-2">
                  <span className="text-2xl font-bold">{plan.priceLabel}</span>
                  <span className="text-imeet-text-muted text-sm">{plan.period}</span>
                </div>
                <p className="text-xs text-imeet-text-muted mt-1">{plan.minutes}</p>
              </div>

              <div className="space-y-2 mb-5">
                {plan.features.map((f, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <Check size={14} className={`flex-shrink-0 ${isLifetime ? 'text-purple-400' : 'text-imeet-gold'}`} />
                    <span className="text-imeet-text-secondary">{f}</span>
                  </div>
                ))}
              </div>

              <button
                disabled={isCurrent || loading === plan.id}
                onClick={() => handleSubscribe(plan.id)}
                className={`w-full py-2.5 rounded-lg text-sm font-semibold transition-all ${
                  isCurrent
                    ? 'bg-white/10 text-imeet-text-muted cursor-default'
                    : loading === plan.id
                      ? 'bg-white/5 text-imeet-text-muted cursor-wait'
                      : isLifetime
                        ? 'bg-purple-500 text-white hover:bg-purple-400 active:scale-[0.98]'
                        : plan.popular
                          ? 'bg-imeet-gold text-black hover:bg-imeet-gold-hover active:scale-[0.98]'
                          : 'border-2 border-imeet-gold/50 text-imeet-gold hover:bg-imeet-gold/10'
                }`}
              >
                {isCurrent ? t('subscription.current_plan') : loading === plan.id ? t('subscription.opening') : plan.id === 'free' ? t('subscription.current') : t('subscription.get_started')}
              </button>
            </div>
          )
        })}
      </div>

      {/* Top-up + Manage */}
      <div className="grid grid-cols-2 gap-4">
        {currentTier === 'lifetime' ? (
          <div className="bg-imeet-panel rounded-[20px_4px_20px_20px] p-5 border border-purple-500/30">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                  <Cpu size={20} className="text-purple-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-purple-400">{t('subscription.asr_title')}</h3>
                  <p className="text-xs text-imeet-text-muted">{t('subscription.asr_desc')}</p>
                </div>
              </div>
              <button
                onClick={handleAsrTopUp}
                disabled={loading === 'asr_topup'}
                className="px-5 py-2.5 bg-purple-500 text-white rounded-lg text-sm font-semibold hover:bg-purple-400 active:scale-[0.98] transition-all disabled:opacity-50"
              >
                {loading === 'asr_topup' ? t('subscription.opening') : t('subscription.buy_asr')}
              </button>
            </div>
            <p className="text-xs text-imeet-text-muted">
              <span className="text-purple-400 font-medium">{user?.asr_balance ?? 0} {t('subscription.asr_remaining')}</span> {t('subscription.asr_note')}
            </p>
          </div>
        ) : (
          <div className="bg-imeet-panel rounded-[20px_4px_20px_20px] p-5 border border-imeet-border">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
                  <Plus size={20} className="text-green-400" />
                </div>
                <div>
                  <h3 className="font-semibold">{t('subscription.time_boost')}</h3>
                  <p className="text-xs text-imeet-text-muted">{t('subscription.time_boost_desc')}</p>
                </div>
              </div>
              <button
                onClick={handleTopUp}
                disabled={loading === 'topup'}
                className="px-5 py-2.5 bg-green-500 text-white rounded-lg text-sm font-semibold hover:bg-green-400 active:scale-[0.98] transition-all disabled:opacity-50"
              >
                {loading === 'topup' ? t('subscription.opening') : t('subscription.buy_boost')}
              </button>
            </div>
            <p className="text-xs text-imeet-text-muted">{t('subscription.boost_note')}</p>
          </div>
        )}

        {currentTier !== 'free' && (
          <div className="bg-imeet-panel rounded-[20px_4px_20px_20px] p-5 border border-imeet-border">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-imeet-gold/10 flex items-center justify-center">
                  <CreditCard size={20} className="text-imeet-gold" />
                </div>
                <div>
                  <h3 className="font-semibold">{t('subscription.manage_billing')}</h3>
                  <p className="text-xs text-imeet-text-muted">{t('subscription.manage_billing_desc')}</p>
                </div>
              </div>
              <button
                onClick={handleManageBilling}
                className="flex items-center gap-2 px-4 py-2.5 border-2 border-imeet-gold/50 text-imeet-gold rounded-lg text-sm font-semibold hover:bg-imeet-gold/10 transition-all"
              >
                <ExternalLink size={14} />
                {t('subscription.open_portal')}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Invite Friends */}
      <div className="bg-imeet-panel rounded-[20px_4px_20px_20px] p-6 border border-imeet-border">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-lg bg-imeet-gold/10 flex items-center justify-center">
            <Gift size={20} className="text-imeet-gold" />
          </div>
          <div>
            <h3 className="font-semibold text-lg">{t('subscription.invite_title')}</h3>
            <p className="text-xs text-imeet-text-muted">{t('subscription.invite_desc')}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-5">
          <div>
            <p className="text-xs text-imeet-text-muted mb-2 uppercase tracking-wider">{t('subscription.invite_code')}</p>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-black/30 border-2 border-imeet-gold/30 rounded-lg px-4 py-3 text-center">
                <span className="text-2xl font-mono font-bold tracking-[0.3em] text-imeet-gold">{inviteCode}</span>
              </div>
              <button
                onClick={copyCode}
                className={`px-4 py-3 rounded-lg font-medium text-sm transition-all ${
                  copied
                    ? 'bg-green-500/20 text-green-400'
                    : 'bg-imeet-gold text-black hover:bg-imeet-gold-hover active:scale-[0.95]'
                }`}
              >
                {copied ? <CheckCircle size={18} /> : <Copy size={18} />}
              </button>
            </div>
            <p className="text-[11px] text-imeet-text-muted mt-2">{t('subscription.invite_share')}</p>
          </div>

          <div className="space-y-3">
            <p className="text-xs text-imeet-text-muted uppercase tracking-wider">{t('subscription.how_it_works')}</p>
            <div className="space-y-2">
              <div className="flex items-start gap-2">
                <div className="w-5 h-5 rounded-full bg-imeet-gold/15 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-[10px] text-imeet-gold font-bold">1</span>
                </div>
                <p className="text-sm text-imeet-text-secondary">{t('subscription.invite_step1')} <span className="text-imeet-gold font-medium">{t('subscription.invite_step1_reward')}</span></p>
              </div>
              <div className="flex items-start gap-2">
                <div className="w-5 h-5 rounded-full bg-imeet-gold/15 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-[10px] text-imeet-gold font-bold">2</span>
                </div>
                <p className="text-sm text-imeet-text-secondary">{t('subscription.invite_step2')} <span className="text-imeet-gold font-medium">{t('subscription.invite_step2_reward')}</span></p>
              </div>
            </div>

            <div className="flex gap-4 pt-2">
              <div className="flex items-center gap-1.5 text-xs text-imeet-text-muted">
                <Users size={12} />
                <span>{referralStats.total_referred} {t('subscription.invited')}</span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-imeet-text-muted">
                <Timer size={12} />
                <span>{referralStats.total_rewards_minutes} {t('subscription.earned')}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
