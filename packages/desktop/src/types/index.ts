export interface User {
  id: string
  email: string
  username: string
  avatar_url?: string
  subscription_tier: 'free' | 'basic' | 'standard' | 'pro'
  subscription_expires_at?: string
  points_balance: number
  is_active: boolean
  created_at: string
}

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

export interface Transaction {
  id: string
  type: 'purchase' | 'consume' | 'bonus' | 'refund'
  points: number
  amount_usd?: number
  description?: string
  created_at: string
}

export interface MeetingRecord {
  meeting: Meeting
  transcripts: Transcript[]
  answers: Answer[]
  summary?: string          // AI 摘要（高级会员）
  summaryGenerating?: boolean
}

export interface EngineMessage {
  type: 'transcription' | 'question_detected' | 'answer' | 'engine_status' | 'error' | 'pong'
  text?: string
  is_final?: boolean
  speaker?: string
  language?: string
  timestamp_ms?: number
  question?: string
  question_type?: string
  confidence?: number
  token?: string
  status?: string
  details?: Record<string, unknown>
  message?: string
}

export interface MeetingConfig {
  title?: string
  meeting_type: MeetingType
  language: string
  audio_source: 'system' | 'mic'
  prep_notes?: string
}

export interface UserStats {
  total_meetings: number
  total_duration_minutes: number
  meetings_this_month: number
  points_balance: number
  subscription_tier: string
}
