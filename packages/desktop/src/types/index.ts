export interface Meeting {
  id: string
  title?: string
  meeting_type: MeetingType
  language: string
  started_at?: string
  ended_at?: string
  duration_seconds: number
  points_consumed: number
  status: 'active' | 'completed' | 'cancelled'
  prep_notes?: string
  summary?: string
  created_at: string
}

export type MeetingType =
  | 'general'
  | 'phone_screen'
  | 'technical'
  | 'coffee_chat'
  | 'project_kickoff'
  | 'weekly_standup'

export interface Transcript {
  id: string
  meeting_id: string
  speaker: 'user' | 'other' | 'system'
  text: string
  language?: string
  timestamp_ms: number
  is_question: boolean
  confidence?: number
  is_final: boolean
}

export interface Answer {
  id: string
  question_text: string
  answer_text: string
  question_type: 'technical' | 'behavioral' | 'general'
  model_used?: string
  rating?: number
}

export interface MeetingRecord {
  meeting: Meeting
  transcripts: Transcript[]
  answers: Answer[]
  summary?: string
  summaryGenerating?: boolean
}

export interface EngineMessage {
  type: 'transcription' | 'question_detected' | 'answer' | 'engine_status' | 'error' | 'pong' | 'save_memory' | 'meeting_summary'
  text?: string
  is_final?: boolean
  speaker?: string
  speaker_label?: string
  language?: string
  timestamp_ms?: number
  question?: string
  question_type?: string
  confidence?: number
  token?: string
  status?: string
  details?: Record<string, unknown>
  message?: string
  memory?: unknown
  summary?: unknown
}

export interface MeetingConfig {
  title?: string
  meeting_type: MeetingType
  language: string
  audio_source: 'system' | 'mic'
  prep_notes?: string
}
