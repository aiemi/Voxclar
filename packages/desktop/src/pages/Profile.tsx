import { useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Save, Plus, X, Upload, User, Briefcase, FileText, CheckCircle, File } from 'lucide-react'
import { saveProfileLocal } from '@/services/storage'
import { useAuthStore } from '@/stores/authStore'

interface ResumeItem {
  name: string
  content: string  // 提取的文本内容
  size: number
}

interface ProfileData {
  name: string
  headline: string
  summary: string
  skills: string[]
  resumes: ResumeItem[]
  context: string  // 预构建的 AI context（所有信息浓缩）
}

function loadProfileLocal(): ProfileData {
  try {
    const userId = useAuthStore.getState().user?.id || 'anonymous'
    const raw = localStorage.getItem(`voxclar_${userId}_profile`)
    if (raw) {
      const data = JSON.parse(raw)
      return { name: '', headline: '', summary: '', skills: [], resumes: [], context: '', ...data }
    }
  } catch {}
  return { name: '', headline: '', summary: '', skills: [], resumes: [], context: '' }
}

/** 从 profile 数据构建 AI context — 上传时就做好，回答时直接用 */
function buildContext(data: Omit<ProfileData, 'context'>): string {
  const parts: string[] = []
  if (data.name) parts.push(`Name: ${data.name}`)
  if (data.headline) parts.push(`Role: ${data.headline}`)
  if (data.summary) parts.push(`Summary: ${data.summary}`)
  if (data.skills.length) parts.push(`Skills: ${data.skills.join(', ')}`)
  if (data.resumes.length) {
    parts.push('--- Resume Content ---')
    data.resumes.forEach((r) => {
      parts.push(`[${r.name}]`)
      // 完整内容传给 AI — 由服务器端 summarize 压缩，绝不在这里截断
      parts.push(r.content)
    })
  }
  return parts.join('\n')
}

/** 把文件转成 base64 字符串 */
function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      resolve(result.split(',')[1] || '') // 去掉 data:xxx;base64, 前缀
    }
    reader.onerror = () => resolve('')
    reader.readAsDataURL(file)
  })
}

export default function Profile() {
  const { t } = useTranslation()
  const saved = loadProfileLocal()
  const [name, setName] = useState(saved.name)
  const [headline, setHeadline] = useState(saved.headline)
  const [summary, setSummary] = useState(saved.summary)
  const [skills, setSkills] = useState<string[]>(saved.skills)
  const [newSkill, setNewSkill] = useState('')
  const [resumes, setResumes] = useState<ResumeItem[]>(saved.resumes)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle')
  const [extracting, setExtracting] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const addSkill = () => {
    if (newSkill.trim() && !skills.includes(newSkill.trim())) {
      setSkills([...skills, newSkill.trim()])
      setNewSkill('')
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    setExtracting(true)

    // 1. 所有文件先解析成文本
    const parsed: { name: string; text: string; size: number }[] = []
    for (const file of Array.from(files)) {
      if (resumes.some((r) => r.name === file.name)) continue
      const base64 = await fileToBase64(file)
      const text = await parseFileOnEngine(base64, file.name)
      parsed.push({ name: file.name, text, size: file.size })
    }

    // 加入简历列表
    const newResumes = parsed.map((p) => ({ name: p.name, content: p.text, size: p.size }))
    const mergedResumes = [...resumes, ...newResumes]
    setResumes(mergedResumes)

    // 2. 合并所有简历（旧的 + 新的）→ 一次性让 AI 综合理解 → 提取 profile
    const allText = mergedResumes.map((r) => `=== ${r.name} ===\n${r.content}`).join('\n\n')
    if (allText) {
      const profile = await extractProfileFromText(allText)
      if (profile) {
        console.log('[Profile] Extracted:', profile)
        if (profile.name) setName(profile.name as string)
        if (profile.headline) setHeadline(profile.headline as string)
        if (profile.summary) setSummary(profile.summary as string)
        if (Array.isArray(profile.skills) && profile.skills.length > 0) setSkills(profile.skills as string[])
      }
    }

    if (fileInputRef.current) fileInputRef.current.value = ''
    setExtracting(false)
  }

  /** 让 engine 解析文件二进制 → 返回纯文本 */
  function parseFileOnEngine(base64: string, filename: string): Promise<string> {
    return new Promise((resolve) => {
      const ws = new WebSocket('ws://localhost:9876')
      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'parse_file', file_data: base64, filename }))
      }
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'file_parsed') {
            ws.close()
            resolve(data.text || '')
          }
        } catch {}
      }
      ws.onerror = () => resolve('')
      setTimeout(() => { try { ws.close() } catch {} resolve('') }, 15000)
    })
  }

  /** 把合并后的文本发给 engine，让 AI 综合理解后提取 profile */
  function extractProfileFromText(text: string): Promise<Record<string, unknown> | null> {
    return new Promise((resolve) => {
      const ws = new WebSocket('ws://localhost:9876')
      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'extract_profile', resume_text: text }))
      }
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'profile_extracted') {
            ws.close()
            resolve(data.profile || null)
          }
        } catch {}
      }
      ws.onerror = () => resolve(null)
      setTimeout(() => { try { ws.close() } catch {} resolve(null) }, 25000)
    })
  }

  const removeResume = async (fileName: string) => {
    const updated = resumes.filter((r) => r.name !== fileName)
    setResumes(updated)

    // 文件变了 → 重新让 AI 综合理解剩余文件 → 更新 profile
    if (updated.length > 0) {
      setExtracting(true)
      const allText = updated.map((r) => `=== ${r.name} ===\n${r.content}`).join('\n\n')
      const profile = await extractProfileFromText(allText)
      if (profile) {
        if (profile.name) setName(profile.name as string)
        if (profile.headline) setHeadline(profile.headline as string)
        if (profile.summary) setSummary(profile.summary as string)
        if (Array.isArray(profile.skills) && profile.skills.length > 0) setSkills(profile.skills as string[])
      }
      setExtracting(false)
    }
  }

  /** 用 AI 浓缩 profile context（Save 时调用） */
  function summarizeContext(profileData: Omit<ProfileData, 'context'>): Promise<string> {
    const raw = buildContext(profileData)
    // 如果内容短，直接用
    if (raw.length < 2000) return Promise.resolve(raw)

    // 长内容让 engine AI 浓缩
    return new Promise((resolve) => {
      const ws = new WebSocket('ws://localhost:9876')
      ws.onopen = () => {
        ws.send(JSON.stringify({
          type: 'summarize_document',
          text: raw,
          doc_type: 'profile',
          doc_id: 'profile_context',
        }))
      }
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'document_summarized') {
            ws.close()
            resolve(data.summary || raw)
          }
        } catch {}
      }
      ws.onerror = () => resolve(raw)
      setTimeout(() => { try { ws.close() } catch {} resolve(raw) }, 20000)
    })
  }

  const handleSave = async () => {
    setSaveStatus('saving')

    // AI 浓缩 context（理解后压缩，不截取）
    const context = await summarizeContext({ name, headline, summary, skills, resumes })

    const data: ProfileData = { name, headline, summary, skills, resumes, context }
    saveProfileLocal(data)

    // Also save condensed context to server DB
    try {
      const { api } = await import('@/services/api')
      await api.updateProfile({ full_name: name, headline, summary, skills })
      // Save condensed context for meeting AI
      await fetch(
        // @ts-ignore
        (import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1') + '/ai/context',
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
          },
          body: JSON.stringify({ condensed_context: context }),
        }
      )
    } catch (e) {
      console.warn('Server profile save failed:', e)
    }

    setSaveStatus('saved')
    setTimeout(() => setSaveStatus('idle'), 2000)
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h2 className="text-2xl font-bold text-imeet-gold">{t('profile.title')}</h2>

      {/* Basic Info */}
      <div className="bg-imeet-panel rounded-[20px_20px_4px_20px] p-6 border border-imeet-border space-y-4">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-lg bg-imeet-gold/10 flex items-center justify-center">
            <User size={18} className="text-imeet-gold" />
          </div>
          <h3 className="font-semibold">
            {t('profile.basic_info')}
            {extracting && <span className="text-xs text-imeet-gold ml-2 animate-pulse">{t('profile.extracting')}</span>}
          </h3>
        </div>
        <div>
          <label className="block text-xs text-imeet-text-muted mb-1.5 uppercase tracking-wider">{t('profile.name')}</label>
          <input value={name} onChange={(e) => setName(e.target.value)} className="input-field w-full" placeholder={t('profile.name_placeholder')} />
        </div>
        <div>
          <label className="block text-xs text-imeet-text-muted mb-1.5 uppercase tracking-wider">{t('profile.headline')}</label>
          <input value={headline} onChange={(e) => setHeadline(e.target.value)} className="input-field w-full" placeholder={t('profile.headline_placeholder')} />
        </div>
        <div>
          <label className="block text-xs text-imeet-text-muted mb-1.5 uppercase tracking-wider">{t('profile.summary')}</label>
          <textarea
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            className="input-field w-full h-28 resize-none"
            placeholder={t('profile.summary_placeholder')}
          />
        </div>
      </div>

      {/* Skills */}
      <div className="bg-imeet-panel rounded-[20px_20px_4px_20px] p-6 border border-imeet-border">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-lg bg-imeet-gold/10 flex items-center justify-center">
            <Briefcase size={18} className="text-imeet-gold" />
          </div>
          <div>
            <h3 className="font-semibold">{t('profile.skills')}</h3>
            <p className="text-xs text-imeet-text-muted">{t('profile.skills_hint')}</p>
          </div>
        </div>
        {skills.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {skills.map((skill) => (
              <span key={skill} className="bg-imeet-gold/10 text-imeet-gold text-sm px-3 py-1 rounded-full flex items-center gap-1.5 border border-imeet-gold/20">
                {skill}
                <button onClick={() => setSkills(skills.filter((s) => s !== skill))} className="hover:text-red-400 transition-colors">
                  <X size={12} />
                </button>
              </span>
            ))}
          </div>
        )}
        <div className="flex gap-2">
          <input
            value={newSkill}
            onChange={(e) => setNewSkill(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addSkill()}
            className="input-field flex-1"
            placeholder={t('profile.skill_placeholder')}
          />
          <button onClick={addSkill} className="px-4 py-2 rounded-lg border-2 border-imeet-gold/50 text-imeet-gold hover:bg-imeet-gold/10 transition-colors">
            <Plus size={16} />
          </button>
        </div>
      </div>

      {/* Resume Upload — 支持多个文件 */}
      <div className="bg-imeet-panel rounded-[20px_20px_4px_20px] p-6 border border-imeet-border">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-9 h-9 rounded-lg bg-imeet-gold/10 flex items-center justify-center">
            <FileText size={18} className="text-imeet-gold" />
          </div>
          <div>
            <h3 className="font-semibold">{t('profile.upload_resume')}</h3>
            <p className="text-xs text-imeet-text-muted">{t('profile.resume_hint')}</p>
          </div>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.doc,.txt,.pptx,.ppt"
          multiple
          className="hidden"
          onChange={handleFileUpload}
        />

        {/* 已上传的文件列表 */}
        {resumes.length > 0 && (
          <div className="space-y-2 mb-4">
            {resumes.map((r) => (
              <div key={r.name} className="flex items-center gap-3 p-3 rounded-lg bg-white/[0.03] border border-imeet-border">
                <File size={16} className="text-imeet-gold flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{r.name}</p>
                  <p className="text-xs text-imeet-text-muted">{(r.size / 1024).toFixed(0)} KB</p>
                </div>
                <button onClick={() => removeResume(r.name)} className="text-imeet-text-muted hover:text-red-400 transition-colors">
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        )}

        <button
          onClick={() => fileInputRef.current?.click()}
          className="w-full py-5 rounded-lg border-2 border-dashed border-imeet-border hover:border-imeet-gold/50 flex flex-col items-center gap-2 text-imeet-text-muted hover:text-imeet-gold transition-all"
        >
          <Upload size={22} />
          <span className="text-sm">{resumes.length > 0 ? t('profile.add_more') : t('profile.upload_click')}</span>
        </button>
      </div>

      {/* Save */}
      <button
        onClick={handleSave}
        className={`w-full font-bold py-3 rounded-lg flex items-center justify-center gap-2 active:scale-[0.98] transition-all ${
          saveStatus === 'saved'
            ? 'bg-green-500 text-white'
            : 'bg-imeet-gold text-black hover:bg-imeet-gold-hover'
        }`}
      >
        {saveStatus === 'saved' ? (
          <><CheckCircle size={18} /> {t('profile.saved')}</>
        ) : (
          <><Save size={18} /> {t('profile.save')}</>
        )}
      </button>
    </div>
  )
}
