import { useEffect, useRef, useCallback } from 'react'
import { useEngineStore } from '@/stores/engineStore'
import { useMeetingStore } from '@/stores/meetingStore'
import type { EngineMessage, MeetingConfig } from '@/types'

const electronAPI = (window as unknown as { electronAPI?: {
  caption: { update: (data: unknown) => void }
} }).electronAPI

const ENGINE_URL = 'ws://localhost:9876'
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000]

export function useEngine() {
  const ws = useRef<WebSocket | null>(null)
  const reconnectAttempt = useRef(0)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  const { updateStatus, setError } = useEngineStore()
  const { updateTranscript, addAnswer, appendAnswerToken } = useMeetingStore()

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return

    updateStatus('connecting')
    const socket = new WebSocket(ENGINE_URL)

    socket.onopen = () => {
      reconnectAttempt.current = 0
      updateStatus('ready')
    }

    socket.onmessage = (event) => {
      const msg: EngineMessage = JSON.parse(event.data)

      switch (msg.type) {
        case 'transcription':
          updateTranscript(
            msg.text || '',
            msg.is_final || false,
            (msg.speaker as 'user' | 'other') || 'other',
          )
          // 系统音频直接推到字幕窗口 — 不经过 store 累积
          if (msg.speaker === 'other') {
            electronAPI?.caption.update({
              transcript: {
                text: msg.text,
                speaker: (msg.speaker_label as string) || 'other',
                is_final: msg.is_final,
              },
              answer: null,
            })
          }
          break
        case 'question_detected':
          addAnswer({
            id: crypto.randomUUID(),
            question_text: msg.question || '',
            answer_text: '',
            question_type: (msg.question_type as 'technical' | 'behavioral' | 'general') || 'general',
          })
          break
        case 'answer':
          if (msg.token) {
            appendAnswerToken(msg.token)
            // AI 回答 token 也直接推到字幕
            const latestAnswer = useMeetingStore.getState().answers
            const last = latestAnswer[latestAnswer.length - 1]
            if (last) {
              electronAPI?.caption.update({
                transcript: null,
                answer: { text: last.answer_text + msg.token, type: last.question_type },
              })
            }
          }
          break
        case 'engine_status':
          updateStatus(
            (msg.status as 'ready' | 'running') || 'ready',
            msg.details as Record<string, unknown>
          )
          break
        case 'save_memory':
          if (msg.memory) {
            import('@/services/storage').then(({ saveMemory }) => saveMemory(msg.memory))
          }
          break
        case 'meeting_summary':
          // AI 会议摘要生成完成
          if (msg.summary) {
            useMeetingStore.getState().setLastRecordSummary(msg.summary as string)
          }
          break
        case 'error':
          setError(msg.message || 'Unknown engine error')
          break
      }
    }

    socket.onclose = () => {
      updateStatus('disconnected')
      scheduleReconnect()
    }

    socket.onerror = () => {
      setError('Engine connection failed')
    }

    ws.current = socket
  }, [updateStatus, setError, updateTranscript, addAnswer, appendAnswerToken])

  const scheduleReconnect = useCallback(() => {
    const delay = RECONNECT_DELAYS[Math.min(reconnectAttempt.current, RECONNECT_DELAYS.length - 1)]
    reconnectAttempt.current++
    reconnectTimer.current = setTimeout(connect, delay)
  }, [connect])

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimer.current)
    ws.current?.close()
    ws.current = null
  }, [])

  const sendMessage = useCallback((msg: Record<string, unknown>) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(msg))
    }
  }, [])

  const startMeeting = useCallback(async (config: MeetingConfig) => {
    // 清空字幕窗口上一次会议的内容
    electronAPI?.caption.update({ transcript: null, answer: null })

    // 加载 profile context (per-user)
    let profileContext = ''
    try {
      const { loadProfile } = await import('@/services/storage')
      const profile = await loadProfile()
      if (profile) profileContext = profile.context || ''
    } catch {}

    // 加载历史记忆 (per-user)
    let memoryData = ''
    try {
      const { loadMemory } = await import('@/services/storage')
      memoryData = loadMemory()
    } catch {}

    // Determine ASR mode based on subscription tier
    const { useAuthStore } = await import('@/stores/authStore')
    const user = useAuthStore.getState().user
    const isLifetime = user?.subscription_tier === 'lifetime'

    // All users go through server for AI. Only ASR differs.
    let asrMode = 'server'  // Default: server Deepgram proxy
    // @ts-ignore
    const serverApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1'
    const serverToken = localStorage.getItem('access_token') || ''

    if (isLifetime) {
      // Lifetime can choose local ASR (faster-whisper) to save minutes
      try {
        const { loadLifetimeConfig } = await import('@/services/storage')
        const lc = loadLifetimeConfig()
        if (lc?.asr_mode === 'local') {
          asrMode = 'local'
        }
      } catch {}
    }

    sendMessage({
      type: 'start_meeting',
      meeting_type: config.meeting_type,
      meeting_title: config.title,
      language: config.language,
      audio_source: config.audio_source,
      prep_notes: config.prep_notes,
      profile_context: profileContext,
      prep_docs_summary: config.prep_notes,
      memory_data: memoryData,
      asr_mode: asrMode,
      server_api_url: serverApiUrl,
      server_token: serverToken,
    })
  }, [sendMessage])

  const stopMeeting = useCallback(() => {
    sendMessage({ type: 'stop_meeting' })
  }, [sendMessage])

  useEffect(() => {
    connect()
    return disconnect
  }, [connect, disconnect])

  return { startMeeting, stopMeeting, sendMessage }
}
