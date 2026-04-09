import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { loadLifetimeConfig as loadLtConfigFromStorage, saveLifetimeConfigStorage } from '@/services/storage'
import { Globe, Volume2, Key, Cpu, Eye, EyeOff, CheckCircle, AlertCircle } from 'lucide-react'
import CustomSelect from '@/components/CustomSelect'
import SupportChat from '@/components/SupportChat'

const electronAPI = (window as unknown as { electronAPI?: {
  platform: string
} }).electronAPI

interface LifetimeConfig {
  openai_api_key: string
  deepgram_api_key: string
  ai_model: string
  asr_mode: string
}

function loadLifetimeConfigLocal(): LifetimeConfig {
  try {
    const data = loadLtConfigFromStorage()
    if (data) return { openai_api_key: '', deepgram_api_key: '', ai_model: 'auto', asr_mode: 'local', ...data }
  } catch {}
  return { openai_api_key: '', deepgram_api_key: '', ai_model: 'auto', asr_mode: 'local' }
}

function saveLifetimeConfig(config: LifetimeConfig) {
  saveLifetimeConfigStorage(config)
}

export default function Settings() {
  const { t, i18n } = useTranslation()

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

  return (
    <div className="max-w-2xl space-y-6">
      <h2 className="text-2xl font-bold text-imeet-gold">{t('settings.title')}</h2>

      {/* API Keys */}
      <div className="bg-imeet-panel rounded-[20px_20px_4px_20px] p-6 border-2 border-purple-500/30">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-9 h-9 rounded-lg bg-purple-500/10 flex items-center justify-center">
            <Key size={18} className="text-purple-400" />
          </div>
          <div>
            <h3 className="font-semibold text-purple-400">API Keys</h3>
            <p className="text-xs text-imeet-text-muted">Your keys are stored locally. Never sent to our servers.</p>
          </div>
        </div>

        <div className="space-y-4">
          {/* OpenAI */}
          <div>
            <label className="text-xs text-imeet-text-muted uppercase tracking-wider mb-1.5 block">
              OpenAI API Key <span className="text-red-400">*</span>
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
            <p className="text-[11px] text-imeet-text-muted mt-1">Required for question detection and AI answers. Get yours at platform.openai.com</p>
          </div>

          {/* Deepgram */}
          <div>
            <label className="text-xs text-imeet-text-muted uppercase tracking-wider mb-1.5 block">
              Deepgram API Key <span className="text-imeet-text-muted">(optional)</span>
            </label>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <input
                  type={showKeys.deepgram ? 'text' : 'password'}
                  value={ltConfig.deepgram_api_key}
                  onChange={(e) => updateLtField('deepgram_api_key', e.target.value)}
                  placeholder="dg-..."
                  className="input-field w-full pr-10"
                />
                <button onClick={() => toggleShowKey('deepgram')} className="absolute right-3 top-1/2 -translate-y-1/2 text-imeet-text-muted hover:text-white">
                  {showKeys.deepgram ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>
            <p className="text-[11px] text-imeet-text-muted mt-1">For cloud ASR mode (Deepgram direct). Leave empty to use free local ASR.</p>
          </div>

          {/* Save + Status */}
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleSaveKeys}
              className="px-5 py-2.5 bg-purple-500 text-white rounded-lg text-sm font-semibold hover:bg-purple-400 active:scale-[0.98] transition-all"
            >
              Save
            </button>
            {saved && (
              <span className="flex items-center gap-1.5 text-green-400 text-sm">
                <CheckCircle size={14} /> Saved
              </span>
            )}
            {!ltConfig.openai_api_key && (
              <span className="flex items-center gap-1.5 text-amber-400 text-xs">
                <AlertCircle size={12} /> OpenAI key required for AI features
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
              onClick={() => updateLtField('asr_mode', 'deepgram')}
              className={`p-4 rounded-lg text-left transition-all ${
                ltConfig.asr_mode === 'deepgram'
                  ? 'bg-purple-500/10 border-2 border-purple-500'
                  : 'bg-white/5 border-2 border-transparent hover:border-imeet-border'
              }`}
            >
              <span className="block text-sm font-semibold mb-1">Cloud (Deepgram)</span>
              <span className="block text-[11px] text-imeet-text-muted leading-relaxed">Your Deepgram key, best accuracy</span>
              <span className="block text-[11px] text-imeet-gold mt-1.5 font-medium">Requires Deepgram API key</span>
            </button>
          </div>
          {ltConfig.asr_mode === 'deepgram' && !ltConfig.deepgram_api_key && (
            <p className="text-[11px] text-amber-400 mt-2">Add your Deepgram API key above to use cloud ASR.</p>
          )}
        </div>
      </div>

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
            <p className="text-xs text-imeet-text-muted">{t('settings.caption_lang_desc_lt')}</p>
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
