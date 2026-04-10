import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Shield, Lock, Server, Eye, RefreshCw, AlertTriangle } from 'lucide-react'

export default function SecurityPolicy() {
  const navigate = useNavigate()

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-12">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-imeet-text-muted hover:text-white transition-colors text-sm mb-2"
      >
        <ArrowLeft size={16} /> Back
      </button>

      <div className="bg-[#1a1a1a] rounded-[20px_20px_4px_20px] border border-white/[0.08] p-8">
        <h1 className="text-2xl font-bold mb-1">Security Policy</h1>
        <p className="text-imeet-text-muted text-sm mb-8">Effective Date: April 6, 2026 &nbsp;|&nbsp; Last Updated: April 6, 2026</p>

        <div className="space-y-6 text-sm text-white/70 leading-relaxed">
          <p>
            At Voxclar, security is foundational — not an afterthought. This document outlines the measures we take to protect your data, your audio, and your privacy across every layer of the Service.
          </p>

          {/* Security Highlights */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <HighlightCard icon={<Lock size={18} />} title="End-to-End Encryption" desc="TLS 1.3 for all data in transit, AES-256 at rest" />
            <HighlightCard icon={<Eye size={18} />} title="Screen Share Safe" desc="Invisible to Zoom, Teams, and Meet screen sharing" />
            <HighlightCard icon={<Server size={18} />} title="Zero Audio Retention" desc="Cloud ASR streams are never stored on our servers" />
            <HighlightCard icon={<Shield size={18} />} title="Server-Side Processing" desc="AI and ASR handled securely on our servers" />
          </div>

          <Section title="1. Architecture Overview">
            <p>Voxclar uses a hybrid architecture designed to minimize data exposure:</p>
            <ul className="list-disc pl-5 space-y-1 mt-2">
              <li><strong className="text-white/80">Desktop Application:</strong> Electron-based app running locally on your machine. Meeting UI, caption overlay, and local engine operate independently of cloud services.</li>
              <li><strong className="text-white/80">Local Engine:</strong> Python-based service running on localhost. Handles audio capture and relays audio to our cloud ASR and AI services.</li>
              <li><strong className="text-white/80">Cloud Backend:</strong> FastAPI server handling authentication, subscriptions, cloud sync, and ASR API.</li>
            </ul>
          </Section>

          <Section title="2. Data Encryption">
            <h3 className="text-white/80 font-medium mt-3 mb-1">In Transit</h3>
            <ul className="list-disc pl-5 space-y-1">
              <li>All client-server communication uses TLS 1.2+ (TLS 1.3 preferred)</li>
              <li>WebSocket connections for real-time ASR streaming are encrypted via WSS</li>
              <li>API keys are transmitted only over HTTPS</li>
            </ul>

            <h3 className="text-white/80 font-medium mt-3 mb-1">At Rest</h3>
            <ul className="list-disc pl-5 space-y-1">
              <li>Database encryption using AES-256</li>
              <li>Passwords hashed with bcrypt (cost factor 12) — never stored in plain text</li>
              <li>API keys stored with one-way hash; full keys displayed only once at generation</li>
              <li>Stripe payment tokens — we never store raw card data</li>
            </ul>
          </Section>

          <Section title="3. Audio Security">
            <div className="bg-white/[0.03] rounded-lg p-4 mt-2">
              <p className="text-white/80 font-medium">Cloud ASR</p>
              <p>Audio is captured via ScreenCaptureKit (macOS) or WASAPI (Windows) and streamed in real-time to our ASR service over an encrypted WebSocket connection. Streams are processed immediately and <strong className="text-white/80">discarded after transcription</strong> — we do not store, log, or retain audio recordings.</p>
            </div>
          </Section>

          <Section title="4. Authentication & Access Control">
            <ul className="list-disc pl-5 space-y-1">
              <li>JWT-based authentication with short-lived access tokens</li>
              <li>Refresh tokens with rotation and revocation</li>
              <li>Per-user data isolation — users cannot access other users' data</li>
              <li>Subscription-based access with secure cloud backend</li>
              <li>API keys scoped per user with independent rate limiting</li>
            </ul>
          </Section>

          <Section title="5. Screen Share Protection">
            <p>The Voxclar floating caption overlay is engineered to be invisible during screen sharing on major video conferencing platforms:</p>
            <ul className="list-disc pl-5 space-y-1 mt-2">
              <li>Uses OS-level window properties that exclude the overlay from screen capture</li>
              <li>Tested against Zoom, Microsoft Teams, and Google Meet</li>
              <li>No pixel data from the overlay is transmitted through screen sharing</li>
            </ul>
            <p className="mt-2 text-white/50 text-xs">Note: Screen share safety depends on the OS and conferencing platform version. We recommend testing with your specific setup.</p>
          </Section>

          <Section title="6. Third-Party Security">
            <p>When you use AI-powered answers, meeting context (not raw audio) is sent to your selected AI provider:</p>
            <ul className="list-disc pl-5 space-y-1 mt-2">
              <li><strong className="text-white/80">Anthropic (Claude):</strong> Data is not used for model training per their API terms</li>
              <li><strong className="text-white/80">OpenAI (GPT):</strong> API data is not used for training per their business terms</li>
              <li><strong className="text-white/80">DeepSeek:</strong> Used for general queries with minimal context</li>
            </ul>
            <p className="mt-2">Your meeting context is processed securely through our server-side AI pipeline.</p>
          </Section>

          <Section title="7. Infrastructure Security">
            <ul className="list-disc pl-5 space-y-1">
              <li>Cloud infrastructure hosted on hardened, regularly patched servers</li>
              <li>PostgreSQL database with encrypted connections and restricted network access</li>
              <li>Automated dependency vulnerability scanning</li>
              <li>Rate limiting on all API endpoints to prevent abuse</li>
              <li>CORS policies restricting cross-origin access</li>
            </ul>
          </Section>

          <Section title="8. Incident Response">
            <p>In the event of a security incident:</p>
            <ul className="list-disc pl-5 space-y-1 mt-2">
              <li>Affected users will be notified within 72 hours of discovery</li>
              <li>We will provide details on what data was affected and remediation steps</li>
              <li>Compromised credentials (API keys, tokens) will be automatically revoked</li>
              <li>A post-incident report will be published for significant events</li>
            </ul>
          </Section>

          <Section title="9. Vulnerability Reporting">
            <p>If you discover a security vulnerability in Voxclar, please report it responsibly:</p>
            <div className="bg-white/[0.03] rounded-lg p-4 mt-2">
              <p>Email: <span className="text-imeet-gold">service@voxclar.com</span></p>
              <p className="mt-1">Subject line: <span className="text-white/80">[SECURITY] Brief description</span></p>
              <p className="mt-2 text-white/50">We appreciate responsible disclosure and will acknowledge your report within 48 hours. We do not pursue legal action against good-faith security researchers.</p>
            </div>
          </Section>

          <Section title="10. Updates to This Policy">
            <p>This Security Policy is reviewed and updated regularly to reflect changes in our security practices and infrastructure. Check this page for the latest version.</p>
          </Section>
        </div>
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="text-base font-semibold text-white mb-2">{title}</h2>
      {children}
    </div>
  )
}

function HighlightCard({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-4 flex items-start gap-3">
      <div className="w-9 h-9 rounded-lg bg-imeet-gold/10 flex items-center justify-center text-imeet-gold flex-shrink-0">
        {icon}
      </div>
      <div>
        <p className="text-white/90 font-medium text-sm">{title}</p>
        <p className="text-white/50 text-xs mt-0.5">{desc}</p>
      </div>
    </div>
  )
}
