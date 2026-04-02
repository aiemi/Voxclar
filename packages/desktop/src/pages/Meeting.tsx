import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useEngine } from '@/hooks/useEngine'
import { useMeetingStore } from '@/stores/meetingStore'
import type { MeetingType } from '@/types'
import { Play, Square, Clock, MonitorUp, Upload, File, X, Loader2 } from 'lucide-react'
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

  if (isRecording) {
    // 录制中 — 简洁的控制面板，全部内容在字幕窗口
    return (
      <div className="h-full flex items-center justify-center">
        <div className="bg-imeet-panel rounded-[10px] p-8 border border-imeet-border w-96 text-center">
          <h3 className="font-semibold text-imeet-gold mb-1 text-lg">{title || 'Meeting'}</h3>
          <p className="text-xs text-imeet-text-muted mb-6 capitalize">{meetingType.replace('_', ' ')}</p>

          {/* Timer */}
          <div className="flex items-center justify-center gap-3 mb-8">
            <Clock size={20} className="text-imeet-gold" />
            <span className="font-mono text-3xl text-imeet-gold">{formatTime(elapsedSeconds)}</span>
            <div className="flex items-center gap-1.5">
              <div className="w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse" />
              <span className="text-xs text-red-400 font-medium">LIVE</span>
            </div>
          </div>

          {/* Controls */}
          <div className="flex gap-3">
            <button
              onClick={handleStop}
              className="flex-1 py-3 rounded-lg border-2 border-red-500/50 text-red-400 font-semibold flex items-center justify-center gap-2 hover:bg-red-500/10 transition-colors"
            >
              <Square size={16} />
              End Meeting
            </button>
            <button
              onClick={toggleCaption}
              className={`px-4 py-3 rounded-lg border-2 transition-all ${
                captionVisible
                  ? 'border-imeet-gold text-imeet-gold bg-imeet-gold/10'
                  : 'border-imeet-border text-imeet-text-muted hover:border-imeet-gold'
              }`}
              title="Toggle Caption Window"
            >
              <MonitorUp size={18} />
            </button>
          </div>

          <p className="text-[11px] text-imeet-text-muted mt-4">
            Captions and AI answers appear in the floating overlay
          </p>
        </div>
      </div>
    )
  }

  // 未录制 — 新会议设置
  return (
    <div className="h-full flex items-center justify-center">
      <div className="bg-imeet-panel rounded-[10px] p-6 border border-imeet-border w-[480px] space-y-4">
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
  )
}
