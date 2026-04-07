import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { MessageCircle, X, Send, Mail } from 'lucide-react'

// @ts-ignore — Vite env
const BASE_URL: string = import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1'

/** Lightweight markdown → HTML for chat messages */
function renderMarkdown(text: string): string {
  let html = text
    // Code blocks
    .replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre style="background:rgba(255,255,255,0.05);padding:8px 12px;border-radius:8px;margin:8px 0;overflow-x:auto;font-size:0.85em"><code>$2</code></pre>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.08);padding:1px 5px;border-radius:3px;font-size:0.85em">$1</code>')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong style="color:#fff">$1</strong>')
    // Italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Headings (### or ##)
    .replace(/^#{2,3}\s+(.+)$/gm, '<div style="font-weight:600;color:#fff;margin:10px 0 4px">$1</div>')
    // Numbered lists
    .replace(/^\d+\.\s+(.+)$/gm, '<li style="margin-left:18px;list-style:decimal;margin-bottom:2px">$1</li>')
    // Bullet lists (with sub-items)
    .replace(/^ {2,}[-•]\s+(.+)$/gm, '<li style="margin-left:32px;list-style:circle;margin-bottom:1px;font-size:0.95em">$1</li>')
    .replace(/^[-•]\s+(.+)$/gm, '<li style="margin-left:18px;list-style:disc;margin-bottom:2px">$1</li>')
    // Wrap consecutive <li> in <ul>
    .replace(/((?:<li[^>]*>.*?<\/li>\n?)+)/g, '<ul style="margin:6px 0;padding:0">$1</ul>')

  // Paragraphs: split on double newlines, wrap non-tag content in <p>
  html = html
    .split(/\n{2,}/)
    .map(block => {
      const trimmed = block.trim()
      if (!trimmed) return ''
      if (trimmed.startsWith('<ul') || trimmed.startsWith('<pre') || trimmed.startsWith('<div')) return trimmed
      return `<p style="margin:0 0 8px">${trimmed.replace(/\n/g, '<br>')}</p>`
    })
    .join('')

  // Single newlines within remaining text
  html = html.replace(/([^>])\n([^<])/g, '$1<br>$2')

  // Clean up
  html = html.replace(/<\/ul><br>/g, '</ul>')
  html = html.replace(/<p style="margin:0 0 8px"><\/p>/g, '')

  return html
}

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function SupportChat() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || streaming) return

    const userMsg: Message = { role: 'user', content: text }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setStreaming(true)

    // Add placeholder for assistant
    setMessages((prev) => [...prev, { role: 'assistant', content: '' }])

    try {
      const token = localStorage.getItem('access_token')
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (token) headers['Authorization'] = `Bearer ${token}`

      const res = await fetch(`${BASE_URL}/support/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: text,
          history: messages.slice(-10),
        }),
      })

      if (!res.ok || !res.body) throw new Error('Failed')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') break
            setMessages((prev) => {
              const updated = [...prev]
              const last = updated[updated.length - 1]
              if (last.role === 'assistant') {
                updated[updated.length - 1] = { ...last, content: last.content + data }
              }
              return updated
            })
          }
        }
      }
    } catch {
      setMessages((prev) => {
        const updated = [...prev]
        const last = updated[updated.length - 1]
        if (last.role === 'assistant' && !last.content) {
          updated[updated.length - 1] = {
            ...last,
            content: t('support.error_message'),
          }
        }
        return updated
      })
    } finally {
      setStreaming(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="bg-imeet-panel rounded-[20px_20px_4px_20px] p-6 border border-imeet-border w-full text-left hover:border-imeet-gold/30 transition-colors group"
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-imeet-gold/10 flex items-center justify-center">
            <MessageCircle size={18} className="text-imeet-gold" />
          </div>
          <div>
            <h3 className="font-semibold group-hover:text-imeet-gold transition-colors">
              {t('support.title')}
            </h3>
            <p className="text-xs text-imeet-text-muted">{t('support.subtitle')}</p>
          </div>
        </div>
      </button>
    )
  }

  return (
    <div className="bg-imeet-panel rounded-[20px_20px_4px_20px] border border-imeet-gold/30 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-imeet-border">
        <div className="flex items-center gap-2">
          <MessageCircle size={16} className="text-imeet-gold" />
          <span className="font-semibold text-sm">{t('support.title')}</span>
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
        </div>
        <button
          onClick={() => setOpen(false)}
          className="p-1.5 rounded-lg hover:bg-white/5 text-imeet-text-muted hover:text-white transition-colors"
        >
          <X size={14} />
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="h-[320px] overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 && (
          <div className="text-center py-8 text-imeet-text-muted text-sm space-y-2">
            <MessageCircle size={32} className="mx-auto opacity-30" />
            <p>{t('support.welcome')}</p>
            <div className="flex flex-wrap gap-1.5 justify-center mt-3">
              {[t('support.quick_1'), t('support.quick_2'), t('support.quick_3')].map((q) => (
                <button
                  key={q}
                  onClick={() => { setInput(q); }}
                  className="px-3 py-1.5 rounded-full text-xs border border-imeet-border hover:border-imeet-gold/50 hover:text-imeet-gold transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-imeet-gold/15 text-imeet-gold rounded-br-sm whitespace-pre-wrap'
                  : 'bg-white/5 text-imeet-text-primary rounded-bl-sm support-msg'
              }`}
            >
              {msg.content ? (
                msg.role === 'assistant' ? (
                  <div dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }} />
                ) : (
                  msg.content
                )
              ) : (
                <span className="inline-flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-imeet-text-muted animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-imeet-text-muted animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-imeet-text-muted animate-bounce" style={{ animationDelay: '300ms' }} />
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="px-4 pb-3">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t('support.placeholder')}
            disabled={streaming}
            className="flex-1 bg-black/30 border border-imeet-border rounded-xl px-4 py-2.5 text-sm
                       focus:outline-none focus:border-imeet-gold/50 disabled:opacity-50
                       placeholder:text-imeet-text-muted"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || streaming}
            className="p-2.5 rounded-xl bg-imeet-gold/15 text-imeet-gold hover:bg-imeet-gold/25
                       disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <Send size={16} />
          </button>
        </div>
        <div className="flex items-center justify-center gap-1.5 mt-2 text-[11px] text-imeet-text-muted">
          <Mail size={10} />
          <span>{t('support.email_fallback')}</span>
        </div>
      </div>
    </div>
  )
}
