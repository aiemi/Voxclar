import { Routes, Route } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { useEngine } from '@/hooks/useEngine'
import Sidebar from '@/components/Sidebar'
import TitleBar from '@/components/TitleBar'
import Dashboard from '@/pages/Dashboard'
import Meeting from '@/pages/Meeting'
import Profile from '@/pages/Profile'
import Settings from '@/pages/Settings'
import MeetingRecord from '@/pages/MeetingRecord'
import Setup from '@/pages/Setup'
import TermsOfService from '@/pages/TermsOfService'
import PrivacyPolicy from '@/pages/PrivacyPolicy'
import SecurityPolicy from '@/pages/SecurityPolicy'
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
      <Route path="*" element={isAuthenticated ? <AuthenticatedApp /> : <Setup />} />
    </Routes>
  )
}
