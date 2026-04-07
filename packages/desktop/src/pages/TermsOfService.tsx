import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'

export default function TermsOfService() {
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
        <h1 className="text-2xl font-bold mb-1">Terms of Service</h1>
        <p className="text-imeet-text-muted text-sm mb-8">Effective Date: April 6, 2026 &nbsp;|&nbsp; Last Updated: April 6, 2026</p>

        <div className="space-y-6 text-sm text-white/70 leading-relaxed">
          <p>
            Welcome to Voxclar. These Terms of Service ("Terms") govern your access to and use of the Voxclar desktop application, website, cloud services, and APIs (collectively, the "Service") provided by Voxclar ("we," "us," or "our"). By creating an account or using the Service, you agree to be bound by these Terms.
          </p>

          <Section title="1. Eligibility">
            <p>You must be at least 18 years old to use Voxclar. By using the Service, you represent that you have the legal capacity to enter into a binding agreement.</p>
          </Section>

          <Section title="2. Account Registration">
            <p>You must provide accurate information when creating an account. You are responsible for maintaining the confidentiality of your credentials and for all activities that occur under your account. Notify us immediately at <Gold>service@voxclar.com</Gold> if you suspect unauthorized access.</p>
          </Section>

          <Section title="3. Description of Service">
            <p>Voxclar is an AI-powered meeting assistant that provides:</p>
            <ul className="list-disc pl-5 space-y-1 mt-2">
              <li>Real-time speech-to-text transcription (local or cloud-based)</li>
              <li>AI-generated contextual answers during meetings</li>
              <li>Meeting recording, summarization, and export</li>
              <li>Voxclar Cloud ASR API for programmatic speech recognition</li>
            </ul>
          </Section>

          <Section title="4. Subscription Plans & Payments">
            <p><strong className="text-white/90">Subscription Plans:</strong> We offer Standard, Pro, and Lifetime plans. Subscription plans renew automatically each billing cycle unless cancelled. You may cancel at any time through the billing portal; cancellation takes effect at the end of the current billing period.</p>
            <p className="mt-2"><strong className="text-white/90">Lifetime License:</strong> A one-time purchase granting perpetual access to core features. Lifetime licenses are non-refundable after activation and are locked to a single device at a time.</p>
            <p className="mt-2"><strong className="text-white/90">Add-ons:</strong> Time Boost and ASR minute packs are one-time purchases that never expire. Minutes are consumed on a subscription-first basis.</p>
            <p className="mt-2"><strong className="text-white/90">Refunds:</strong> Subscription payments are non-refundable for the current billing period. If you believe you were charged in error, contact <Gold>service@voxclar.com</Gold> within 7 days.</p>
          </Section>

          <Section title="5. Acceptable Use">
            <p>You agree NOT to:</p>
            <ul className="list-disc pl-5 space-y-1 mt-2">
              <li>Record conversations without the consent of all participants where required by law</li>
              <li>Use the Service for any illegal, fraudulent, or deceptive purpose</li>
              <li>Reverse-engineer, decompile, or disassemble the application</li>
              <li>Resell, redistribute, or sublicense your account or API access</li>
              <li>Attempt to circumvent rate limits, usage caps, or security measures</li>
              <li>Transmit malware, viruses, or any harmful code through the Service</li>
              <li>Use the Service to harass, threaten, or harm others</li>
            </ul>
          </Section>

          <Section title="6. User Responsibility & Consent">
            <p>
              <strong className="text-white/90">You are solely responsible</strong> for obtaining consent from all participants before recording or transcribing any conversation. Laws regarding recording consent vary by jurisdiction (one-party vs. all-party consent). It is your obligation to understand and comply with all applicable local, state, and federal laws.
            </p>
            <p className="mt-2">Voxclar does not monitor or verify whether you have obtained proper consent and assumes no liability for your failure to do so.</p>
          </Section>

          <Section title="7. Intellectual Property">
            <p>The Voxclar application, brand, logos, and all associated technology are the property of Voxclar. Your subscription or license grants you a limited, non-exclusive, non-transferable right to use the Service for personal or internal business purposes.</p>
            <p className="mt-2">You retain ownership of all content you create, upload, or generate through the Service (transcripts, summaries, profiles, etc.).</p>
          </Section>

          <Section title="8. API Usage">
            <p>Access to the Voxclar Cloud ASR API is subject to:</p>
            <ul className="list-disc pl-5 space-y-1 mt-2">
              <li>Rate limits as published in our API documentation</li>
              <li>Your available ASR minute balance</li>
              <li>Our API-specific terms, including prohibitions on competitive benchmarking without consent</li>
            </ul>
            <p className="mt-2">We reserve the right to suspend or revoke API access for abuse, excessive usage, or violation of these Terms.</p>
          </Section>

          <Section title="9. Disclaimer of Warranties">
            <p>
              THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
            </p>
            <p className="mt-2">We do not warrant that:</p>
            <ul className="list-disc pl-5 space-y-1 mt-2">
              <li>Transcriptions will be 100% accurate</li>
              <li>AI-generated answers will be correct, complete, or appropriate</li>
              <li>The Service will be uninterrupted, secure, or error-free</li>
            </ul>
          </Section>

          <Section title="10. Limitation of Liability">
            <p>
              TO THE MAXIMUM EXTENT PERMITTED BY LAW, VOXCLAR SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING BUT NOT LIMITED TO LOSS OF PROFITS, DATA, EMPLOYMENT OPPORTUNITIES, OR REPUTATION, ARISING OUT OF OR RELATED TO YOUR USE OF THE SERVICE.
            </p>
            <p className="mt-2">
              Our total liability for any claim arising from these Terms or the Service shall not exceed the amount you paid to Voxclar in the 12 months preceding the claim.
            </p>
          </Section>

          <Section title="11. Indemnification">
            <p>You agree to indemnify and hold harmless Voxclar and its officers, employees, and agents from any claims, damages, losses, or expenses (including legal fees) arising from your use of the Service, your violation of these Terms, or your violation of any third-party rights (including recording consent laws).</p>
          </Section>

          <Section title="12. Termination">
            <p>We may suspend or terminate your account at any time for violation of these Terms, with or without notice. Upon termination, your right to use the Service ceases immediately. Sections regarding liability, indemnification, and intellectual property survive termination.</p>
          </Section>

          <Section title="13. Changes to Terms">
            <p>We may update these Terms from time to time. Material changes will be communicated via email or in-app notification. Continued use of the Service after changes constitutes acceptance of the updated Terms.</p>
          </Section>

          <Section title="14. Governing Law">
            <p>These Terms are governed by and construed in accordance with the laws of the United States. Any disputes shall be resolved through binding arbitration in accordance with the rules of the American Arbitration Association.</p>
          </Section>

          <Section title="15. Contact">
            <p>For questions about these Terms, contact us at:</p>
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

function Gold({ children }: { children: React.ReactNode }) {
  return <span className="text-imeet-gold">{children}</span>
}
