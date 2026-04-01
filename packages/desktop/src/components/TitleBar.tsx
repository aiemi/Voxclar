import { Minus, Square, X } from 'lucide-react'

const api = (window as unknown as { electronAPI?: {
  window: { minimize: () => void; maximize: () => void; close: () => void }
} }).electronAPI

export default function TitleBar() {
  return (
    <div className="drag-region h-8 bg-imeet-panel border-b border-imeet-border flex items-center justify-between px-2 flex-shrink-0">
      {/* macOS 左侧留空给交通灯按钮 */}
      <div className="w-20" />

      <span className="text-xs text-imeet-text-muted select-none">Voxclar</span>

      {/* Windows 风格窗口按钮（macOS 上隐藏，用原生交通灯） */}
      <div className="no-drag flex items-center gap-1">
        {api && (
          <>
            <button
              onClick={() => api.window.minimize()}
              className="w-6 h-6 flex items-center justify-center rounded hover:bg-imeet-card text-imeet-text-secondary hover:text-white transition-colors"
            >
              <Minus size={12} />
            </button>
            <button
              onClick={() => api.window.maximize()}
              className="w-6 h-6 flex items-center justify-center rounded hover:bg-imeet-card text-imeet-text-secondary hover:text-white transition-colors"
            >
              <Square size={10} />
            </button>
            <button
              onClick={() => api.window.close()}
              className="w-6 h-6 flex items-center justify-center rounded hover:bg-red-500 text-imeet-text-secondary hover:text-white transition-colors"
            >
              <X size={12} />
            </button>
          </>
        )}
      </div>
    </div>
  )
}
