/**
 * Storage -- Lifetime version. Everything is local (localStorage).
 */
import type { MeetingRecord } from '@/types'

function localKey(key: string): string {
  return `voxclar_lifetime_${key}`
}

// -- Profile --

export async function loadProfile(): Promise<any> {
  try {
    const raw = localStorage.getItem(localKey('profile'))
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

export function saveProfileLocal(data: any) {
  localStorage.setItem(localKey('profile'), JSON.stringify(data))
}

// -- Meeting Records --

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

export async function loadRecords(): Promise<MeetingRecord[]> {
  return loadRecordsSync()
}

// -- Memory (local) --

export function loadMemory(): string {
  return localStorage.getItem(localKey('memory')) || ''
}

export function saveMemory(data: any) {
  localStorage.setItem(localKey('memory'), JSON.stringify(data))
}

// -- Lifetime Config (API keys, ASR mode) --

export function loadLifetimeConfig(): any {
  try {
    const raw = localStorage.getItem(localKey('config'))
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

export function saveLifetimeConfigStorage(config: any) {
  localStorage.setItem(localKey('config'), JSON.stringify(config))
}
