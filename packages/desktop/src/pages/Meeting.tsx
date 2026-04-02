import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useEngine } from '@/hooks/useEngine'
import { useMeetingStore } from '@/stores/meetingStore'
import type { MeetingType } from '@/types'
import { Play, Square, Clock, MonitorUp, Upload, File, X, Loader2, Shield, Zap, Brain, Mic, MessageSquare } from 'lucide-react'
import CustomSelect from '@/components/CustomSelect'

const electronAPI = (window as unknown as { electronAPI?: {
  caption: { show: () => void; hide: () => void; toggle: () => Promise<boolean>; update: (data: unknown) => void }
} }).electronAPI

const MEETING_TYPES: { value: MeetingType; labelKey: string }[] = [
  { value: 'general', labelKey: 'meeting.types.general' },
  { value: 'phone_screen', labelKey: 'meeting.types.phone_screen' },
  { value: 'technical', labelKey: 'meeting.types.technical' },
  { value: 'coffee_chat', labelKey: 'meeting.types.coffee_chat' },
  { value: 'project_kickoff', labelKey: 'meeting.types.project_kickoff' },
  { value: 'weekly_standup', labelKey: 'meeting.types.weekly_standup' },
]

export default function Meeting() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { startMeeting, stopMeeting } = useEngine()
  const { isRecording, elapsedSeconds, setElapsed } = useMeetingStore()
  const store = useMeetingStore()

  const [title, setTitle] = useState('')
  const [meetingType, setMeetingType] = useState<MeetingType>('general')
  const [language, setLanguage] = useState('multi')
  const [prepNotes, setPrepNotes] = useState('')
  const [prepFiles, setPrepFiles] = useState<{name: string; summary: string}[]>([])
  const [summarizing, setSummarizing] = useState(false)
  const prepFileRef = useRef<HTMLInputElement>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined)

  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => setElapsed(elapsedSeconds + 1), 1000)
    }
    return () => clearInterval(timerRef.current)
  }, [isRecording, elapsedSeconds, setElapsed])

  const [captionVisible, setCaptionVisible] = useState(false)

  function fileToBase64(file: File): Promise<string> {
    return new Promise((resolve) => {
      const reader = new FileReader()
      reader.onload = () => resolve((reader.result as string).split(',')[1] || '')
      reader.onerror = () => resolve('')
      reader.readAsDataURL(file)
    })
  }

  const handlePrepFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files) return
    setSummarizing(true)

    for (const file of Array.from(files)) {
      const base64 = await fileToBase64(file)
      try {
        const ws = new WebSocket('ws://localhost:9876')
        const summary = await new Promise<string>((resolve) => {
          ws.onopen = () => {
            ws.send(JSON.stringify({
              type: 'summarize_document',
              file_data: base64,
              filename: file.name,
              doc_type: 'prep_notes',
              doc_id: file.name,
            }))
          }
          ws.onmessage = (event) => {
            const data = JSON.parse(event.data)
            if (data.type === 'document_summarized') resolve(data.summary)
          }
          setTimeout(() => resolve('(timeout)'), 25000)
        })
        ws.close()
        setPrepFiles((prev) => [...prev, { name: file.name, summary }])
      } catch {
        setPrepFiles((prev) => [...prev, { name: file.name, summary: '(failed)' }])
      }
    }

    setSummarizing(false)
    if (prepFileRef.current) prepFileRef.current.value = ''
  }

  const handleStart = () => {
    store.startMeeting({
      id: crypto.randomUUID(),
      title,
      meeting_type: meetingType,
      language,
      status: 'active',
      duration_seconds: 0,
      points_consumed: 0,
      created_at: new Date().toISOString(),
    })
    const allPrepNotes = [
      prepNotes,
      ...prepFiles.map((f) => `[${f.name}]\n${f.summary}`),
    ].filter(Boolean).join('\n\n')
    startMeeting({ title, meeting_type: meetingType, language, audio_source: 'system', prep_notes: allPrepNotes })
    electronAPI?.caption.show()
    setCaptionVisible(true)
  }

  const handleStop = () => {
    stopMeeting()
    store.stopMeeting()
    clearInterval(timerRef.current)
    electronAPI?.caption.hide()
    setCaptionVisible(false)
    setTimeout(() => navigate('/records'), 500)
  }

  const toggleCaption = async () => {
    const visible = await electronAPI?.caption.toggle()
    setCaptionVisible(visible ?? false)
  }

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`
  }

  const { answers } = useMeetingStore()

  if (isRecording) {
    return (
      <div className="h-full flex flex-col gap-5">
        {/* Top: Control Card */}
        <div className="bg-imeet-panel rounded-[10px] p-6 border border-imeet-border">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-imeet-gold text-lg">{title || 'Meeting'}</h3>
              <p className="text-xs text-imeet-text-muted capitalize">{meetingType.replace('_', ' ')}</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Clock size={18} className="text-imeet-gold" />
                <span className="font-mono text-2xl text-imeet-gold">{formatTime(elapsedSeconds)}</span>
              </div>
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-500/10">
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                <span className="text-xs text-red-400 font-medium">LIVE</span>
              </div>
            </div>
          </div>
          <div className="flex gap-3 mt-4">
            <button
              onClick={handleStop}
              className="flex-1 py-2.5 rounded-lg border-2 border-red-500/50 text-red-400 font-semibold flex items-center justify-center gap-2 hover:bg-red-500/10 transition-colors"
            >
              <Square size={14} /> End Meeting
            </button>
            <button
              onClick={toggleCaption}
              className={`px-4 py-2.5 rounded-lg border-2 transition-all ${
                captionVisible
                  ? 'border-imeet-gold text-imeet-gold bg-imeet-gold/10'
                  : 'border-imeet-border text-imeet-text-muted hover:border-imeet-gold'
              }`}
              title="Toggle Caption Window"
            >
              <MonitorUp size={16} />
            </button>
          </div>
        </div>

        {/* Live Status Cards */}
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-imeet-panel rounded-[10px] p-4 border border-imeet-border text-center">
            <Mic size={20} className="text-green-400 mx-auto mb-2" />
            <p className="text-2xl font-bold">{store.transcripts.filter(t => t.speaker === 'other').length || 0}</p>
            <p className="text-xs text-imeet-text-muted">Segments Heard</p>
          </div>
          <div className="bg-imeet-panel rounded-[10px] p-4 border border-imeet-border text-center">
            <Brain size={20} className="text-imeet-gold mx-auto mb-2" />
            <p className="text-2xl font-bold">{answers.length}</p>
            <p className="text-xs text-imeet-text-muted">AI Answers</p>
          </div>
          <div className="bg-imeet-panel rounded-[10px] p-4 border border-imeet-border text-center">
            <Shield size={20} className="text-blue-400 mx-auto mb-2" />
            <p className="text-sm font-medium text-blue-400 mt-1">Protected</p>
            <p className="text-xs text-imeet-text-muted">Screen Share Safe</p>
          </div>
        </div>

        {/* Recent AI Answer Preview */}
        <div className="bg-imeet-panel rounded-[10px] p-5 border border-imeet-border flex-1 overflow-y-auto">
          <h3 className="text-sm font-semibold text-imeet-gold mb-3 flex items-center gap-2">
            <MessageSquare size={14} /> Latest AI Answer
          </h3>
          {answers.length > 0 ? (
            <div className="text-sm text-white/80 leading-relaxed" dangerouslySetInnerHTML={{
              __html: formatAnswer(answers[answers.length - 1].answer_text || 'Generating...')
            }} />
          ) : (
            <p className="text-sm text-imeet-text-muted">
              AI answers will appear here and in the floating caption overlay when questions are detected.
            </p>
          )}
        </div>
      </div>
    )
  }

  // 未录制 — 新会议设置
  return (
    <div className="h-full flex gap-6 p-2">
      {/* Left: Setup Form */}
      <div className="flex-1">
        <div className="bg-imeet-panel rounded-[10px] p-6 border border-imeet-border space-y-4">
          <h2 className="text-lg font-bold text-imeet-gold">{t('meeting.new')}</h2>

        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={t('meeting.topic')}
          className="input-field w-full"
        />

        <div className="grid grid-cols-2 gap-3">
          <CustomSelect
            value={meetingType}
            onChange={(v) => setMeetingType(v as MeetingType)}
            options={MEETING_TYPES.map((mt) => ({ value: mt.value, label: t(mt.labelKey) }))}
          />
          <CustomSelect
            value={language}
            onChange={setLanguage}
            options={[
              { value: 'en', label: 'English' },
              { value: 'zh', label: '中文' },
              { value: 'ja', label: '日本語' },
              { value: 'multi', label: 'Auto-detect' },
            ]}
          />
        </div>

        <textarea
          value={prepNotes}
          onChange={(e) => setPrepNotes(e.target.value)}
          placeholder={t('meeting.prep_notes')}
          className="input-field w-full h-24 resize-none text-sm"
        />

        {/* Prep files */}
        <input ref={prepFileRef} type="file" accept=".pdf,.docx,.doc,.txt,.pptx,.ppt" multiple className="hidden" onChange={handlePrepFileUpload} />
        {prepFiles.length > 0 && (
          <div className="space-y-1.5">
            {prepFiles.map((f) => (
              <div key={f.name} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.03] border border-imeet-border text-xs">
                <File size={12} className="text-imeet-gold flex-shrink-0" />
                <span className="truncate flex-1">{f.name}</span>
                <button onClick={() => setPrepFiles(prepFiles.filter((x) => x.name !== f.name))} className="text-imeet-text-muted hover:text-red-400">
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        )}
        <button
          type="button"
          onClick={() => prepFileRef.current?.click()}
          disabled={summarizing}
          className="w-full py-2.5 rounded-lg border border-dashed border-imeet-border hover:border-imeet-gold/50 text-xs text-imeet-text-muted hover:text-imeet-gold transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
        >
          {summarizing ? <><Loader2 size={12} className="animate-spin" /> Analyzing...</> : <><Upload size={12} /> Upload prep files (PDF/Word/PPT)</>}
        </button>

        <button
          onClick={handleStart}
          className="w-full bg-imeet-gold text-black font-bold py-3.5 rounded-lg flex items-center justify-center gap-2 hover:bg-imeet-gold-hover active:scale-[0.98] transition-all text-lg"
        >
          <Play size={20} />
          {t('meeting.start')}
        </button>
      </div>
      </div>

      {/* Right: How it works */}
      <div className="w-80 flex-shrink-0 space-y-4">
        <div className="bg-imeet-panel rounded-[10px] p-5 border border-imeet-border">
          <h3 className="text-sm font-semibold text-imeet-gold mb-4">How Voxclar Works</h3>
          <div className="space-y-4">
            {[
              { icon: Zap, title: 'Real-time Captions', desc: 'Word-by-word transcription powered by Deepgram Nova-2' },
              { icon: Brain, title: 'Smart Detection', desc: 'AI detects questions and generates context-aware answers' },
              { icon: Shield, title: 'Screen Share Safe', desc: 'Invisible in Zoom, Teams, and Meet screen sharing' },
              { icon: Upload, title: 'Prep Material', desc: 'Upload resumes and notes — AI references them in answers' },
            ].map((item) => (
              <div key={item.title} className="flex gap-3">
                <div className="w-8 h-8 rounded-lg bg-imeet-gold/10 flex items-center justify-center flex-shrink-0">
                  <item.icon size={14} className="text-imeet-gold" />
                </div>
                <div>
                  <p className="text-sm font-medium">{item.title}</p>
                  <p className="text-xs text-imeet-text-muted leading-relaxed">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white/[0.02] rounded-[10px] p-4 border border-imeet-border">
          <p className="text-xs text-imeet-text-muted leading-relaxed">
            <span className="text-imeet-gold font-medium">Tip:</span> Upload your resume in Profile and prep notes here for the best AI-generated answers tailored to your experience.
          </p>
        </div>
      </div>
    </div>
  )
}
