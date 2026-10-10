// Additive fields the hub already sends (docs/sino/architecture.md).
import type { Entry, Health, HubEvent } from '../types'

interface FeedLog {
  entries: Entry[]
  health: Health | null
}

export type ReplyVariant = 'ate' | 'ate_repeat' | 'unknown'

const str = (v: unknown) => (typeof v === 'string' ? v : '')

let seq = 0
const newId = () => `e${Date.now()}-${seq++}`

export function whoName(who: string): string {
  const name = who.trim()
  if (!name) return ''
  return name.charAt(0).toUpperCase() + name.slice(1)
}

function variantOf(value: unknown): ReplyVariant | undefined {
  if (value === 'ate' || value === 'ate_repeat' || value === 'unknown') return value
  return undefined
}

export type MealKey = 'mealAte' | 'mealRepeat' | 'mealUnknown'

export function mealKey(variant: ReplyVariant): MealKey {
  switch (variant) {
    case 'ate':
      return 'mealAte'
    case 'ate_repeat':
      return 'mealRepeat'
    case 'unknown':
      return 'mealUnknown'
    default: {
      const _never: never = variant
      return _never
    }
  }
}

export type Voice =
  | { type: 'who'; name: string }
  | { type: 'meal'; variant: ReplyVariant }
  | { type: 'speaker'; name: string }

export function voiceOf(entry: Entry): Voice | null {
  if (entry.who) return { type: 'who', name: whoName(entry.who) }
  if (entry.replyVariant) return { type: 'meal', variant: entry.replyVariant }
  if (entry.speaker) return { type: 'speaker', name: entry.speaker }
  return null
}

export interface AboutLola {
  text: string
  source: string
  latencyMs?: number
  snapshot?: string
  label?: string
}

export function readAbout(event: HubEvent): AboutLola | null {
  if (event.event !== 'about_lola') return null
  const snapshot = str(event.snapshot)
  const label = str(event.label)
  return {
    text: str(event.answer),
    source: str(event.source),
    latencyMs: typeof event.latency_ms === 'number' ? event.latency_ms : undefined,
    snapshot: snapshot || undefined,
    label: label || undefined,
  }
}

export function applyHubEvent(state: FeedLog, event: HubEvent, at: number): FeedLog {
  if (event.event === 'health') return { ...state, health: event as unknown as Health }
  if (event.event === 'alert') {
    const kind = str(event.kind)
    const entry: Entry = {
      id: newId(),
      kind: 'urgent',
      transcript: str(event.transcript),
      at,
      count: 1,
      alertKind: kind || undefined,
    }
    return { ...state, entries: [entry, ...state.entries] }
  }
  if (event.event === 'urgent_reply') {
    return {
      ...state,
      entries: state.entries.map((x) => (x.kind === 'urgent' ? { ...x, kind: 'seen' } : x)),
    }
  }
  if (event.event === 'ask_caregiver') {
    const transcript = str(event.transcript)
    const count = typeof event.count === 'number' ? event.count : 1
    const open = state.entries.find((x) => x.kind === 'needs' && x.transcript === transcript)
    if (open) {
      const updated = { ...open, count, at }
      return { ...state, entries: [updated, ...state.entries.filter((x) => x.id !== open.id)] }
    }
    const entry: Entry = { id: newId(), kind: 'needs', transcript, at, firstAt: at, count }
    return { ...state, entries: [entry, ...state.entries] }
  }
  if (event.event === 'decided' && event.action === 'comfort') {
    const who = str(event.who)
    const entry: Entry = {
      id: newId(),
      kind: 'answered',
      transcript: str(event.transcript),
      at,
      count: 1,
      replyId: str(event.reply_id),
      who: who || undefined,
      replyVariant: variantOf(event.reply_variant),
    }
    return { ...state, entries: [entry, ...state.entries] }
  }
  return state
}
