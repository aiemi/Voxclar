import { useRef, useEffect } from 'react'
import type { Transcript } from '@/types'

interface Props {
  transcripts: Transcript[]
}

export default function TranscriptView({ transcripts }: Props) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcripts])

  const speakerColors: Record<string, string> = {
    user: 'text-blue-400',
    other: 'text-imeet-gold',
    system: 'text-gray-500',
  }

  return (
    <div className="space-y-2 text-sm">
      {transcripts.map((tr) => (
        <div key={tr.id} className={tr.is_final ? 'text-white' : 'text-imeet-text-secondary'}>
          <span className={`${speakerColors[tr.speaker] || 'text-gray-400'} text-xs mr-2 font-mono`}>
            [{tr.speaker}]
          </span>
          {tr.text}
        </div>
      ))}
      <div ref={endRef} />
    </div>
  )
}
