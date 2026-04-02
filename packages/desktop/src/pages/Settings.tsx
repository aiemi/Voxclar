import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Globe, Volume2 } from 'lucide-react'
import CustomSelect from '@/components/CustomSelect'

const electronAPI = (window as unknown as { electronAPI?: {
  platform: string
} }).electronAPI

export default function Settings() {
  const { t, i18n } = useTranslation()
  const [audioDevice, setAudioDevice] = useState('system')
  const [language, setLanguage] = useState(i18n.language)
  const [captionLang, setCaptionLang] = useState('multi')

  const handleLanguageChange = (lang: string) => {
    setLanguage(lang)
    i18n.changeLanguage(lang)
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h2 className="text-2xl font-bold text-imeet-gold">{t('settings.title')}</h2>

      {/* Audio Source */}
      <div className="bg-imeet-panel rounded-[20px_20px_4px_20px] p-6 border border-imeet-border">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-lg bg-imeet-gold/10 flex items-center justify-center">
            <Volume2 size={18} className="text-imeet-gold" />
          </div>
          <div>
            <h3 className="font-semibold">{t('settings.audio_device')}</h3>
            <p className="text-xs text-imeet-text-muted">System audio capture for transcription</p>
          </div>
        </div>
        <CustomSelect
          value={audioDevice}
          onChange={setAudioDevice}
          options={[
            { value: 'system', label: 'System Audio (ScreenCaptureKit)' },
            { value: 'mic', label: 'Microphone Only' },
          ]}
        />
        <p className="text-xs text-imeet-text-muted mt-2">
          {electronAPI?.platform === 'darwin'
            ? 'macOS: Uses ScreenCaptureKit to capture system audio (requires Screen Recording permission)'
            : 'Windows: Uses WASAPI loopback to capture system audio'}
        </p>
      </div>

      {/* Caption Language */}
      <div className="bg-imeet-panel rounded-[20px_20px_4px_20px] p-6 border border-imeet-border">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-lg bg-imeet-gold/10 flex items-center justify-center">
            <Globe size={18} className="text-imeet-gold" />
          </div>
          <div>
            <h3 className="font-semibold">Caption Language</h3>
            <p className="text-xs text-imeet-text-muted">Language for speech recognition (Deepgram)</p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {[
            { value: 'en', label: 'English' },
            { value: 'zh', label: '中文' },
            { value: 'ja', label: '日本語' },
            { value: 'multi', label: 'Auto-detect' },
          ].map((lang) => (
            <button
              key={lang.value}
              onClick={() => setCaptionLang(lang.value)}
              className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                captionLang === lang.value
                  ? 'bg-imeet-gold/15 text-imeet-gold border-2 border-imeet-gold'
                  : 'bg-white/5 text-imeet-text-secondary border-2 border-transparent hover:border-imeet-border'
              }`}
            >
              {lang.label}
            </button>
          ))}
        </div>
      </div>

      {/* App Language */}
      <div className="bg-imeet-panel rounded-[20px_20px_4px_20px] p-6 border border-imeet-border">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-lg bg-imeet-gold/10 flex items-center justify-center">
            <Globe size={18} className="text-imeet-gold" />
          </div>
          <div>
            <h3 className="font-semibold">{t('settings.language')}</h3>
            <p className="text-xs text-imeet-text-muted">Interface language</p>
          </div>
        </div>
        <div className="flex gap-2">
          {[
            { value: 'en', label: 'English' },
            { value: 'zh', label: '中文' },
          ].map((lang) => (
            <button
              key={lang.value}
              onClick={() => handleLanguageChange(lang.value)}
              className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-all flex-1 ${
                language === lang.value
                  ? 'bg-imeet-gold/15 text-imeet-gold border-2 border-imeet-gold'
                  : 'bg-white/5 text-imeet-text-secondary border-2 border-transparent hover:border-imeet-border'
              }`}
            >
              {lang.label}
            </button>
          ))}
        </div>
      </div>

    </div>
  )
}
