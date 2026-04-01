import { useAuthStore } from '@/stores/authStore'
import { Check, Crown, Star, Zap, Timer } from 'lucide-react'

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

export default function Subscription() {
  const user = useAuthStore((s) => s.user)
  const currentTier = user?.subscription_tier || 'free'

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
              className={`relative bg-imeet-panel rounded-[10px] p-5 border-2 transition-all hover:-translate-y-1 ${
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
    </div>
  )
}
