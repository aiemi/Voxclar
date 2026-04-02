import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { useEngineStore } from '@/stores/engineStore'
import { Mic, Activity, Play, Zap, Shield, Globe, Timer, FileText, Brain } from 'lucide-react'
import clsx from 'clsx'
import AnimatedText from '@/components/AnimatedText'

export default function Dashboard() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const engineStatus = useEngineStore((s) => s.status)

  const statusColor = {
    disconnected: 'bg-red-500',
    connecting: 'bg-[#f5c148] animate-pulse',
    ready: 'bg-[#67cd4e]',
    running: 'bg-imeet-gold animate-pulse',
    error: 'bg-[#cd4e4e]',
  }[engineStatus]

  return (
    <div className="space-y-5">
      {/* Welcome + Quick Start */}
      <div className="bg-[#1a1a1a] rounded-[20px_20px_4px_20px] border border-white/[0.08] p-6">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-2xl font-bold">
              <AnimatedText text={`${t('dashboard.welcome')}, `} />
              <AnimatedText text={user?.username || 'User'} className="text-imeet-gold" />
            </h2>
            <p className="text-white/[0.35] text-sm mt-1">
              {user?.subscription_tier ? `${user.subscription_tier.charAt(0).toUpperCase() + user.subscription_tier.slice(1)} Plan` : 'Free Plan'}
            </p>
          </div>
          {/* Engine status pill */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.08]">
            <div className={clsx('w-2 h-2 rounded-full', statusColor)} />
            <span className="text-xs text-white/[0.5] capitalize">{engineStatus}</span>
          </div>
        </div>
        <button
          onClick={() => navigate('/meeting')}
          className="w-full bg-imeet-gold text-black font-bold py-3.5 rounded-[8px] flex items-center justify-center gap-3 hover:bg-imeet-gold-hover active:scale-[0.98] transition-all text-base"
        >
          <Play size={20} />
          {t('dashboard.quick_start')}
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-[#1a1a1a] rounded-[20px_4px_20px_20px] border border-white/[0.08] p-5 hover:-translate-y-1 transition-transform duration-300">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
              <Mic size={18} className="text-blue-400" />
            </div>
            <span className="text-sm text-white/[0.5]">Meetings</span>
          </div>
          <p className="text-3xl font-bold">0</p>
        </div>
        <div className="bg-[#1a1a1a] rounded-[4px_20px_20px_20px] border border-white/[0.08] p-5 hover:-translate-y-1 transition-transform duration-300">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-imeet-gold/10 flex items-center justify-center">
              <Timer size={18} className="text-imeet-gold" />
            </div>
            <span className="text-sm text-white/[0.5]">Time Left</span>
          </div>
          <p className="text-3xl font-bold text-imeet-gold">{user?.points_balance ?? 10} <span className="text-base font-normal text-white/[0.35]">min</span></p>
        </div>
      </div>

      {/* Feature Grid — 4 cards with different corner cuts like website */}
      <div className="grid grid-cols-2 gap-4">
        {[
          { icon: Zap, title: 'Real-time Captions', desc: 'Word-by-word powered by Deepgram Nova-2', radius: '20px 20px 4px 20px' },
          { icon: Brain, title: 'AI Answers', desc: 'Claude & GPT with your resume context', radius: '20px 4px 20px 20px' },
          { icon: Shield, title: 'Screen Share Safe', desc: 'Invisible in Zoom, Teams, Meet', radius: '4px 20px 20px 20px' },
          { icon: FileText, title: 'Meeting Records', desc: 'Full transcript + branded PDF export', radius: '20px 20px 20px 4px' },
        ].map((feat) => (
          <div
            key={feat.title}
            className="bg-white/[0.02] border border-white/[0.06] p-5 hover:-translate-y-1 hover:border-imeet-gold/[0.15] transition-all duration-300 cursor-default"
            style={{ borderRadius: feat.radius }}
          >
            <feat.icon size={22} className="text-imeet-gold mb-3" />
            <h3 className="text-imeet-gold font-semibold text-[13px] mb-1">{feat.title}</h3>
            <p className="text-[12px] text-white/[0.4] leading-relaxed">{feat.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
