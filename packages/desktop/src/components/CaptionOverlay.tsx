import { useState, useEffect, useRef } from 'react'

interface CaptionData {
  transcript: { text: string; speaker: string; is_final: boolean } | null
  answer: { text: string; type: string } | null
}

const electronAPI = (window as unknown as { electronAPI?: {
  caption: {
    onData: (cb: (data: unknown) => void) => () => void
    setOpacity: (opacity: number) => void
  }
} }).electronAPI

export default function CaptionOverlay() {
  const [confirmed, setConfirmed] = useState('')
  const [pending, setPending] = useState('')
  const [answer, setAnswer] = useState<{ text: string; type: string } | null>(null)
  const [opacity, setOpacity] = useState(0.88)
  const [showSettings, setShowSettings] = useState(false)
  const textRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!electronAPI) return
    const cleanup = electronAPI.caption.onData((raw) => {
      const data = raw as CaptionData
      if (data.transcript) {
        if (data.transcript.is_final) {
          setConfirmed((prev) => {
            const combined = prev ? `${prev} ${data.transcript!.text}` : data.transcript!.text
            return combined.length > 500 ? combined.slice(-500) : combined
          })
          setPending('')
        } else {
          setPending(data.transcript.text)
        }
      }
      if (data.answer) setAnswer(data.answer)
    })
    return cleanup
  }, [])

  useEffect(() => {
    if (textRef.current) {
      textRef.current.scrollTop = textRef.current.scrollHeight
    }
  }, [confirmed, pending])

  const changeOpacity = (v: number) => {
    setOpacity(v)
    electronAPI?.caption.setOpacity(v)
  }

  const displayText = confirmed || pending

  return (
    <div className="h-screen w-screen select-none flex flex-col" style={{ borderRadius: '12px', overflow: 'hidden' }}>
      {/* 顶部工具栏 — 可拖动 + 设置按钮 */}
      <div
        className="flex items-center justify-between px-3 py-1.5 flex-shrink-0"
        style={{
          WebkitAppRegion: 'drag',
          background: `rgba(15, 15, 15, ${Math.min(opacity + 0.05, 1)})`,
        } as React.CSSProperties}
      >
        <span className="text-[10px] text-amber-400/50 font-medium tracking-wider">Voxclar</span>

        <div className="flex items-center gap-1 relative" style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}>
          {/* 透明度快捷按钮 */}
          {showSettings && (
            <div className="flex items-center gap-0.5 mr-1">
              {[0.3, 0.5, 0.7, 0.85, 1.0].map((v) => (
                <button
                  key={v}
                  onClick={() => changeOpacity(v)}
                  className={`text-[10px] px-1.5 py-0.5 rounded transition-colors ${
                    Math.abs(opacity - v) < 0.05
                      ? 'bg-amber-500/30 text-amber-400'
                      : 'text-white/40 hover:bg-white/15 hover:text-white/70'
                  }`}
                >
                  {Math.round(v * 100)}%
                </button>
              ))}
            </div>
          )}
          {/* 设置按钮 — 大点击区域 */}
          <button
            onClick={() => setShowSettings((v) => !v)}
            className="px-2 py-1 rounded hover:bg-white/15 transition-colors text-[11px] text-white/50 hover:text-white/80"
          >
            {showSettings ? '✕' : '⚙ Settings'}
          </button>
        </div>
      </div>

      {/* 内容区 — 不可拖动，滚动条可用 */}
      <div
        className="flex-1 flex flex-col min-h-0 px-4 py-2"
        style={{
          WebkitAppRegion: 'no-drag',
          background: `rgba(20, 20, 20, ${opacity})`,
        } as React.CSSProperties}
      >
        {/* 字幕 */}
        <div
          ref={textRef}
          className={`overflow-y-auto min-h-0 custom-scrollbar ${answer?.text ? 'max-h-[45%]' : 'flex-1'}`}
        >
          {displayText ? (
            <p className="text-[15px] leading-relaxed">
              <span className="text-white/90">{confirmed}</span>
              {pending && <span className="text-white/50">{` ${pending}`}</span>}
            </p>
          ) : (
            <div className="flex items-center gap-2 text-[11px] text-white/25 py-2">
              <div className="w-1.5 h-1.5 rounded-full bg-green-500/60 animate-pulse" />
              <span>Waiting for speech...</span>
            </div>
          )}
        </div>

        {/* AI 回答 */}
        {answer?.text && (
          <div className="flex-1 min-h-0 overflow-y-auto border-t border-amber-400/20 pt-2 mt-2 custom-scrollbar">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[9px] bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded font-medium">AI</span>
              <span className="text-[9px] text-white/40 uppercase">{answer.type}</span>
            </div>
            <p className="text-[13px] text-white/85 leading-relaxed whitespace-pre-wrap">{answer.text}</p>
          </div>
        )}
      </div>

      <style>{`
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 3px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.35); }
      `}</style>
    </div>
  )
}
