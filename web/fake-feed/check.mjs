// Plays the whole fake feed fast and checks it against the /ws contract.
//   node web/fake-feed/check.mjs
import { openFakeFeed, SCRIPT } from './index.js'

const KEYS = {
  heard: ['event', 'transcript', 'dropped', 'drop_reason'],
  decided: ['event', 'action', 'reply_id', 'reason', 'trigger_words', 'confidence', 'latency_ms', 'source', 'ignored', 'transcript'],
  play_reply: ['event', 'reply_id', 'reply_audio', 'photo', 'speaker'],
  alert: ['event', 'transcript'],
  ask_caregiver: ['event', 'transcript', 'count'],
  health: ['event', 'whisper', 'ollama', 'server', 'mic', 'offline', 'model', 'last_event_at'],
  about_lola: ['event', 'intent', 'answer', 'source', 'latency_ms', 'snapshot', 'label'],
}
const EXTRA = {
  decided: ['who', 'reply_variant', 'last_meal_ts'],
  alert: ['kind'],
}
const ALLOWED = {
  lola: ['health', 'decided', 'play_reply'],
  caregiver: ['health', 'decided', 'alert', 'ask_caregiver', 'about_lola'],
  backstage: ['health', 'heard', 'decided'],
}

function keysOk(msg) {
  const want = KEYS[msg.event]
  if (!want) return false
  const got = Object.keys(msg)
  const extra = EXTRA[msg.event] || []
  const unknown = got.filter((k) => !want.includes(k) && !extra.includes(k))
  if (unknown.length) return false
  return want.every((k) => got.includes(k))
}

const total = SCRIPT.reduce((n, s) => n + s.wait, 0)
const got = { lola: [], caregiver: [], backstage: [] }
const feeds = Object.keys(got).map((s) => openFakeFeed(s, (m) => got[s].push(m), { speed: 1000, loop: false }))
await new Promise((r) => setTimeout(r, total / 1000 + 200))
feeds.forEach((f) => f.close())

let bad = 0
const fail = (msg) => { bad++; console.log('FAIL', msg) }
for (const [screen, msgs] of Object.entries(got)) {
  if (msgs[0]?.event !== 'health') fail(`${screen}: first message is not health`)
  for (const m of msgs) {
    if (!ALLOWED[screen].includes(m.event)) fail(`${screen} got ${m.event}`)
    if (!keysOk(m)) fail(`${screen} ${m.event} keys ${Object.keys(m).join()}`)
    if (m.event === 'decided' && m.action === 'silent' && screen !== 'backstage') fail(`${screen} got a silent decided`)
  }
}
// TV lines ignored: N, counted the way architecture.md says
const b = got.backstage
const tv = b.filter((m) => (m.event === 'heard' && m.drop_reason === 'junk line') || (m.event === 'decided' && m.ignored === 'tv')).length
const counts = got.caregiver.filter((m) => m.event === 'ask_caregiver').map((m) => `${m.transcript} x${m.count}`)
console.log(`lola ${got.lola.length}, caregiver ${got.caregiver.length}, backstage ${b.length} messages`)
console.log(`TV lines ignored: ${tv}`)
console.log(`yellow cards: ${counts.join(' | ')}`)
if (tv !== 2) fail(`expected TV lines ignored: 2, got ${tv}`)
const mealCard = got.caregiver.some((m) => m.event === 'ask_caregiver' && m.transcript === "Lola asked if she's eaten. No meal logged.")
const mealDecided = got.caregiver.some((m) => m.event === 'decided' && m.reply_id === 'meal-check' && m.reply_variant === 'unknown' && m.last_meal_ts === '')
const about = got.caregiver.find((m) => m.event === 'about_lola')
if (!mealCard) fail('missing meal card')
if (!mealDecided) fail('missing meal decided')
if (!about || about.snapshot !== '/clips/snapshot' || about.label !== 'RECORDED CLIP · DEMO') fail('missing about_lola snapshot')
if (about && (got.lola.some((m) => m.event === 'about_lola') || got.backstage.some((m) => m.event === 'about_lola'))) fail('about_lola left the caregiver')
if (!got.caregiver.some((m) => m.event === 'decided' && m.who === 'joy')) fail('missing decided.who')
if (bad) process.exit(1)
console.log('ok')
