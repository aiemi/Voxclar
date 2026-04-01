import { useState } from 'react'
import { ThumbsUp, ThumbsDown, Copy, ChevronDown, ChevronUp } from 'lucide-react'
import type { Answer } from '@/types'

interface Props {
  answer: Answer
}

export default function AnswerCard({ answer }: Props) {
  const [expanded, setExpanded] = useState(true)

  const typeBadge = {
    technical: 'bg-blue-500/20 text-blue-400',
    behavioral: 'bg-purple-500/20 text-purple-400',
    general: 'bg-imeet-gold/20 text-imeet-gold',
  }[answer.question_type]

  return (
    <div className="bg-imeet-card rounded-imeet border border-imeet-border">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className={`text-xs px-2 py-0.5 rounded ${typeBadge}`}>
            {answer.question_type}
          </span>
          <p className="text-sm text-imeet-text-secondary truncate">{answer.question_text}</p>
        </div>
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {/* Body */}
      {expanded && (
        <div className="px-3 pb-3">
          <p className="text-sm whitespace-pre-wrap">{answer.answer_text || '...'}</p>
          <div className="flex gap-2 mt-2">
            <button className="text-imeet-text-muted hover:text-green-400 transition-colors">
              <ThumbsUp size={14} />
            </button>
            <button className="text-imeet-text-muted hover:text-red-400 transition-colors">
              <ThumbsDown size={14} />
            </button>
            <button
              className="text-imeet-text-muted hover:text-imeet-gold transition-colors"
              onClick={() => navigator.clipboard.writeText(answer.answer_text)}
            >
              <Copy size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
