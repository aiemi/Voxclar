import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

export default function PrivacyPolicy() {
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
        <h1 className="text-2xl font-bold mb-1">Privacy Policy</h1>
        <p className="text-imeet-text-muted text-sm mb-8">Effective Date: April 6, 2026 &nbsp;|&nbsp; Last Updated: April 6, 2026</p>

        <div className="space-y-6 text-sm text-white/70 leading-relaxed">
          <p>
            Voxclar ("we," "us," or "our") is committed to protecting your privacy. This Privacy Policy explains what information we collect, how we use it, and your rights regarding your data when you use the Voxclar desktop application, website, and cloud services (the "Service").
          </p>

          <Section title="1. Information We Collect">
            <h3 className="text-white/80 font-medium mt-3 mb-1">1.1 Account Information</h3>
            <p>When you register, we collect your email address, username, and hashed password. We never store passwords in plain text.</p>

            <h3 className="text-white/80 font-medium mt-3 mb-1">1.2 Profile Data</h3>
            <p>You may optionally provide your name, headline, work experience, education, projects, skills, and uploaded resumes. This data is used to personalize AI-generated answers.</p>

            <h3 className="text-white/80 font-medium mt-3 mb-1">1.3 Meeting Data</h3>
            <ul className="list-disc pl-5 space-y-1 mt-1">
              <li><strong className="text-white/80">Subscription users (Standard/Pro):</strong> Transcripts, AI answers, and meeting summaries are stored in our cloud database to enable cross-device sync.</li>
              <li><strong className="text-white/80">Lifetime/Free users:</strong> All meeting data is stored locally on your device. We do not have access to it.</li>
            </ul>

            <h3 className="text-white/80 font-medium mt-3 mb-1">1.4 Audio Data</h3>
            <ul className="list-disc pl-5 space-y-1 mt-1">
              <li><strong className="text-white/80">Local ASR mode:</strong> Audio is processed entirely on your device using faster-whisper. No audio data is transmitted to any server.</li>
              <li><strong className="text-white/80">Cloud ASR mode:</strong> Audio is streamed to our speech recognition service for real-time transcription. Audio streams are processed in real-time and <strong className="text-white/80">not stored</strong> after transcription is complete.</li>
            </ul>

            <h3 className="text-white/80 font-medium mt-3 mb-1">1.5 Payment Information</h3>
            <p>Payments are processed by Stripe. We do not store your credit card number, CVV, or full payment details. We only store your Stripe customer ID and subscription status.</p>

            <h3 className="text-white/80 font-medium mt-3 mb-1">1.6 Usage Data</h3>
            <p>We collect anonymized usage metrics (meeting count, total duration, feature usage) to improve the Service. We do not track keystrokes, screen content, or browsing activity.</p>
          </Section>

          <Section title="2. How We Use Your Information">
            <ul className="list-disc pl-5 space-y-1">
              <li>Provide, maintain, and improve the Service</li>
              <li>Process payments and manage subscriptions</li>
              <li>Generate AI-powered answers based on your profile and preparation materials</li>
              <li>Send transactional emails (account verification, billing receipts)</li>
              <li>Detect and prevent fraud, abuse, and security incidents</li>
              <li>Comply with legal obligations</li>
            </ul>
            <p className="mt-2">We do <strong className="text-white/80">not</strong> sell, rent, or share your personal information with third parties for marketing purposes.</p>
          </Section>

          <Section title="3. Third-Party Services">
            <p>We use the following third-party services:</p>
            <div className="mt-2 space-y-2">
              <div className="bg-white/[0.03] rounded-lg p-3">
                <p className="text-white/80 font-medium">Stripe</p>
                <p>Payment processing. Subject to <a href="https://stripe.com/privacy" target="_blank" rel="noreferrer" className="text-imeet-gold hover:underline">Stripe's Privacy Policy</a>.</p>
              </div>
              <div className="bg-white/[0.03] rounded-lg p-3">
                <p className="text-white/80 font-medium">AI Providers (Claude, OpenAI, DeepSeek)</p>
                <p>When using AI answers, relevant meeting context is sent to your selected AI provider for response generation. No raw audio is shared with AI providers.</p>
              </div>
              <div className="bg-white/[0.03] rounded-lg p-3">
                <p className="text-white/80 font-medium">Voxclar Cloud ASR</p>
                <p>Cloud speech recognition. Audio streams are processed in real-time and not retained after transcription.</p>
              </div>
            </div>
          </Section>

          <Section title="4. Data Storage & Retention">
            <ul className="list-disc pl-5 space-y-1">
              <li>Account data is retained as long as your account is active</li>
              <li>Cloud meeting data (subscribers) is retained until you delete it or close your account</li>
              <li>Local meeting data (lifetime/free) is stored on your device and fully under your control</li>
              <li>Audio streams are processed in real-time and never stored on our servers</li>
              <li>Upon account deletion, all associated cloud data is permanently removed within 30 days</li>
            </ul>
          </Section>

          <Section title="5. Data Security">
            <p>We implement industry-standard security measures including:</p>
            <ul className="list-disc pl-5 space-y-1 mt-2">
              <li>TLS/SSL encryption for all data in transit</li>
              <li>AES-256 encryption for data at rest</li>
              <li>Bcrypt password hashing with salt</li>
              <li>JWT-based authentication with token expiration</li>
              <li>Regular security audits and dependency updates</li>
            </ul>
            <p className="mt-2">For details, see our <button onClick={() => navigate('/security')} className="text-imeet-gold hover:underline">Security Policy</button>.</p>
          </Section>

          <Section title="6. Your Rights">
            <p>You have the right to:</p>
            <ul className="list-disc pl-5 space-y-1 mt-2">
              <li><strong className="text-white/80">Access:</strong> Request a copy of your personal data</li>
              <li><strong className="text-white/80">Correction:</strong> Update inaccurate or incomplete data</li>
              <li><strong className="text-white/80">Deletion:</strong> Request deletion of your account and associated data</li>
              <li><strong className="text-white/80">Portability:</strong> Export your meeting records and profile data</li>
              <li><strong className="text-white/80">Objection:</strong> Opt out of non-essential data processing</li>
            </ul>
            <p className="mt-2">To exercise any of these rights, contact <span className="text-imeet-gold">service@voxclar.com</span>.</p>
          </Section>

          <Section title="7. Cookies & Local Storage">
            <p>The Voxclar desktop app uses localStorage to persist your preferences, session tokens, and local meeting data. We do not use tracking cookies. The website may use essential cookies for authentication and session management only.</p>
          </Section>

          <Section title="8. Children's Privacy">
            <p>Voxclar is not intended for use by individuals under the age of 18. We do not knowingly collect personal information from minors. If you believe a minor has provided us with personal data, contact us immediately.</p>
          </Section>

          <Section title="9. International Data Transfers">
            <p>Your data may be processed in the United States and other countries where our service providers operate. By using the Service, you consent to the transfer of your data to these jurisdictions, which may have different data protection laws than your country of residence.</p>
          </Section>

          <Section title="10. Changes to This Policy">
            <p>We may update this Privacy Policy periodically. Material changes will be communicated via email or in-app notification at least 14 days before they take effect. Continued use of the Service after changes constitutes acceptance.</p>
          </Section>

          <Section title="11. Contact Us">
            <p>For privacy-related questions or requests:</p>
            <p className="mt-2 text-imeet-gold">service@voxclar.com</p>
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
