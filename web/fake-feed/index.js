// V1 fake event feed. Lets /lola, /caregiver and /backstage build without the hub.
//
// It emits the exact /ws shapes from docs/sino/architecture.md (The 3 interfaces)
// and routes them per screen the same way brain/server.py does:
//   heard            -> backstage
//   decided          -> every screen (silent: backstage only)
//   play_reply       -> lola
//   alert            -> caregiver
//   ask_caregiver    -> caregiver
//   health           -> every screen, on connect and when a part changes
//
// Every decided payload below is real output of brain/decide.py in stub mode
// (SINO_MODEL=stub), copied on Sat Oct 10. latency_ms is the stub's own number,
// NOT a hub measurement. This feed is for building screens only. Never show it
// to judges as the real thing: check IS_FAKE and label the screen.
//
// Usage:
//   import { openFeed } from '../fake-feed/index.js'
//   const feed = openFeed('caregiver', (msg) => console.log(msg))
//   // add ?feed=hub to the page URL to use the real hub socket instead
//   feed.close()

export const IS_FAKE = true

const SCREENS = ['lola', 'caregiver', 'backstage']

const HEALTH_OK = {
  event: 'health', whisper: true, ollama: true, server: true, mic: true, offline: true,
  model: 'stub', last_event_at: '',
}

// Helper: one decide() result. Keys match the Decision interface exactly.
const d = (action, reply_id, reason, trigger_words, confidence, latency_ms, source, ignored = '') =>
  ({ action, reply_id, reason, trigger_words, confidence, latency_ms, source, ignored })

// The script. Each step is one utterance (or a health change). wait is ms before it fires.
export const SCRIPT = [
  { wait: 1500, text: 'Nasaan si Nanay?', decision: d('comfort', 'nasaan-si-nanay', 'known question', [], 1.0, 1, 'rule') },
  { wait: 4000, text: 'Abangan ang susunod na kabanata', decision: d('silent', '', 'television line', ['abangan', 'kabanata'], 1.0, 0, 'rule', 'tv') },
  { wait: 3000, text: 'Thank you for watching', dropped: 'junk line' },
  { wait: 3000, text: 'Kumain na ba ako?', decision: d('caregiver', '', 'model unavailable', [], 0.0, 0, 'model') },
  { wait: 3000, text: '', dropped: 'too quiet' },
  { wait: 3000, text: 'Sino ka?', decision: d('comfort', 'sino-ka', 'known question', [], 1.0, 0, 'rule'), who: 'joy' },
  { wait: 4000, text: 'Kumain na ba ako?', decision: d('caregiver', '', 'model unavailable', [], 0.0, 0, 'model') },
  { wait: 3000, text: 'Inumin ko na ba ang gamot?', decision: d('caregiver', '', 'medication', ['gamot'], 1.0, 0, 'rule') },
  { wait: 3000, health: { ollama: false } },
  { wait: 3000, text: 'Ang sakit ng loob ko', decision: d('caregiver', '', 'sakit ng loob idiom', ['sakit ng loob'], 1.0, 0, 'rule') },
  { wait: 2000, health: { ollama: true } },
  { wait: 3000, text: 'Gusto ko nang umuwi', decision: d('comfort', 'gusto-ko-nang-umuwi', 'known question', [], 1.0, 0, 'rule') },
  { wait: 4000, text: 'Masakit dibdib ko', decision: d('urgent', '', 'urgent word', ['masakit', 'masakit dibdib'], 1.0, 0, 'rule') },
  { wait: 5000, text: 'Nasaan yung aso?', decision: d('caregiver', '', 'model unavailable', [], 0.0, 0, 'model') },
  {
    wait: 3000,
    text: 'Kumain na ba ako?',
    decision: d('comfort', 'meal-check', 'known question', [], 1.0, 0, 'rule'),
    meal: { reply_variant: 'unknown', last_meal_ts: '' },
  },
  {
    wait: 2000,
    about: {
      intent: 'where',
      answer: 'Huling nakita sa recording: sala (clip 0:02).',
      source: 'rule',
      latency_ms: 1,
      snapshot: '/clips/snapshot',
      label: 'RECORDED CLIP · DEMO',
    },
  },
]

const MEAL_NOTE = "Lola asked if she's eaten. No meal logged."

// Turn one script step into [screen, payload] pairs, like brain/server.py publish().
// counts tracks repeats so grouped yellow cards get the right count.
export function expand(step, counts, health) {
  if (step.health) {
    Object.assign(health, step.health)
    return SCREENS.map((s) => [s, { ...health }])
  }
  if (step.about) return [['caregiver', { event: 'about_lola', ...step.about }]]
  const heard = { event: 'heard', transcript: step.text, dropped: !!step.dropped, drop_reason: step.dropped || '' }
  if (step.dropped) return [['backstage', heard]] // junk drop: no decide(), no other event
  const r = step.decision
  const decided = { event: 'decided', ...r, transcript: step.text }
  if (step.who) decided.who = step.who
  if (step.meal) {
    decided.reply_variant = step.meal.reply_variant
    decided.last_meal_ts = step.meal.last_meal_ts
  }
  const out = [['backstage', heard]]
  for (const s of r.action === 'silent' ? ['backstage'] : SCREENS) out.push([s, decided])
  if (r.action === 'comfort') {
    // reply_audio and photo are empty in brain/seed.json until the recordings land
    out.push(['lola', { event: 'play_reply', reply_id: r.reply_id, reply_audio: '', photo: '' }])
    if (step.meal?.reply_variant === 'unknown') {
      counts[MEAL_NOTE] = (counts[MEAL_NOTE] || 0) + 1
      out.push(['caregiver', { event: 'ask_caregiver', transcript: MEAL_NOTE, count: counts[MEAL_NOTE] }])
    }
  } else if (r.action === 'urgent') {
    out.push(['caregiver', { event: 'alert', transcript: step.text }])
  } else if (r.action === 'caregiver') {
    counts[step.text] = (counts[step.text] || 0) + 1
    out.push(['caregiver', { event: 'ask_caregiver', transcript: step.text, count: counts[step.text] }])
  }
  return out
}

// Play the script for one screen. Calls onEvent(payload) with each message for that screen.
// opts.speed: 2 plays twice as fast. opts.loop: start over at the end (default true).
export function openFakeFeed(screen, onEvent, { speed = 1, loop = true } = {}) {
  if (!SCREENS.includes(screen)) throw new Error(`unknown screen ${screen}`)
  let timer = null
  let i = 0
  let counts = {}
  let health = { ...HEALTH_OK }
  const emit = (p) => onEvent(JSON.parse(JSON.stringify(p))) // copy, so screens can't mutate the script

  const next = () => {
    if (i >= SCRIPT.length) {
      if (!loop) return
      i = 0
      counts = {}
    }
    const step = SCRIPT[i++]
    timer = setTimeout(() => {
      if (step.decision) health.last_event_at = new Date().toISOString().slice(0, 19)
      for (const [s, p] of expand(step, counts, health)) if (s === screen) emit(p)
      next()
    }, step.wait / speed)
  }

  timer = setTimeout(() => { emit(health); next() }, 0) // health first, like the hub on connect
  return {
    send() {}, // the fake feed ignores client messages (ask_about_lola is a Should item)
    close() { clearTimeout(timer); timer = null },
  }
}

// Same interface as openFakeFeed, but on the real hub socket.
export function openHubFeed(screen, onEvent, { url } = {}) {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const ws = new WebSocket(url || `${proto}//${location.host}/ws?screen=${screen}`)
  ws.onmessage = (e) => {
    try { onEvent(JSON.parse(e.data)) } catch { /* ignore a bad frame */ }
  }
  return {
    send(obj) { if (ws.readyState === 1) ws.send(JSON.stringify(obj)) },
    close() { ws.close() },
  }
}

// Default entry point. Fake unless the page URL has ?feed=hub.
export function openFeed(screen, onEvent, opts = {}) {
  const useHub = typeof location !== 'undefined' && new URLSearchParams(location.search).get('feed') === 'hub'
  return useHub ? openHubFeed(screen, onEvent, opts) : openFakeFeed(screen, onEvent, opts)
}
