import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { api } from '@/services/api'
import { Globe, Volume2, Eye, EyeOff, CheckCircle, Copy, RefreshCw, Code } from 'lucide-react'
import CustomSelect from '@/components/CustomSelect'
import SupportChat from '@/components/SupportChat'

const electronAPI = (window as unknown as { electronAPI?: {
  platform: string
} }).electronAPI

function ApiKeyCard() {
  const { t } = useTranslation()
  const [apiKey, setApiKey] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [showKey, setShowKey] = useState(false)

  useEffect(() => {
    api.getApiKey().then((res) => setApiKey(res.api_key)).catch(() => {})
  }, [])

  const handleGenerate = async () => {
    setLoading(true)
    try {
      const res = await api.generateApiKey()
      setApiKey(res.api_key)
      setShowKey(true)
    } catch (err) {
      console.error('Failed to generate API key:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = () => {
    if (apiKey) {
      navigator.clipboard.writeText(apiKey)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="bg-imeet-panel rounded-[20px_20px_4px_20px] p-6 border-2 border-purple-500/30">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-9 h-9 rounded-lg bg-purple-500/10 flex items-center justify-center">
          <Code size={18} className="text-purple-400" />
        </div>
        <div>
          <h3 className="font-semibold text-purple-400">{t('settings.api_key_title')}</h3>
          <p className="text-xs text-imeet-text-muted">{t('settings.api_key_desc')}</p>
        </div>
      </div>

      {apiKey ? (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-black/30 border border-purple-500/20 rounded-lg px-4 py-3 font-mono text-sm">
              {showKey ? apiKey : '•'.repeat(32)}
            </div>
            <button
              onClick={() => setShowKey(!showKey)}
              className="p-3 rounded-lg bg-white/5 text-imeet-text-muted hover:text-white transition-colors"
            >
              {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
            <button
              onClick={handleCopy}
              className={`p-3 rounded-lg transition-colors ${
                copied ? 'bg-green-500/20 text-green-400' : 'bg-white/5 text-imeet-text-muted hover:text-white'
              }`}
            >
              {copied ? <CheckCircle size={14} /> : <Copy size={14} />}
            </button>
          </div>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="flex items-center gap-2 text-xs text-imeet-text-muted hover:text-purple-400 transition-colors"
          >
            <RefreshCw size={12} /> {t('settings.regenerate')}
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-imeet-text-muted">{t('settings.generate_hint')}</p>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="px-5 py-2.5 bg-purple-500 text-white rounded-lg text-sm font-semibold hover:bg-purple-400 active:scale-[0.98] transition-all disabled:opacity-50"
          >
            {loading ? t('settings.generating') : t('settings.generate_key_free')}
          </button>
        </div>
      )}

      <p className="text-[11px] text-imeet-text-muted mt-3">
        API Endpoint: <code className="text-purple-400">https://api.voxclar.com/v1/listen</code>
        {' · '}Docs: <code className="text-purple-400">voxclar.com/docs</code>
      </p>
    </div>
  )
}

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

      <ApiKeyCard />

      {/* Audio Source */}
      <div className="bg-imeet-panel rounded-[20px_20px_4px_20px] p-6 border border-imeet-border">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-lg bg-imeet-gold/10 flex items-center justify-center">
            <Volume2 size={18} className="text-imeet-gold" />
          </div>
          <div>
            <h3 className="font-semibold">{t('settings.audio_device')}</h3>
            <p className="text-xs text-imeet-text-muted">{t('settings.audio_desc')}</p>
          </div>
        </div>
        <CustomSelect
          value={audioDevice}
          onChange={setAudioDevice}
          options={[
            { value: 'system', label: t('settings.audio_system') },
            { value: 'mic', label: t('settings.audio_mic') },
          ]}
        />
        <p className="text-xs text-imeet-text-muted mt-2">
          {electronAPI?.platform === 'darwin' ? t('settings.audio_mac') : t('settings.audio_win')}
        </p>
      </div>

      {/* Caption Language */}
      <div className="bg-imeet-panel rounded-[20px_20px_4px_20px] p-6 border border-imeet-border">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-lg bg-imeet-gold/10 flex items-center justify-center">
            <Globe size={18} className="text-imeet-gold" />
          </div>
          <div>
            <h3 className="font-semibold">{t('settings.caption_lang')}</h3>
            <p className="text-xs text-imeet-text-muted">
              {t('settings.caption_lang_desc')}
            </p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {[
            { value: 'en', label: t('settings.lang_en') },
            { value: 'zh', label: t('settings.lang_zh') },
            { value: 'ja', label: t('settings.lang_ja') },
            { value: 'multi', label: t('settings.lang_auto') },
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
            <p className="text-xs text-imeet-text-muted">{t('settings.interface_lang')}</p>
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

      {/* Support Chat */}
      <SupportChat />

    </div>
  )
}
