// Turns /ws events into the caregiver's cards (architecture.md, "Events").
//   alert          -> red urgent card, pinned until marked read
//   ask_caregiver  -> quiet yellow card; repeats of the same words share one card
//   decided comfort-> green "answered" card
//   health         -> the status bar on the sala card
import type { Entry, Health, HubEvent } from '../types'

export interface LogState {
  entries: Entry[] // newest first
  health: Health | null
}

export type LogAction =
  | { type: 'event'; event: HubEvent; at: number }
  | { type: 'markRead'; id: string }
  | { type: 'unmarkRead'; id: string }
  | { type: 'replySaved'; id: string; speaker: string }
  | { type: 'load'; entries: Entry[] } // restore what this phone saved earlier
  | { type: 'addNote'; entry: Entry } // an activity the caregiver logged
  | { type: 'removeNote'; id: string }

export const initialLog: LogState = { entries: [], health: null }

let seq = 0
const newId = () => `e${Date.now()}-${seq++}`
const str = (v: unknown) => (typeof v === 'string' ? v : '')

export function logReducer(state: LogState, action: LogAction): LogState {
  switch (action.type) {
    case 'event': {
      const e = action.event
      if (e.event === 'health') return { ...state, health: e as unknown as Health }
      if (e.event === 'alert') {
        const entry: Entry = { id: newId(), kind: 'urgent', transcript: str(e.transcript), at: action.at, count: 1 }
        return { ...state, entries: [entry, ...state.entries] }
      }
      if (e.event === 'ask_caregiver') {
        const transcript = str(e.transcript)
        const count = typeof e.count === 'number' ? e.count : 1
        const open = state.entries.find((x) => x.kind === 'needs' && x.transcript === transcript)
        if (open) {
          // same words again: update the one card and move it to the top
          const updated = { ...open, count, at: action.at }
          return { ...state, entries: [updated, ...state.entries.filter((x) => x.id !== open.id)] }
        }
        const entry: Entry = { id: newId(), kind: 'needs', transcript, at: action.at, firstAt: action.at, count }
        return { ...state, entries: [entry, ...state.entries] }
      }
      if (e.event === 'decided' && e.action === 'comfort') {
        const entry: Entry = {
          id: newId(), kind: 'answered', transcript: str(e.transcript), at: action.at, count: 1, replyId: str(e.reply_id),
        }
        return { ...state, entries: [entry, ...state.entries] }
      }
      return state // heard, silent decided, play_reply and others are not for this screen
    }
    case 'load':
      return { ...state, entries: [...state.entries, ...action.entries.filter((x) => !state.entries.some((y) => y.id === x.id))].sort((a, b) => b.at - a.at) }
    case 'addNote':
      return { ...state, entries: [action.entry, ...state.entries] }
    case 'removeNote':
      return { ...state, entries: state.entries.filter((x) => x.id !== action.id) }
    case 'markRead':
      return { ...state, entries: state.entries.map((x) => (x.id === action.id ? { ...x, kind: 'seen' } : x)) }
    case 'unmarkRead':
      return { ...state, entries: state.entries.map((x) => (x.id === action.id ? { ...x, kind: 'urgent' } : x)) }
    case 'replySaved':
      return {
        ...state,
        entries: state.entries.map((x) =>
          x.id === action.id ? { ...x, kind: 'answered', speaker: action.speaker, savedByYou: true } : x,
        ),
      }
  }
}
