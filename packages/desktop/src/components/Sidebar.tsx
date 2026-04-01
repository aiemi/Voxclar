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
    connecting: 'bg-yellow-500',
    ready: 'bg-green-500',
    running: 'bg-imeet-gold animate-pulse',
    error: 'bg-red-500',
  }[engineStatus]

  return (
    <div className="w-56 h-full bg-imeet-panel border-r border-imeet-border flex flex-col">
      {/* macOS 交通灯区域 */}
      <div className="drag-region h-10 flex-shrink-0" />

      {/* Logo */}
      <div className="px-4 pb-4">
        <h1 className="text-xl font-bold">
          <span className="text-imeet-gold">Vox</span>
          <span className="text-white">clar</span>
        </h1>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = location.pathname === item.path
          return (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={clsx('nav-item w-full', isActive && 'nav-item-active')}
            >
              <item.icon size={18} />
              <span className="text-sm">{'label' in item ? item.label : t(item.labelKey)}</span>
            </button>
          )
        })}
      </nav>

      {/* Engine status */}
      <div className="px-4 py-2">
        <div className="flex items-center gap-2 text-xs text-imeet-text-secondary">
          <div className={clsx('w-2 h-2 rounded-full', statusColor)} />
          <span className="capitalize">{engineStatus}</span>
        </div>
      </div>

      {/* User */}
      <div className="p-4 border-t border-imeet-border">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <p className="text-sm font-medium truncate">{user?.username || 'User'}</p>
            <p className="text-xs text-imeet-gold">
              {user?.points_balance ?? 10} min left
            </p>
          </div>
          <button
            onClick={logout}
            className="text-imeet-text-secondary hover:text-red-400 transition-colors"
            title="Logout"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
