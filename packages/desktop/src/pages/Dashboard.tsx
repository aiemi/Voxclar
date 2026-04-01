import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { useEngineStore } from '@/stores/engineStore'
import { Mic, Clock, Activity, Play, Zap, Shield, Globe, Timer } from 'lucide-react'
import clsx from 'clsx'

export default function Dashboard() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const engineStatus = useEngineStore((s) => s.status)

  const statusColor = {
    disconnected: 'bg-red-500',
    connecting: 'bg-yellow-500 animate-pulse',
    ready: 'bg-green-500',
    running: 'bg-imeet-gold animate-pulse',
    error: 'bg-red-500',
  }[engineStatus]

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div>
        <h2 className="text-2xl font-bold">
          {t('dashboard.welcome')}, <span className="text-imeet-gold">{user?.username || 'User'}</span>
        </h2>
        <p className="text-imeet-text-muted text-sm mt-1">
          {user?.subscription_tier ? `${user.subscription_tier.charAt(0).toUpperCase() + user.subscription_tier.slice(1)} Plan` : 'Free Plan'}
        </p>
      </div>

      {/* Quick Start */}
      <button
        onClick={() => navigate('/meeting')}
        className="w-full bg-imeet-gold text-black font-bold py-4 rounded-[10px] flex items-center justify-center gap-3 hover:bg-imeet-gold-hover active:scale-[0.99] transition-all text-lg"
      >
        <Play size={22} />
        {t('dashboard.quick_start')}
      </button>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4">
        {[
          { icon: Mic, label: 'Meetings', value: '0', color: 'text-blue-400', bg: 'bg-blue-500/10' },
          { icon: Timer, label: 'Time Left', value: `${user?.points_balance ?? 10} min`, color: 'text-imeet-gold', bg: 'bg-imeet-gold/10' },
        ].map((stat) => (
          <div key={stat.label} className="bg-imeet-panel rounded-[10px] p-5 border border-imeet-border">
            <div className="flex items-center gap-3 mb-3">
              <div className={`w-9 h-9 rounded-lg ${stat.bg} flex items-center justify-center`}>
                <stat.icon size={18} className={stat.color} />
              </div>
              <span className="text-sm text-imeet-text-secondary">{stat.label}</span>
            </div>
            <p className="text-2xl font-bold">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Feature Highlights — matching web design */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { icon: Zap, title: 'Real-time Captions', desc: 'Deepgram Nova-2 powered, word-by-word like Zoom' },
          { icon: Shield, title: 'Screen Share Safe', desc: 'Hidden from Zoom/Teams screen sharing' },
          { icon: Globe, title: 'Multi-language', desc: 'English, Chinese, Japanese & auto-detect' },
        ].map((feat) => (
          <div
            key={feat.title}
            className="bg-white/[0.03] rounded-[10px] p-5 text-center hover:-translate-y-1 transition-transform"
          >
            <feat.icon size={24} className="text-imeet-gold mx-auto mb-3" />
            <h3 className="text-imeet-gold font-semibold text-sm mb-1">{feat.title}</h3>
            <p className="text-xs text-imeet-text-muted leading-relaxed">{feat.desc}</p>
          </div>
        ))}
      </div>

      {/* Engine Status */}
      <div className="bg-imeet-panel rounded-[10px] p-5 border border-imeet-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-imeet-gold/10 flex items-center justify-center">
            <Activity size={18} className="text-imeet-gold" />
          </div>
          <div>
            <h3 className="font-semibold text-sm">{t('dashboard.engine_status')}</h3>
            <div className="flex items-center gap-2 mt-0.5">
              <div className={clsx('w-2 h-2 rounded-full', statusColor)} />
              <span className="text-sm text-imeet-text-secondary capitalize">{engineStatus}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
