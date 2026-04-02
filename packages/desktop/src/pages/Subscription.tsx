import { useState } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { Check, Crown, Star, Zap, Timer, Gift, Copy, CheckCircle, Users } from 'lucide-react'

const PLANS = [
  {
    id: 'free',
    name: 'Free',
    tier: 'free',
    price: 0,
    icon: Zap,
    minutes: 10,
    features: [
      '10 min/month',
      'Real-time captions',
      'Basic AI answers',
    ],
  },
  {
    id: 'basic',
    name: 'Basic',
    tier: 'basic',
    price: 9.99,
    icon: Star,
    minutes: 60,
    features: [
      '60 min/month',
      'Real-time captions',
      'GPT-powered answers',
      'Meeting export (TXT)',
    ],
  },
  {
    id: 'standard',
    name: 'Standard',
    tier: 'standard',
    price: 19.99,
    icon: Crown,
    minutes: 200,
    popular: true,
    features: [
      '200 min/month',
      'Real-time captions',
      'Claude-powered answers',
      'Export (PDF/JSON)',
      'Resume matching',
    ],
  },
  {
    id: 'pro',
    name: 'Pro',
    tier: 'pro',
    price: 49.99,
    icon: Crown,
    minutes: -1,
    features: [
      'Unlimited minutes',
      'Real-time captions',
      'All AI models',
      'All export formats',
      'Custom prompts',
      'API access',
    ],
  },
]

// 本地生成邀请码（后端没跑时的 fallback）
function getOrCreateInviteCode(): string {
  const key = 'voxclar_invite_code'
  let code = localStorage.getItem(key)
  if (!code) {
    const chars = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
    code = Array.from({ length: 6 }, () => chars[Math.floor(Math.random() * chars.length)]).join('')
    localStorage.setItem(key, code)
  }
  return code
}

export default function Subscription() {
  const user = useAuthStore((s) => s.user)
  const currentTier = user?.subscription_tier || 'free'
  const [copied, setCopied] = useState(false)
  const inviteCode = getOrCreateInviteCode()

  const copyCode = () => {
    navigator.clipboard.writeText(inviteCode)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-imeet-gold mb-2">Subscription Plans</h2>
        <div className="flex items-center justify-center gap-3">
          <Timer size={20} className="text-imeet-gold" />
          <span className="text-lg">
            <span className="text-imeet-gold font-bold">{user?.points_balance ?? 10}</span>
            <span className="text-imeet-text-secondary ml-1">minutes remaining</span>
          </span>
        </div>
      </div>

      {/* Plans Grid */}
      <div className="grid grid-cols-4 gap-4">
        {PLANS.map((plan) => {
          const isCurrent = currentTier === plan.tier
          const Icon = plan.icon

          return (
            <div
              key={plan.id}
              className={`relative bg-imeet-panel rounded-[20px_4px_20px_20px] p-5 border-2 transition-all hover:-translate-y-1 ${
                plan.popular
                  ? 'border-imeet-gold shadow-[0_0_20px_rgba(255,215,0,0.1)]'
                  : isCurrent
                    ? 'border-imeet-gold/50'
                    : 'border-imeet-border hover:border-imeet-border-light'
              }`}
            >
              {/* Popular Badge */}
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="bg-imeet-gold text-black text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider">
                    Popular
                  </span>
                </div>
              )}

              <div className="text-center mb-4">
                <div className="w-10 h-10 rounded-lg bg-imeet-gold/10 flex items-center justify-center mx-auto mb-3">
                  <Icon size={20} className="text-imeet-gold" />
                </div>
                <h3 className="text-lg font-bold text-imeet-gold">{plan.name}</h3>
                <div className="mt-2">
                  <span className="text-2xl font-bold">${plan.price}</span>
                  <span className="text-imeet-text-muted text-sm">/mo</span>
                </div>
                <p className="text-xs text-imeet-text-muted mt-1">
                  {plan.minutes === -1 ? 'Unlimited' : `${plan.minutes} min`}
                </p>
              </div>

              {/* Features */}
              <div className="space-y-2 mb-5">
                {plan.features.map((f) => (
                  <div key={f} className="flex items-center gap-2 text-sm">
                    <Check size={14} className="text-imeet-gold flex-shrink-0" />
                    <span className="text-imeet-text-secondary">{f}</span>
                  </div>
                ))}
              </div>

              {/* Button */}
              <button
                disabled={isCurrent}
                className={`w-full py-2.5 rounded-lg text-sm font-semibold transition-all ${
                  isCurrent
                    ? 'bg-white/10 text-imeet-text-muted cursor-default'
                    : plan.popular
                      ? 'bg-imeet-gold text-black hover:bg-imeet-gold-hover active:scale-[0.98]'
                      : 'border-2 border-imeet-gold/50 text-imeet-gold hover:bg-imeet-gold/10'
                }`}
              >
                {isCurrent ? 'Current Plan' : 'Upgrade'}
              </button>
            </div>
          )
        })}
      </div>

      {/* Invite Friends */}
      <div className="bg-imeet-panel rounded-[20px_4px_20px_20px] p-6 border border-imeet-border">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-lg bg-imeet-gold/10 flex items-center justify-center">
            <Gift size={20} className="text-imeet-gold" />
          </div>
          <div>
            <h3 className="font-semibold text-lg">Invite Friends, Earn Free Time</h3>
            <p className="text-xs text-imeet-text-muted">Share your code — both of you get bonus minutes</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-5">
          {/* Invite Code */}
          <div>
            <p className="text-xs text-imeet-text-muted mb-2 uppercase tracking-wider">Your Invite Code</p>
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
            <p className="text-[11px] text-imeet-text-muted mt-2">
              Share this code with friends when they sign up
            </p>
          </div>

          {/* Rewards Info */}
          <div className="space-y-3">
            <p className="text-xs text-imeet-text-muted uppercase tracking-wider">How It Works</p>
            <div className="space-y-2">
              <div className="flex items-start gap-2">
                <div className="w-5 h-5 rounded-full bg-imeet-gold/15 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-[10px] text-imeet-gold font-bold">1</span>
                </div>
                <p className="text-sm text-imeet-text-secondary">Friend signs up with your code → <span className="text-imeet-gold font-medium">they get 10 min free</span></p>
              </div>
              <div className="flex items-start gap-2">
                <div className="w-5 h-5 rounded-full bg-imeet-gold/15 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-[10px] text-imeet-gold font-bold">2</span>
                </div>
                <p className="text-sm text-imeet-text-secondary">Friend makes first purchase → <span className="text-imeet-gold font-medium">you get 30 min free</span></p>
              </div>
            </div>

            {/* Stats */}
            <div className="flex gap-4 pt-2">
              <div className="flex items-center gap-1.5 text-xs text-imeet-text-muted">
                <Users size={12} />
                <span>0 invited</span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-imeet-text-muted">
                <Timer size={12} />
                <span>0 min earned</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
