import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import TextAlign from '@tiptap/extension-text-align'
import Highlight from '@tiptap/extension-highlight'
import { useMeetingStore, loadRecords } from '@/stores/meetingStore'
import { useAuthStore } from '@/stores/authStore'
import type { MeetingRecord } from '@/types'
import {
  Clock, MessageSquare, FileText, Lock, Copy, CheckCircle,
  FileDown, Bold, Italic, List, ListOrdered, AlignLeft, AlignCenter,
  Heading2, Highlighter, Undo, Redo, Eye, Pencil, Trash2,
} from 'lucide-react'

const electronAPI = (window as unknown as { electronAPI?: {
  export: { savePDF: (html: string, filename: string) => Promise<string | null> }
} }).electronAPI

function formatDuration(s: number) { return `${Math.floor(s / 60)}m ${s % 60}s` }
function formatDate(iso: string) { return new Date(iso).toLocaleString() }
function formatDateLong(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
}

function formatAnswer(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong style="color:#FFD700">$1</strong>')
    .replace(/^#{1,3}\s+(.+)$/gm, '<h3>$1</h3>')
    .replace(/^[-•]\s+(.+)$/gm, '<li>$1</li>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
}

/** 把 MeetingRecord 转成编辑器初始 HTML */
function recordToHtml(record: MeetingRecord, isPremium: boolean): string {
  const parts: string[] = []

  parts.push(`<h2>Transcript</h2>`)
  for (const t of record.transcripts) {
    const label = t.speaker === 'other' ? 'Interviewer' : 'Candidate'
    const color = t.speaker === 'other' ? '#B8960F' : '#3B82F6'
    parts.push(`<p><strong style="color:${color}">[${label}]</strong> ${t.text}</p>`)
  }

  if (record.answers.length > 0) {
    parts.push(`<h2>AI-Generated Answers</h2>`)
    for (const a of record.answers) {
      parts.push(`<blockquote><p><strong>Q (${a.question_type}):</strong> ${a.question_text}</p><p>${formatAnswer(a.answer_text)}</p></blockquote>`)
    }
  }

  if (isPremium && record.summary) {
    parts.push(`<h2>AI Meeting Summary</h2>`)
    parts.push(formatAnswer(record.summary))
  }

  return parts.join('')
}

/** 编辑器工具栏按钮 */
function ToolbarButton({ onClick, active, children, title }: {
  onClick: () => void; active?: boolean; children: React.ReactNode; title?: string
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`w-7 h-7 flex items-center justify-center rounded transition-colors ${
        active ? 'bg-imeet-gold/20 text-imeet-gold' : 'text-imeet-text-muted hover:bg-white/10 hover:text-white'
      }`}
    >
      {children}
    </button>
  )
}

export default function MeetingRecordPage() {
  const navigate = useNavigate()
  const { lastRecord } = useMeetingStore()
  const user = useAuthStore((s) => s.user)
  const [records, setRecords] = useState<MeetingRecord[]>(loadRecords)
  const [selectedId, setSelectedId] = useState<string | null>(lastRecord?.meeting.id || records[0]?.meeting.id || null)
  const [copied, setCopied] = useState(false)
  const [mode, setMode] = useState<'edit' | 'preview'>('edit')

  const deleteRecord = (id: string) => {
    const updated = records.filter((r) => r.meeting.id !== id)
    setRecords(updated)
    try {
      localStorage.setItem('voxclar_meeting_records', JSON.stringify(updated))
    } catch {}
    if (selectedId === id) {
      setSelectedId(updated[0]?.meeting.id || null)
    }
  }

  const isPremium = user?.subscription_tier && user.subscription_tier !== 'free'
  const record = selectedId
    ? (lastRecord?.meeting.id === selectedId ? lastRecord : records.find((r) => r.meeting.id === selectedId))
    : null

  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder: 'Meeting record will appear here...' }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Highlight,
    ],
    content: record ? recordToHtml(record, !!isPremium) : '',
    editorProps: {
      attributes: {
        class: 'prose prose-sm prose-invert max-w-none focus:outline-none min-h-[300px] text-sm leading-relaxed',
      },
    },
  }, [selectedId]) // 切换会议时重新初始化

  const copyText = useCallback(() => {
    if (!editor) return
    navigator.clipboard.writeText(editor.getText())
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [editor])

  const exportPDF = async () => {
    if (!editor || !record || !electronAPI) return
    const editorHtml = editor.getHTML()
    const title = record.meeting.title || 'Untitled Meeting'
    const html = wrapInPDFTemplate(editorHtml, record)
    await electronAPI.export.savePDF(html, `Voxclar-${title.replace(/\s+/g, '_')}.pdf`)
  }

  return (
    <div className="h-full flex gap-5">
      {/* Left: Meeting List */}
      <div className="w-60 flex-shrink-0 flex flex-col gap-2">
        <h3 className="text-sm font-semibold text-imeet-gold mb-1">Meeting History</h3>

        <div className="flex-1 overflow-y-auto space-y-1.5">
          {records.length === 0 && <p className="text-xs text-imeet-text-muted">No meetings yet</p>}
          {records.map((r) => (
            <div
              key={r.meeting.id}
              className={`relative group p-3 rounded-lg transition-all text-sm cursor-pointer ${
                selectedId === r.meeting.id
                  ? 'bg-imeet-gold/10 border border-imeet-gold/30'
                  : 'bg-imeet-panel border border-imeet-border hover:border-imeet-border-light'
              }`}
              onClick={() => setSelectedId(r.meeting.id)}
            >
              <p className="font-medium truncate pr-6">{r.meeting.title || 'Untitled'}</p>
              <div className="flex items-center gap-2 mt-1 text-xs text-imeet-text-muted">
                <Clock size={10} />
                <span>{formatDuration(r.meeting.duration_seconds)}</span>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); deleteRecord(r.meeting.id) }}
                className="absolute top-2.5 right-2.5 opacity-0 group-hover:opacity-100 text-white/20 hover:text-red-400 transition-all"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Right: Editor */}
      <div className="flex-1 flex flex-col min-w-0">
        {!record ? (
          <div className="flex-1 flex items-center justify-center text-imeet-text-muted">
            Select a meeting to view its record
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-bold">{record.meeting.title || 'Untitled Meeting'}</h2>
                <p className="text-xs text-imeet-text-muted">
                  {formatDate(record.meeting.created_at)} · {formatDuration(record.meeting.duration_seconds)}
                </p>
              </div>
              <div className="flex gap-2">
                {/* View Mode Toggle */}
                <div className="flex bg-imeet-panel rounded-lg border border-imeet-border overflow-hidden">
                  <button
                    onClick={() => setMode('edit')}
                    className={`px-3 py-1.5 text-xs font-medium flex items-center gap-1 transition-colors ${
                      mode === 'edit' ? 'bg-imeet-gold/15 text-imeet-gold' : 'text-imeet-text-muted hover:text-white'
                    }`}
                  >
                    <Pencil size={12} /> Edit
                  </button>
                  <button
                    onClick={() => setMode('preview')}
                    className={`px-3 py-1.5 text-xs font-medium flex items-center gap-1 transition-colors ${
                      mode === 'preview' ? 'bg-imeet-gold/15 text-imeet-gold' : 'text-imeet-text-muted hover:text-white'
                    }`}
                  >
                    <Eye size={12} /> Preview
                  </button>
                </div>
                <button onClick={copyText} className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  copied ? 'bg-green-500/20 text-green-400' : 'bg-white/5 text-imeet-text-secondary hover:text-white'
                }`}>
                  {copied ? <CheckCircle size={14} /> : <><Copy size={14} className="inline mr-1" />Copy</>}
                </button>
                <button onClick={exportPDF} className="px-3 py-1.5 rounded-lg text-xs font-medium bg-imeet-gold text-black hover:bg-imeet-gold-hover transition-all">
                  <FileDown size={14} className="inline mr-1" />Export PDF
                </button>
              </div>
            </div>

            {/* Toolbar — 编辑模式显示 */}
            {mode === 'edit' && editor && (
              <div className="flex items-center gap-0.5 px-3 py-2 bg-imeet-panel rounded-t-[10px] border border-b-0 border-imeet-border">
                <ToolbarButton onClick={() => editor.chain().focus().toggleBold().run()} active={editor.isActive('bold')} title="Bold">
                  <Bold size={14} />
                </ToolbarButton>
                <ToolbarButton onClick={() => editor.chain().focus().toggleItalic().run()} active={editor.isActive('italic')} title="Italic">
                  <Italic size={14} />
                </ToolbarButton>
                <ToolbarButton onClick={() => editor.chain().focus().toggleHighlight().run()} active={editor.isActive('highlight')} title="Highlight">
                  <Highlighter size={14} />
                </ToolbarButton>
                <div className="w-px h-5 bg-imeet-border mx-1" />
                <ToolbarButton onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} active={editor.isActive('heading', { level: 2 })} title="Heading">
                  <Heading2 size={14} />
                </ToolbarButton>
                <ToolbarButton onClick={() => editor.chain().focus().toggleBulletList().run()} active={editor.isActive('bulletList')} title="Bullet List">
                  <List size={14} />
                </ToolbarButton>
                <ToolbarButton onClick={() => editor.chain().focus().toggleOrderedList().run()} active={editor.isActive('orderedList')} title="Ordered List">
                  <ListOrdered size={14} />
                </ToolbarButton>
                <div className="w-px h-5 bg-imeet-border mx-1" />
                <ToolbarButton onClick={() => editor.chain().focus().setTextAlign('left').run()} active={editor.isActive({ textAlign: 'left' })} title="Align Left">
                  <AlignLeft size={14} />
                </ToolbarButton>
                <ToolbarButton onClick={() => editor.chain().focus().setTextAlign('center').run()} active={editor.isActive({ textAlign: 'center' })} title="Align Center">
                  <AlignCenter size={14} />
                </ToolbarButton>
                <div className="w-px h-5 bg-imeet-border mx-1" />
                <ToolbarButton onClick={() => editor.chain().focus().undo().run()} title="Undo">
                  <Undo size={14} />
                </ToolbarButton>
                <ToolbarButton onClick={() => editor.chain().focus().redo().run()} title="Redo">
                  <Redo size={14} />
                </ToolbarButton>

                <div className="flex-1" />

                {/* AI Summary Badge */}
                {!isPremium && (
                  <button
                    onClick={() => navigate('/subscription')}
                    className="flex items-center gap-1 text-[10px] bg-imeet-gold/10 text-imeet-gold px-2 py-1 rounded-full hover:bg-imeet-gold/20 transition-colors"
                  >
                    <Lock size={10} /> AI Summary — Upgrade
                  </button>
                )}
              </div>
            )}

            {/* Editor Content */}
            <div className={`flex-1 overflow-y-auto bg-imeet-panel border border-imeet-border p-6 ${
              mode === 'edit' ? 'rounded-b-[10px]' : 'rounded-[20px_20px_4px_20px]'
            }`}>
              {mode === 'preview' ? (
                <div className="bg-white rounded-lg p-8 min-h-full text-black">
                  {/* PDF Preview — 白色背景 */}
                  <div style={{ fontFamily: '-apple-system,BlinkMacSystemFont,sans-serif' }}>
                    <div className="flex justify-between items-start border-b-2 border-yellow-500 pb-4 mb-6">
                      <div>
                        <p className="text-xl font-bold"><span className="text-yellow-600">Vox</span>clar</p>
                        <h1 className="text-lg font-bold mt-1">{record.meeting.title || 'Untitled Meeting'}</h1>
                        <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">
                          {record.meeting.meeting_type.replace('_', ' ').toUpperCase()}
                        </span>
                      </div>
                      <div className="text-right text-xs text-gray-500 leading-relaxed">
                        <p>{formatDateLong(record.meeting.created_at)}</p>
                        <p>Duration: {formatDuration(record.meeting.duration_seconds)}</p>
                      </div>
                    </div>
                    <div
                      className="prose prose-sm max-w-none"
                      dangerouslySetInnerHTML={{ __html: editor?.getHTML() || '' }}
                    />
                    <div className="border-t mt-8 pt-4 text-center text-xs text-gray-400">
                      Generated by Voxclar — AI-Powered Interview Assistant
                    </div>
                  </div>
                </div>
              ) : (
                <EditorContent editor={editor} />
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

/** 把编辑器内容包在品牌化 PDF 模板里 */
function wrapInPDFTemplate(editorHtml: string, record: MeetingRecord): string {
  const title = record.meeting.title || 'Untitled Meeting'
  const date = formatDateLong(record.meeting.created_at)
  const duration = formatDuration(record.meeting.duration_seconds)

  return `<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  *{margin:0;padding:0;box-sizing:border-box;}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:48px;color:#222;line-height:1.6;}
  .header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:32px;padding-bottom:16px;border-bottom:2px solid #FFD700;}
  .logo{font-size:22px;font-weight:bold;} .logo span{color:#FFD700;}
  .meta{text-align:right;font-size:11px;color:#666;line-height:1.6;}
  h1{font-size:20px;margin:4px 0;} h2{font-size:16px;color:#B8960F;margin:20px 0 10px;border-bottom:1px solid #EEE;padding-bottom:6px;}
  p{margin:6px 0;font-size:13px;} strong{color:#333;}
  blockquote{margin:12px 0;padding:10px 14px;background:#FAFAF5;border-left:3px solid #FFD700;border-radius:4px;}
  .badge{display:inline-block;padding:2px 10px;border-radius:10px;font-size:10px;font-weight:600;background:#FFF3CD;color:#856404;margin-bottom:12px;}
  mark{background:#FFF3CD;padding:0 2px;border-radius:2px;}
  .footer{margin-top:40px;padding-top:12px;border-top:1px solid #EEE;text-align:center;font-size:9px;color:#BBB;}
  ul,ol{margin:8px 0 8px 20px;font-size:13px;} li{margin:3px 0;}
</style></head><body>
  <div class="header">
    <div>
      <div class="logo"><span>Vox</span>clar</div>
      <h1>${title}</h1>
      <span class="badge">${record.meeting.meeting_type.replace('_', ' ').toUpperCase()}</span>
    </div>
    <div class="meta"><div>${date}</div><div>Duration: ${duration}</div><div>ID: ${record.meeting.id.slice(0, 8)}</div></div>
  </div>
  ${editorHtml}
  <div class="footer">Generated by Voxclar — AI-Powered Interview Assistant<br>Confidential — Do not distribute without authorization.</div>
</body></html>`
}
