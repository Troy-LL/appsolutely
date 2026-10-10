// Everything this screen needs from the hub.
// No backend code lives here: these only call what brain/server.py already serves.
import { useEffect, useRef } from 'react'
// V1 fake feed (web/fake-feed). Fake by default; add ?feed=hub to the URL for the real hub.
import { openFakeFeed } from '../../../fake-feed/index.js'
import { openCaregiverSocket, type LinkStatus } from '../feed/connect'
// The real seed file, used for "What Sino knows" while on the fake feed.
import seed from '../../../../brain/seed.json'
import type { HubEvent, MemberColor, Question } from '../types'
import { SAFETY_WORDS } from './safetyWords'

export const USING_HUB =
  typeof location !== 'undefined' && new URLSearchParams(location.search).get('feed') === 'hub'

// Subscribe to /ws as the "caregiver" screen. The callback always sees the latest props.
// Returns send(), used by Ask Sino about Lola and by "Kumain na". The fake feed ignores what is sent.
export function useFeed(
  onEvent: (e: HubEvent) => void,
  hooks?: { onStatus?: (status: LinkStatus) => void; onVisible?: () => void },
) {
  const cb = useRef(onEvent)
  cb.current = onEvent
  const hooksRef = useRef(hooks)
  hooksRef.current = hooks
  const feedRef = useRef<{ send(obj: unknown): void } | null>(null)
  useEffect(() => {
    const onMsg = (msg: HubEvent) => cb.current(msg)
    const feed = USING_HUB
      ? openCaregiverSocket(onMsg, {
          onStatus: (status) => hooksRef.current?.onStatus?.(status),
          onVisible: () => hooksRef.current?.onVisible?.(),
        })
      : openFakeFeed('caregiver', onMsg)
    feedRef.current = feed
    return () => { feedRef.current = null; feed.close() }
  }, [])
  return (obj: unknown) => feedRef.current?.send(obj)
}

// GET /questions. On the fake feed there is no hub, so we read brain/seed.json instead.
export async function loadQuestions(): Promise<Question[]> {
  if (!USING_HUB) return seed as Question[]
  const res = await fetch('/questions')
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return (await res.json()) as Question[]
}

// Ids that shipped in brain/seed.json. Those stay; only a question the family added can go.
export function isBuiltIn(id: string): boolean {
  return (seed as Question[]).some((q) => q.id === id)
}

// DELETE /questions/{id}. 404 means it is already gone. A built-in id throws the hub's error.
export async function deleteQuestion(id: string): Promise<void> {
  if (!USING_HUB) {
    if (isBuiltIn(id)) throw new Error('built-in questions stay')
    return
  }
  const res = await fetch(`/questions/${encodeURIComponent(id)}`, { method: 'DELETE' })
  if (res.ok || res.status === 404) return
  let why = `HTTP ${res.status}`
  try {
    const body = (await res.json()) as { error?: string }
    if (body.error) why = body.error
  } catch {
    /* keep the status code */
  }
  throw new Error(why)
}

// Turn Lola's words into an id the hub accepts (1-64 of a-z 0-9 -).
export function idFor(text: string): string {
  const id = text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64)
  return id || 'tanong'
}

// POST /questions as multipart (architecture.md, "POST /questions field encoding").
// One tap on a yellow card: Lola's words become a question, the recording its reply.
export async function saveReply(opts: { transcript: string; speaker: string; audio: Blob }): Promise<Question | 'fake'> {
  if (!USING_HUB) return 'fake'
  const ext = opts.audio.type.includes('mp4') ? 'm4a' : opts.audio.type.includes('ogg') ? 'ogg' : 'webm'
  const id = idFor(opts.transcript)
  const form = new FormData()
  form.append('id', id)
  form.append('question', opts.transcript.slice(0, 300))
  form.append('phrasings', opts.transcript.slice(0, 300))
  form.append('speaker', opts.speaker.slice(0, 60))
  form.append('reply_audio', opts.audio, `${id}-reply.${ext}`)
  const res = await fetch('/questions', { method: 'POST', body: form })
  if (!res.ok) {
    let why = `HTTP ${res.status}`
    try {
      const body = (await res.json()) as { error?: string }
      if (body.error) why = body.error
    } catch {
      /* keep the status code */
    }
    throw new Error(why)
  }
  return (await res.json()) as Question
}

export interface SafetyList {
  builtin: string[]
  custom: string[]
}

function asWords(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.filter((word): word is string => typeof word === 'string' && word.length > 0)
}

// GET /safety-words. Fake feed keeps the built-in copy; nothing is stored.
export async function loadSafetyWords(): Promise<SafetyList> {
  if (!USING_HUB) return { builtin: SAFETY_WORDS, custom: [] }
  const res = await fetch('/safety-words')
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const body = (await res.json()) as { builtin?: unknown; custom?: unknown }
  const builtin = asWords(body.builtin)
  return { builtin: builtin.length ? builtin : SAFETY_WORDS, custom: asWords(body.custom) }
}

// POST /safety-words. Returns the stored word, or 'fake' when this phone is not on the hub.
export async function addSafetyWord(word: string): Promise<{ word: string } | 'fake'> {
  if (!USING_HUB) return 'fake'
  const res = await fetch('/safety-words', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ word }),
  })
  if (!res.ok) {
    let why = `HTTP ${res.status}`
    try {
      const body = (await res.json()) as { error?: string }
      if (body.error) why = body.error
    } catch {
      /* keep the status code */
    }
    throw new Error(why)
  }
  return (await res.json()) as { word: string }
}

export interface FamilyMember {
  id: string
  name: string
  color: MemberColor
  photo: string
}

const COLORS: MemberColor[] = ['green', 'amber', 'red']

export function readMember(value: unknown): FamilyMember | null {
  if (!value || typeof value !== 'object') return null
  const row = value as Record<string, unknown>
  const name = typeof row.name === 'string' ? row.name.trim() : ''
  const id = typeof row.id === 'string' ? row.id : ''
  if (!name || !id) return null
  const color = COLORS.includes(row.color as MemberColor) ? (row.color as MemberColor) : 'green'
  const photo = typeof row.photo === 'string' ? row.photo : ''
  return { id, name, color, photo }
}

// GET /family. Fake feed has no hub file, so the wall keeps what this phone added.
export async function loadFamily(): Promise<FamilyMember[]> {
  if (!USING_HUB) return []
  const res = await fetch('/family')
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const body = (await res.json()) as { members?: unknown }
  if (!Array.isArray(body.members)) return []
  return body.members.map(readMember).filter((member): member is FamilyMember => member !== null)
}

function photoExt(file: File): string {
  const fromName = file.name.split('.').pop()?.toLowerCase() ?? ''
  if (fromName === 'jpeg' || fromName === 'jpg') return 'jpg'
  if (fromName === 'png' || fromName === 'webp' || fromName === 'heic') return fromName
  if (file.type === 'image/png') return 'png'
  if (file.type === 'image/webp') return 'webp'
  if (file.type === 'image/heic' || file.type === 'image/heif') return 'heic'
  return 'jpg'
}

// POST /family. Multipart name, color, and optional photo. Returns the stored member.
export async function addFamilyMember(opts: {
  name: string
  color: MemberColor
  photo?: File
}): Promise<FamilyMember | 'fake'> {
  if (!USING_HUB) return 'fake'
  const form = new FormData()
  form.append('name', opts.name.slice(0, 60))
  form.append('color', opts.color)
  if (opts.photo) form.append('photo', opts.photo, `photo.${photoExt(opts.photo)}`)
  const res = await fetch('/family', { method: 'POST', body: form })
  if (!res.ok) {
    let why = `HTTP ${res.status}`
    try {
      const body = (await res.json()) as { error?: string }
      if (body.error) why = body.error
    } catch {
      /* keep the status code */
    }
    throw new Error(why)
  }
  const member = readMember(await res.json())
  if (!member) throw new Error('bad member')
  return member
}

// DELETE /family/{id}. 404 means the frame is already gone.
export async function removeFamilyMember(id: string): Promise<void> {
  if (!USING_HUB) return
  const res = await fetch(`/family/${encodeURIComponent(id)}`, { method: 'DELETE' })
  if (res.ok || res.status === 404) return
  throw new Error(`HTTP ${res.status}`)
}

// POST /urgent-reply. A recorded voice on an urgent card; the hub stores it and tells Lola.
export async function postUrgentReply(opts: { text: string; speaker: string; audio: Blob }): Promise<void> {
  const ext = opts.audio.type.includes('mp4') ? 'm4a' : opts.audio.type.includes('ogg') ? 'ogg' : opts.audio.type.includes('wav') ? 'wav' : 'webm'
  const form = new FormData()
  form.append('text', opts.text.slice(0, 300))
  form.append('speaker', opts.speaker.slice(0, 60))
  form.append('reply_audio', opts.audio, `urgent-reply.${ext}`)
  const res = await fetch('/urgent-reply', { method: 'POST', body: form })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}
