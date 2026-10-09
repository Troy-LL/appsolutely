// Turns /ws events into the caregiver's cards (architecture.md, "Events").
//   alert          -> red urgent card, pinned until marked read
//   ask_caregiver  -> quiet yellow card; repeats of the same words share one card
//   decided comfort-> green "answered" card
//   health         -> the status bar on the sala card
import type { Entry, Health, HubEvent } from '../types'
import { applyHubEvent } from '../feed/events'

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

export function logReducer(state: LogState, action: LogAction): LogState {
  switch (action.type) {
    case 'event':
      return applyHubEvent(state, action.event, action.at)
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
    default: {
      const _never: never = action
      return _never
    }
  }
}
