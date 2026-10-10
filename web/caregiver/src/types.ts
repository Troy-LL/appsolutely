// Shapes from docs/sino/architecture.md ("The 3 interfaces"). Do not rename keys.

export type Lang = 'tl' | 'en' | 'both'
export type Scale = 0 | 1 | 2 // A, A+, A++
export type Screen = 'home' | 'family' | 'ask' | 'activity' | 'receipt' | 'knows' | 'record' | 'person' | 'add' | 'account' | 'monitor' | 'calibrate'
export type MemberColor = 'green' | 'amber' | 'red'

// health event (plus the additive model / last_event_at fields)
export interface Health {
  whisper: boolean
  ollama: boolean
  server: boolean
  mic: boolean
  offline: boolean
  model?: string
  last_event_at?: string
}

// Questions file entry: {id, question, phrasings[], reply_audio, photo, speaker}
export interface Question {
  id: string
  question: string
  phrasings: string[]
  reply_audio: string
  photo: string
  speaker: string
  by_person?: Record<string, { reply_audio?: string; photo?: string; speaker?: string }>
}

// Any message from /ws. We only read the events the caregiver screen gets.
export interface HubEvent {
  event: string
  [key: string]: unknown
}

// One card on the caregiver phone, built from the events above.
export type EntryKind = 'urgent' | 'seen' | 'needs' | 'answered' | 'note'
export interface Entry {
  id: string
  kind: EntryKind
  transcript: string // Lola's exact words. Never translated.
  at: number // ms since epoch, when the phone got it (latest repeat)
  firstAt?: number // first time Lola said it (grouped yellow cards)
  count: number // ask_caregiver repeats of the same transcript
  replyId?: string // comfort: which reply played
  speaker?: string // comfort: whose voice played
  who?: string // decided.who from face match
  replyVariant?: 'ate' | 'ate_repeat' | 'unknown'
  alertKind?: string // alert.kind, when the hub sends one
  savedByYou?: boolean // a reply recorded on this phone
  sentToHub?: boolean // meal_logged already went out; Undo does not unsend
  label?: [string, string] // note: what Lola did, [Tagalog, English]
  preset?: string // note: which quick pick, e.g. 'ate'
}

// The full-screen red alarm, opened by an alert event. It shows the newest red card
// (Lola's words) and closes on "Papunta na ako / On my way" or an urgent_reply.
export interface Alarm {
  ringing: boolean // false once the 2-minute cap stopped the sound
  silent: boolean // this phone could not make sound when the alert came
}

export interface Person {
  id?: string // hub/data/family.json id, when this frame was added on the wall
  name: string // as Lola says it, e.g. "Joy"
  color: MemberColor
  photo?: string // /media/... from by_person, a question photo, or an added member
  local?: boolean // added on this phone only (fake feed, not on the hub)
}

// Ask Sino about Lola (T7). The caregiver socket sends ask_about_lola and gets about_lola back
// (architecture.md, "Ask Sino about Lola"). Answers are built from the log, never a diagnosis.
export type AskIntent = 'how' | 'saying' | 'where' | 'ate' | 'unknown'
export interface ChatMsg {
  id: string
  from: 'you' | 'sino'
  text: string
  at: number
  pending?: boolean
  error?: boolean
  source?: string // "rule" / "model" from the hub, "fake" on the fake feed
  latencyMs?: number
  snapshot?: string // about_lola, caregiver only, "/clips/snapshot"
  label?: string // about_lola, e.g. "RECORDED CLIP · DEMO"
}
