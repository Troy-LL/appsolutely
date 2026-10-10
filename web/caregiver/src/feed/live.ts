import type { HubEvent } from '../types'

export interface LiveRow {
  id: string
  transcript: string
  action: 'comfort' | 'caregiver' | 'urgent' | 'silent' | 'dropped'
  tv: boolean
  at: number
}

export interface LiveFace {
  who: string | null
  score: number
  at: number
}

export interface LiveState {
  rows: LiveRow[]
  face: LiveFace | null
}

export const emptyLive: LiveState = { rows: [], face: null }

const ACTIONS = ['comfort', 'caregiver', 'urgent', 'silent'] as const

function isAction(value: unknown): value is (typeof ACTIONS)[number] {
  return typeof value === 'string' && (ACTIONS as readonly string[]).includes(value)
}

function text(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

function rowId(event: HubEvent, kind: string, at: number, n: number): string {
  const uid = event.utterance_id
  if (typeof uid === 'string' && uid.trim()) return `${kind}:${uid.trim()}`
  return `${kind}:${at}:${n}`
}

function push(state: LiveState, row: LiveRow): LiveState {
  return { ...state, rows: [row, ...state.rows].slice(0, 40) }
}

export function reduceLive(state: LiveState, event: HubEvent, at: number): LiveState {
  if (event.event === 'decided') {
    if (!isAction(event.action)) return state
    return push(state, {
      id: rowId(event, 'decided', at, state.rows.length),
      transcript: text(event.transcript),
      action: event.action,
      tv: event.ignored === 'tv',
      at,
    })
  }
  if (event.event === 'heard' && event.dropped === true) {
    return push(state, {
      id: rowId(event, 'heard', at, state.rows.length),
      transcript: text(event.transcript),
      action: 'dropped',
      tv: event.drop_reason === 'junk line',
      at,
    })
  }
  if (event.event === 'face_seen') {
    const who = text(event.who).trim()
    const score = typeof event.score === 'number' && Number.isFinite(event.score) ? event.score : 0
    return { ...state, face: { who: who ? who : null, score, at } }
  }
  return state
}
