import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { useEngineStore } from '@/stores/engineStore'
import { LayoutDashboard, MessageSquare, User, CreditCard, Settings, LogOut, FileText } from 'lucide-react'
import clsx from 'clsx'

const NAV_ITEMS = [
  { path: '/', icon: LayoutDashboard, labelKey: 'nav.dashboard' },
  { path: '/meeting', icon: MessageSquare, labelKey: 'nav.meeting' },
  { path: '/records', icon: FileText, label: 'Records' },
  { path: '/profile', icon: User, labelKey: 'nav.profile' },
  { path: '/subscription', icon: CreditCard, labelKey: 'nav.subscription' },
  { path: '/settings', icon: Settings, labelKey: 'nav.settings' },
]

export default function Sidebar() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const engineStatus = useEngineStore((s) => s.status)

  const statusColor = {
    disconnected: 'bg-red-500',
    connecting: 'bg-yellow-500 animate-pulse',
    ready: 'bg-[#67cd4e]',
    running: 'bg-imeet-gold animate-pulse',
    error: 'bg-red-500',
  }[engineStatus]

  return (
    <div className="w-56 h-full bg-[#0a0a0a] border-r border-white/[0.06] flex flex-col">
      {/* macOS 交通灯 */}
      <div className="drag-region h-10 flex-shrink-0" />

      {/* Logo */}
      <div className="px-5 pb-5">
        <h1 className="text-xl font-bold tracking-tight">
          <span className="text-imeet-gold">Vox</span>
          <span className="text-white">clar</span>
        </h1>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const isActive = location.pathname === item.path
          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={clsx(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200',
                isActive
                  ? 'text-imeet-gold bg-white/[0.06]'
                  : 'text-white/50 hover:text-white/80 hover:bg-white/[0.03]'
              )}
            >
              <item.icon size={17} strokeWidth={isActive ? 2.2 : 1.8} />
              <span>{'label' in item ? item.label : t(item.labelKey)}</span>
            </button>
          )
        })}
      </nav>

      {/* Engine status */}
      <div className="px-5 py-2">
        <div className="flex items-center gap-2 text-[11px] text-white/40">
          <div className={clsx('w-1.5 h-1.5 rounded-full', statusColor)} />
          <span className="capitalize">{engineStatus}</span>
        </div>
      </div>

      {/* User */}
      <div className="p-4 mx-3 mb-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <p className="text-sm font-medium truncate">{user?.username || 'User'}</p>
            <p className="text-[11px] text-imeet-gold">
              {user?.points_balance ?? 10} min left
            </p>
          </div>
          <button
            onClick={logout}
            className="text-white/30 hover:text-red-400 transition-colors p-1"
            title="Logout"
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </div>
  )
}
