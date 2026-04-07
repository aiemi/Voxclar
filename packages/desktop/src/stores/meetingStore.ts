import { create } from 'zustand'
import type { Meeting, Transcript, Answer, MeetingRecord } from '@/types'
import { saveRecordLocal, loadRecordsSync, updateRecordLocal } from '@/services/storage'

/**
 * 双轨累积：system(other) 和 mic(user) 各自独立累积文本。
 * 只有 is_final 才追加到对应轨道的 Transcript 条目。
 * interim 更新当前条目文本但不创建新条目。
 * 两个轨道不互相干扰。
 */

interface MeetingState {
  activeMeeting: Meeting | null
  transcripts: Transcript[]
  answers: Answer[]
  isRecording: boolean
  elapsedSeconds: number
  lastRecord: MeetingRecord | null  // 刚结束的会议记录

  startMeeting: (meeting: Meeting) => void
  stopMeeting: () => void
  addTranscript: (t: Transcript) => void
  updateTranscript: (text: string, isFinal: boolean, speaker: 'user' | 'other') => void
  addAnswer: (a: Answer) => void
  appendAnswerToken: (token: string) => void
  setElapsed: (s: number) => void
  setLastRecordSummary: (summary: string) => void
  reset: () => void
}

// 每个 speaker 轨道的累积状态
interface TrackState {
  entryId: string       // 当前 transcript 条目的 id
  confirmedText: string // 已 final 的累积文本
}

const tracks: Record<string, TrackState> = {}

function resetTracks() {
  delete tracks['other']
  delete tracks['user']
}

/** 读取历史会议记录 (同步, 本地用户用) */
export function loadRecords(): MeetingRecord[] {
  return loadRecordsSync()
}

export const useMeetingStore = create<MeetingState>((set, get) => ({
  activeMeeting: null,
  transcripts: [],
  answers: [],
  isRecording: false,
  lastRecord: null,
  elapsedSeconds: 0,

  startMeeting: (meeting) => {
    resetTracks()
    set({ activeMeeting: meeting, transcripts: [], answers: [], isRecording: true, elapsedSeconds: 0 })
  },

  stopMeeting: () => {
    const { activeMeeting, transcripts, answers, elapsedSeconds } = get()
    if (activeMeeting) {
      const record: MeetingRecord = {
        meeting: {
          ...activeMeeting,
          status: 'completed',
          duration_seconds: elapsedSeconds,
          ended_at: new Date().toISOString(),
        },
        transcripts: [...transcripts],
        answers: [...answers],
      }
      // Always save locally (per-user key)
      saveRecordLocal(record)
      set({ isRecording: false, lastRecord: record })
    } else {
      set({ isRecording: false })
    }
  },

  addTranscript: (t) => set((state) => ({ transcripts: [...state.transcripts, t] })),

  updateTranscript: (text, isFinal, speaker) =>
    set((state) => {
      const transcripts = [...state.transcripts]
      let track = tracks[speaker]

      if (!track) {
        const id = crypto.randomUUID()
        tracks[speaker] = { entryId: id, confirmedText: isFinal ? text : '' }
        transcripts.push({
          id,
          meeting_id: state.activeMeeting?.id || '',
          speaker,
          text,
          timestamp_ms: Date.now(),
          is_question: false,
          is_final: false,
        })
        return { transcripts }
      }

      const idx = transcripts.findIndex((t) => t.id === track.entryId)
      if (idx === -1) {
        const id = crypto.randomUUID()
        tracks[speaker] = { entryId: id, confirmedText: isFinal ? text : '' }
        transcripts.push({
          id,
          meeting_id: state.activeMeeting?.id || '',
          speaker,
          text,
          timestamp_ms: Date.now(),
          is_question: false,
          is_final: false,
        })
        return { transcripts }
      }

      if (isFinal) {
        track.confirmedText = track.confirmedText
          ? `${track.confirmedText} ${text}`
          : text
        transcripts[idx] = {
          ...transcripts[idx],
          text: track.confirmedText,
          timestamp_ms: Date.now(),
        }
      } else {
        const display = track.confirmedText
          ? `${track.confirmedText} ${text}`
          : text
        transcripts[idx] = {
          ...transcripts[idx],
          text: display,
          timestamp_ms: Date.now(),
        }
      }

      return { transcripts }
    }),

  addAnswer: (a) => set((state) => ({ answers: [...state.answers, a] })),

  appendAnswerToken: (token) =>
    set((state) => {
      const last = state.answers[state.answers.length - 1]
      if (last) {
        const updated = [...state.answers]
        updated[updated.length - 1] = { ...last, answer_text: last.answer_text + token }
        return { answers: updated }
      }
      return state
    }),

  setElapsed: (s) => set({ elapsedSeconds: s }),

  setLastRecordSummary: (summary) => set((state) => {
    if (!state.lastRecord) return state
    const updated = { ...state.lastRecord, summary, summaryGenerating: false }
    // 同步更新本地存储
    updateRecordLocal(updated.meeting.id, () => updated)
    return { lastRecord: updated }
  }),

  reset: () => {
    resetTracks()
    set({ activeMeeting: null, transcripts: [], answers: [], isRecording: false, elapsedSeconds: 0 })
  },
}))
