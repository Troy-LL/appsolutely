// Everything this screen needs from the hub, behind three small functions.
// No backend code lives here: these only call what brain/server.py already serves.
import { useEffect, useRef } from 'react'
// V1 fake feed (web/fake-feed). Fake by default; add ?feed=hub to the URL for the real hub.
import { openFakeFeed } from '../../../fake-feed/index.js'
import { openCaregiverSocket, type LinkStatus } from '../feed/connect'
// The real seed file, used for "What Sino knows" while on the fake feed.
import seed from '../../../../brain/seed.json'
import type { HubEvent, Question } from '../types'

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
