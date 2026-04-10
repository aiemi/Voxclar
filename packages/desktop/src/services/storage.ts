/**
 * Storage abstraction — routes to API (cloud) or localStorage (local) based on subscription tier.
 *
 * Cloud tiers (standard, pro): data stored in server database
 * Local tiers (free, lifetime): data stored in localStorage with user ID prefix
 */
import { api } from './api'
import { useAuthStore } from '@/stores/authStore'
import type { MeetingRecord } from '@/types'

function getUserId(): string {
  return useAuthStore.getState().user?.id || 'anonymous'
}

function getTier(): string {
  return useAuthStore.getState().user?.subscription_tier || 'free'
}

function isCloudTier(): boolean {
  const tier = getTier()
  return tier === 'standard' || tier === 'pro'
}

function localKey(key: string): string {
  return `voxclar_${getUserId()}_${key}`
}

// ── Profile ──────────────────────────────────────────

export async function loadProfile(): Promise<any> {
  if (isCloudTier()) {
    try {
      const profile = await api.getCurrentUser()
      // Also try server profile
      const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8001/api/v1'
      const res = await fetch(`${apiBase}/profiles/me`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` },
      })
      if (res.ok) return await res.json()
    } catch {}
  }
  // Local fallback
  try {
    const raw = localStorage.getItem(localKey('profile'))
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

export function saveProfileLocal(data: any) {
  localStorage.setItem(localKey('profile'), JSON.stringify(data))
}

// ── Meeting Records ──────────────────────────────────

export async function loadRecords(): Promise<MeetingRecord[]> {
  if (isCloudTier()) {
    try {
      const { meetings } = await api.listMeetings(0, 50)
      // Fetch transcripts and answers for each meeting in parallel
      const records = await Promise.all(
        meetings.map(async (m) => {
          const [transcriptRes, answerRes] = await Promise.all([
            api.getTranscripts(m.id).catch(() => ({ transcripts: [], total: 0 })),
            api.getAnswers(m.id).catch(() => ({ answers: [], total: 0 })),
          ])
          return {
            meeting: m,
            transcripts: transcriptRes.transcripts,
            answers: answerRes.answers,
            summary: m.summary,
          } as MeetingRecord
        })
      )
      return records
    } catch {}
  }
  // Local fallback
  try {
    const raw = localStorage.getItem(localKey('records'))
    return raw ? JSON.parse(raw) : []
  } catch { return [] }
}

/** Load a single meeting's full data from cloud */
export async function loadCloudRecord(meetingId: string): Promise<MeetingRecord | null> {
  try {
    const [meeting, transcriptRes, answerRes] = await Promise.all([
      api.getMeeting(meetingId),
      api.getTranscripts(meetingId).catch(() => ({ transcripts: [], total: 0 })),
      api.getAnswers(meetingId).catch(() => ({ answers: [], total: 0 })),
    ])
    return {
      meeting,
      transcripts: transcriptRes.transcripts,
      answers: answerRes.answers,
      summary: meeting.summary,
    } as MeetingRecord
  } catch {
    return null
  }
}

export function saveRecordLocal(record: MeetingRecord) {
  try {
    const raw = localStorage.getItem(localKey('records'))
    const records: MeetingRecord[] = raw ? JSON.parse(raw) : []
    records.unshift(record)
    if (records.length > 50) records.length = 50
    localStorage.setItem(localKey('records'), JSON.stringify(records))
  } catch {}
}

export function updateRecordLocal(meetingId: string, updater: (r: MeetingRecord) => MeetingRecord) {
  try {
    const raw = localStorage.getItem(localKey('records'))
    const records: MeetingRecord[] = raw ? JSON.parse(raw) : []
    const updated = records.map((r) => r.meeting.id === meetingId ? updater(r) : r)
    localStorage.setItem(localKey('records'), JSON.stringify(updated))
  } catch {}
}

export function loadRecordsSync(): MeetingRecord[] {
  try {
    const raw = localStorage.getItem(localKey('records'))
    return raw ? JSON.parse(raw) : []
  } catch { return [] }
}

// ── Memory (always local, per user) ──────────────────

export function loadMemory(): string {
  return localStorage.getItem(localKey('memory')) || ''
}

export function saveMemory(data: any) {
  localStorage.setItem(localKey('memory'), JSON.stringify(data))
}

