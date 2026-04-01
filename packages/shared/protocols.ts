// Shared protocol types between desktop and engine

export type EngineMessageType =
  | 'transcription'
  | 'question_detected'
  | 'answer'
  | 'engine_status'
  | 'error'
  | 'start_meeting'
  | 'stop_meeting'
  | 'update_settings'
  | 'ping'
  | 'pong'

export type MeetingType =
  | 'general'
  | 'phone_screen'
  | 'technical'
  | 'coffee_chat'
  | 'project_kickoff'
  | 'weekly_standup'

export type QuestionType = 'technical' | 'behavioral' | 'general'
export type Speaker = 'user' | 'other' | 'system'
export type SubscriptionTier = 'free' | 'basic' | 'standard' | 'pro'
export type EngineStatus = 'disconnected' | 'connecting' | 'ready' | 'running' | 'error'

export interface MeetingConfig {
  meeting_type: MeetingType
  language: string
  audio_source: 'system' | 'mic'
  title?: string
  prep_notes?: string
}

export interface TranscriptionMessage {
  type: 'transcription'
  text: string
  is_final: boolean
  speaker: Speaker
  language: string
  timestamp_ms: number
  confidence?: number
}

export interface QuestionDetectedMessage {
  type: 'question_detected'
  question: string
  question_type: QuestionType
  confidence: number
}

export interface AnswerMessage {
  type: 'answer'
  token: string
}

export interface EngineStatusMessage {
  type: 'engine_status'
  status: EngineStatus
  details?: Record<string, unknown>
}

export type EngineMessage =
  | TranscriptionMessage
  | QuestionDetectedMessage
  | AnswerMessage
  | EngineStatusMessage
  | { type: 'error'; message: string }
  | { type: 'pong' }
