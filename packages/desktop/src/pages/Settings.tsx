import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { api } from '@/services/api'
import { loadLifetimeConfig as loadLtConfigFromStorage, saveLifetimeConfigStorage } from '@/services/storage'
import { Globe, Volume2, Key, Cpu, Eye, EyeOff, CheckCircle, AlertCircle, Copy, RefreshCw, Code } from 'lucide-react'
import CustomSelect from '@/components/CustomSelect'
import SupportChat from '@/components/SupportChat'

const electronAPI = (window as unknown as { electronAPI?: {
  platform: string
} }).electronAPI

interface LifetimeConfig {
  claude_api_key: string
  openai_api_key: string
  deepseek_api_key: string
  ai_model: string
  asr_mode: string
}

function loadLifetimeConfigLocal(): LifetimeConfig {
  try {
    const data = loadLtConfigFromStorage()
    if (data) return { claude_api_key: '', openai_api_key: '', deepseek_api_key: '', ai_model: 'auto', asr_mode: 'local', ...data }
  } catch {}
  return { claude_api_key: '', openai_api_key: '', deepseek_api_key: '', ai_model: 'auto', asr_mode: 'local' }
}

function saveLifetimeConfig(config: LifetimeConfig) {
  saveLifetimeConfigStorage(config)
}

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
  const user = useAuthStore((s) => s.user)
  const isLifetime = user?.subscription_tier === 'lifetime'

  const [audioDevice, setAudioDevice] = useState('system')
  const [language, setLanguage] = useState(i18n.language)
  const [captionLang, setCaptionLang] = useState('multi')

  const [ltConfig, setLtConfig] = useState<LifetimeConfig>(loadLifetimeConfigLocal)
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({})
  const [saved, setSaved] = useState(false)

  const handleLanguageChange = (lang: string) => {
    setLanguage(lang)
    i18n.changeLanguage(lang)
  }

  const updateLtField = (field: keyof LifetimeConfig, value: string) => {
    setLtConfig((prev) => {
      const updated = { ...prev, [field]: value }
      saveLifetimeConfig(updated)
      return updated
    })
    setSaved(false)
  }

  const handleSaveKeys = () => {
    saveLifetimeConfig(ltConfig)
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  const toggleShowKey = (key: string) => {
    setShowKeys((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const hasAnyKey = ltConfig.claude_api_key || ltConfig.openai_api_key || ltConfig.deepseek_api_key

  return (
    <div className="max-w-2xl space-y-6">
      <h2 className="text-2xl font-bold text-imeet-gold">{t('settings.title')}</h2>

      {isLifetime && <ApiKeyCard />}

      {isLifetime && (
        <div className="bg-imeet-panel rounded-[20px_20px_4px_20px] p-6 border-2 border-purple-500/30">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-9 h-9 rounded-lg bg-purple-500/10 flex items-center justify-center">
              <Key size={18} className="text-purple-400" />
            </div>
            <div>
              <h3 className="font-semibold text-purple-400">{t('settings.ai_keys_title')}</h3>
              <p className="text-xs text-imeet-text-muted">{t('settings.ai_keys_desc')}</p>
            </div>
          </div>

          <div className="space-y-4">
            {/* Claude */}
            <div>
              <label className="text-xs text-imeet-text-muted uppercase tracking-wider mb-1.5 block">
                {t('settings.claude_label')}
              </label>
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <input
                    type={showKeys.claude ? 'text' : 'password'}
                    value={ltConfig.claude_api_key}
                    onChange={(e) => updateLtField('claude_api_key', e.target.value)}
                    placeholder="sk-ant-..."
                    className="input-field w-full pr-10"
                  />
                  <button onClick={() => toggleShowKey('claude')} className="absolute right-3 top-1/2 -translate-y-1/2 text-imeet-text-muted hover:text-white">
                    {showKeys.claude ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>
              <p className="text-[11px] text-imeet-text-muted mt-1">{t('settings.claude_hint')}</p>
            </div>

            {/* OpenAI */}
            <div>
              <label className="text-xs text-imeet-text-muted uppercase tracking-wider mb-1.5 block">
                {t('settings.openai_label')}
              </label>
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <input
                    type={showKeys.openai ? 'text' : 'password'}
                    value={ltConfig.openai_api_key}
                    onChange={(e) => updateLtField('openai_api_key', e.target.value)}
                    placeholder="sk-..."
                    className="input-field w-full pr-10"
                  />
                  <button onClick={() => toggleShowKey('openai')} className="absolute right-3 top-1/2 -translate-y-1/2 text-imeet-text-muted hover:text-white">
                    {showKeys.openai ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>
              <p className="text-[11px] text-imeet-text-muted mt-1">{t('settings.openai_hint')}</p>
            </div>

            {/* DeepSeek */}
            <div>
              <label className="text-xs text-imeet-text-muted uppercase tracking-wider mb-1.5 block">
                {t('settings.deepseek_label')}
              </label>
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <input
                    type={showKeys.deepseek ? 'text' : 'password'}
                    value={ltConfig.deepseek_api_key}
                    onChange={(e) => updateLtField('deepseek_api_key', e.target.value)}
                    placeholder="sk-..."
                    className="input-field w-full pr-10"
                  />
                  <button onClick={() => toggleShowKey('deepseek')} className="absolute right-3 top-1/2 -translate-y-1/2 text-imeet-text-muted hover:text-white">
                    {showKeys.deepseek ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>
              <p className="text-[11px] text-imeet-text-muted mt-1">{t('settings.deepseek_hint')}</p>
            </div>

            {/* Model Preference */}
            <div>
              <label className="text-xs text-imeet-text-muted uppercase tracking-wider mb-1.5 block">
                {t('settings.preferred_model')}
              </label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {[
                  { value: 'auto', label: t('settings.model_auto'), desc: t('settings.model_auto_label') },
                  { value: 'claude', label: 'Claude', desc: 'Anthropic' },
                  { value: 'openai', label: 'GPT-5.3', desc: 'OpenAI' },
                  { value: 'deepseek', label: 'DeepSeek', desc: 'R1' },
                ].map((m) => (
                  <button
                    key={m.value}
                    onClick={() => updateLtField('ai_model', m.value)}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-all text-center ${
                      ltConfig.ai_model === m.value
                        ? 'bg-purple-500/15 text-purple-400 border-2 border-purple-500'
                        : 'bg-white/5 text-imeet-text-secondary border-2 border-transparent hover:border-imeet-border'
                    }`}
                  >
                    <span className="block">{m.label}</span>
                    <span className="block text-[10px] text-imeet-text-muted">{m.desc}</span>
                  </button>
                ))}
              </div>
              <p className="text-[11px] text-imeet-text-muted mt-1">{t('settings.model_auto_desc')}</p>
            </div>

            {/* Save + Status */}
            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={handleSaveKeys}
                className="px-5 py-2.5 bg-purple-500 text-white rounded-lg text-sm font-semibold hover:bg-purple-400 active:scale-[0.98] transition-all"
              >
                {t('settings.save_keys')}
              </button>
              {saved && (
                <span className="flex items-center gap-1.5 text-green-400 text-sm">
                  <CheckCircle size={14} /> {t('settings.saved')}
                </span>
              )}
              {!hasAnyKey && (
                <span className="flex items-center gap-1.5 text-amber-400 text-xs">
                  <AlertCircle size={12} /> {t('settings.no_key_warning')}
                </span>
              )}
            </div>
          </div>

          {/* ASR Mode Selection */}
          <div className="mt-5 pt-4 border-t border-purple-500/20">
            <div className="flex items-center gap-2 mb-3">
              <Cpu size={14} className="text-purple-400" />
              <span className="text-sm font-medium text-purple-400">{t('settings.asr_mode_title')}</span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => updateLtField('asr_mode', 'local')}
                className={`p-4 rounded-lg text-left transition-all ${
                  ltConfig.asr_mode === 'local'
                    ? 'bg-purple-500/10 border-2 border-purple-500'
                    : 'bg-white/5 border-2 border-transparent hover:border-imeet-border'
                }`}
              >
                <span className="block text-sm font-semibold mb-1">{t('settings.local_asr')}</span>
                <span className="block text-[11px] text-imeet-text-muted leading-relaxed">{t('settings.local_asr_desc')}</span>
                <span className="block text-[11px] text-green-400 mt-1.5 font-medium">{t('settings.local_asr_free')}</span>
              </button>
              <button
                onClick={() => updateLtField('asr_mode', 'cloud')}
                className={`p-4 rounded-lg text-left transition-all ${
                  ltConfig.asr_mode === 'cloud'
                    ? 'bg-purple-500/10 border-2 border-purple-500'
                    : 'bg-white/5 border-2 border-transparent hover:border-imeet-border'
                }`}
              >
                <span className="block text-sm font-semibold mb-1">{t('settings.cloud_asr')}</span>
                <span className="block text-[11px] text-imeet-text-muted leading-relaxed">{t('settings.cloud_asr_desc')}</span>
                <span className="block text-[11px] text-imeet-gold mt-1.5 font-medium">{t('settings.cloud_asr_paid')}</span>
              </button>
            </div>
            {ltConfig.asr_mode === 'cloud' && (
              <p className="text-[11px] text-imeet-text-muted mt-2">{t('settings.cloud_asr_note')}</p>
            )}
          </div>
        </div>
      )}

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
              {isLifetime ? t('settings.caption_lang_desc_lt') : t('settings.caption_lang_desc')}
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
