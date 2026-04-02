import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useEngine } from '@/hooks/useEngine'
import { useMeetingStore } from '@/stores/meetingStore'
import type { MeetingType } from '@/types'
import { Play, Square, Clock, ThumbsUp, ThumbsDown, Copy, MonitorUp, Subtitles, MessageSquare, Upload, File, X, Loader2 } from 'lucide-react'
import CustomSelect from '@/components/CustomSelect'

function formatAnswer(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<span style="color:#FFD700;font-weight:600">$1</span>')
    .replace(/^#{1,3}\s+(.+)$/gm, '<div style="color:#FFD700;font-weight:600;margin-top:6px">$1</div>')
    .replace(/^[-•]\s+/gm, '  · ')
    .replace(/`([^`]+)`/g, '<code style="background:rgba(255,215,0,0.1);color:#FFD700;padding:1px 4px;border-radius:3px;font-size:12px">$1</code>')
    .replace(/\n/g, '<br>')
}

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
  const { transcripts, answers, isRecording, elapsedSeconds, setElapsed } = useMeetingStore()
  const store = useMeetingStore()

  const [title, setTitle] = useState('')
  const [meetingType, setMeetingType] = useState<MeetingType>('general')
  const [language, setLanguage] = useState('multi')
  const [prepNotes, setPrepNotes] = useState('')
  const [prepFiles, setPrepFiles] = useState<{name: string; summary: string}[]>([])
  const [summarizing, setSummarizing] = useState(false)
  const prepFileRef = useRef<HTMLInputElement>(null)
  const transcriptEndRef = useRef<HTMLDivElement>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined)

  /** 把文件转 base64 */
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
            if (data.type === 'document_summarized') {
              resolve(data.summary)
            }
          }
          setTimeout(() => resolve('(summarization timeout)'), 25000)
        })
        ws.close()
        setPrepFiles((prev) => [...prev, { name: file.name, summary }])
      } catch {
        setPrepFiles((prev) => [...prev, { name: file.name, summary: '(upload failed)' }])
      }
    }

    setSummarizing(false)
    if (prepFileRef.current) prepFileRef.current.value = ''
  }

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcripts])

  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => setElapsed(elapsedSeconds + 1), 1000)
    }
    return () => clearInterval(timerRef.current)
  }, [isRecording, elapsedSeconds, setElapsed])

  const [captionVisible, setCaptionVisible] = useState(false)

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
    // 合并手写 prep notes + 文件摘要
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
    // 跳转到会议记录页
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

  return (
    <div className="h-full flex gap-5">
      {/* Left Panel */}
      <div className="w-72 flex-shrink-0 flex flex-col gap-4">
        {!isRecording ? (
          <div className="bg-imeet-panel rounded-[10px] p-5 border border-imeet-border space-y-4">
            <h2 className="text-lg font-bold text-imeet-gold">{t('meeting.new')}</h2>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t('meeting.topic')}
              className="input-field w-full"
            />
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
            <textarea
              value={prepNotes}
              onChange={(e) => setPrepNotes(e.target.value)}
              placeholder={t('meeting.prep_notes')}
              className="input-field w-full h-20 resize-none text-sm"
            />

            {/* 准备资料文件上传 */}
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
              className="w-full py-2 rounded-lg border border-dashed border-imeet-border hover:border-imeet-gold/50 text-xs text-imeet-text-muted hover:text-imeet-gold transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              {summarizing ? <><Loader2 size={12} className="animate-spin" /> Analyzing...</> : <><Upload size={12} /> Upload prep files (PDF/Word/PPT)</>}
            </button>
            <button
              onClick={handleStart}
              className="w-full bg-imeet-gold text-black font-bold py-3 rounded-lg flex items-center justify-center gap-2 hover:bg-imeet-gold-hover active:scale-[0.98] transition-all"
            >
              <Play size={18} />
              {t('meeting.start')}
            </button>
          </div>
        ) : (
          <div className="bg-imeet-panel rounded-[10px] p-5 border border-imeet-border">
            <h3 className="font-semibold text-imeet-gold mb-3 truncate">{title || 'Meeting'}</h3>

            {/* Timer */}
            <div className="flex items-center gap-3 mb-4">
              <div className="flex items-center gap-2">
                <Clock size={16} className="text-imeet-gold" />
                <span className="font-mono text-xl text-imeet-gold">{formatTime(elapsedSeconds)}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                <span className="text-xs text-red-400">LIVE</span>
              </div>
            </div>

            {/* Controls */}
            <div className="flex gap-2">
              <button
                onClick={handleStop}
                className="flex-1 py-2.5 rounded-lg border-2 border-red-500/50 text-red-400 font-medium text-sm flex items-center justify-center gap-2 hover:bg-red-500/10 transition-colors"
              >
                <Square size={14} />
                {t('meeting.stop')}
              </button>
              <button
                onClick={toggleCaption}
                className={`px-3 py-2.5 rounded-lg border-2 transition-all ${
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
        )}
      </div>

      {/* Right Panel */}
      <div className="flex-1 flex flex-col gap-4 min-w-0">
        {/* Transcript */}
        <div className="bg-imeet-panel rounded-[10px] p-5 border border-imeet-border flex-1 overflow-y-auto">
          <h3 className="font-semibold text-imeet-gold mb-4 flex items-center gap-2 text-sm">
            <Subtitles size={16} />
            {t('meeting.transcript')}
          </h3>
          <div className="space-y-3">
            {transcripts.length === 0 && (
              <p className="text-imeet-text-muted text-sm">
                {isRecording ? (
                  <span className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                    Listening...
                  </span>
                ) : t('meeting.no_meetings')}
              </p>
            )}
            {transcripts.map((tr) => (
              <div key={tr.id}>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium uppercase tracking-wider inline-block mb-1 ${
                  tr.speaker === 'other'
                    ? 'bg-amber-500/15 text-amber-400'
                    : 'bg-blue-500/15 text-blue-400'
                }`}>
                  {tr.speaker === 'other' ? 'Them' : 'You'}
                </span>
                <p className="text-sm text-white/85 leading-relaxed">{tr.text}</p>
              </div>
            ))}
            <div ref={transcriptEndRef} />
          </div>
        </div>

        {/* AI Answers */}
        {answers.length > 0 && (
          <div className="bg-imeet-panel rounded-[10px] p-5 border border-imeet-border max-h-72 overflow-y-auto">
            <h3 className="font-semibold text-imeet-gold mb-3 flex items-center gap-2 text-sm">
              <MessageSquare size={16} />
              {t('meeting.ai_answers')}
            </h3>
            <div className="space-y-3">
              {answers.map((a) => (
                <div key={a.id} className="bg-white/[0.03] rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-[10px] px-2 py-0.5 rounded font-medium ${
                      a.question_type === 'technical' ? 'bg-blue-500/15 text-blue-400' :
                      a.question_type === 'behavioral' ? 'bg-purple-500/15 text-purple-400' :
                      'bg-imeet-gold/15 text-imeet-gold'
                    }`}>{a.question_type}</span>
                    <p className="text-xs text-imeet-text-muted truncate flex-1">{a.question_text}</p>
                  </div>
                  <div className="text-sm leading-relaxed" dangerouslySetInnerHTML={{ __html: formatAnswer(a.answer_text || '...') }} />
                  <div className="flex gap-3 mt-3 pt-2 border-t border-white/5">
                    <button className="text-imeet-text-muted hover:text-green-400 transition-colors"><ThumbsUp size={13} /></button>
                    <button className="text-imeet-text-muted hover:text-red-400 transition-colors"><ThumbsDown size={13} /></button>
                    <button
                      className="text-imeet-text-muted hover:text-imeet-gold transition-colors"
                      onClick={() => navigator.clipboard.writeText(a.answer_text)}
                    >
                      <Copy size={13} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
