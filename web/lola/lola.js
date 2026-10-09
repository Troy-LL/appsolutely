// lola.js — Lola's wall. Plain ES module, no build step. States: Waiting
// (clock) -> Listening (ring) -> Answer (framed photo). Events from the fake
// feed, or the real hub with ?feed=hub. Behavior: task spec; look:
// docs/sino/design-system.md. Options: ?big, ?time=17:15, ?hub=host:port, ?feed=hub.
import { openFeed, IS_FAKE } from '../fake-feed/index.js'
import { STRINGS, pair, dayPartKey } from './strings.js'

// SAFETY (sound): never louder than MAX_VOLUME; clips fade in over FADE_IN_MS.
// TODO: decision D5 — the real volume is set together on the iPad at test time.
const MAX_VOLUME = 0.8
const FADE_IN_MS = 300
const HOLD_MS = 8000
const BACKOFF_MS = [500, 1000, 2000, 4000, 8000]
const SILENT_WAV = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YQAAAAA='
const params = new URLSearchParams(location.search)
const $ = (sel) => document.querySelector(sel)
if (params.has('big')) document.documentElement.classList.add('big') // bigger type
const stage = { waiting: $('#waiting'), listening: $('#listening'), answer: $('#answer') }

// ---- Clock: flat ink SVG, hands redrawn once a minute (?time freezes it) ----
function fixedTime() {
  const raw = params.get('time')
  if (!raw) return null
  const m = /^(\d{1,2}):(\d{2})$/.exec(raw)
  if (!m) return null
  const h = +m[1], min = +m[2]
  if (h > 23 || min > 59) return null
  return { h, min }
}

function drawClock() {
  const svg = $('#waiting .clock')
  const d = new Date()
  const now = fixedTime() || { h: d.getHours(), min: d.getMinutes() }
  // Hand angles. 12 o'clock is straight up (-90deg from the x-axis).
  const minA = (now.min / 60) * 360 - 90
  const hourA = (((now.h % 12) + now.min / 60) / 12) * 360 - 90
  const hand = (deg, len, w) => {
    const r = (deg * Math.PI) / 180
    const x = 50 + len * Math.cos(r), y = 50 + len * Math.sin(r)
    return `<line x1="50" y1="50" x2="${x.toFixed(2)}" y2="${y.toFixed(2)}" stroke="#2b2420" stroke-width="${w}" stroke-linecap="round"/>`
  }
  svg.innerHTML =
    `<circle cx="50" cy="50" r="46" fill="none" stroke="#2b2420" stroke-width="3"/>` +
    hand(hourA, 24, 5) + hand(minA, 36, 3) +
    `<circle cx="50" cy="50" r="3" fill="#2b2420"/>`

  // Time text, e.g. "5:15" (12-hour, no leading zero, no AM/PM word).
  const h12 = now.h % 12 === 0 ? 12 : now.h % 12
  $('#waiting .time').textContent = `${h12}:${String(now.min).padStart(2, '0')}`
  // Day-part pair from strings.js, keyed by the 24-hour hour.
  $('#waiting .daypart').textContent = pair(STRINGS.dayParts[dayPartKey(now.h)])
}

// Fill the fixed waiting/listening copy from strings.js.
$('#waiting .reassure').textContent = pair(STRINGS.waitingReassurance)
$('#listening .caption').textContent = pair(STRINGS.listening)
// Redraw the clock now, then at the top of each minute (unless frozen).
drawClock()
if (!fixedTime()) {
  const toNextMinute = (60 - new Date().getSeconds()) * 1000
  setTimeout(function tick() { drawClock(); setInterval(drawClock, 60000) }, toNextMinute)
}

// ---- State switching: one object on the wall at a time ----
function show(name) {
  for (const key of Object.keys(stage)) {
    stage[key].classList.toggle('show', key === name)
    stage[key].setAttribute('aria-hidden', key === name ? 'false' : 'true')
  }
}
show('waiting') // start on the clock

// ---- Speaker names from GET /questions (reply_id -> speaker), loaded once ----
const speakers = new Map()
const hubBase = () => (params.get('hub') ? `${location.protocol}//${params.get('hub')}` : '')
async function loadSpeakers() {
  try {
    const res = await fetch(`${hubBase()}/questions`)
    if (!res.ok) return
    for (const q of await res.json()) if (q && q.id) speakers.set(q.id, q.speaker || '')
  } catch { /* offline / not served: leave the map empty, show nothing extra */ }
}
loadSpeakers()

// ---- Audio queue: one clip at a time; a new reply mid-clip waits its turn ----
let current = null // the <audio> playing now
let pending = null // the newest answer waiting its turn
let blocked = null // a clip whose play() was refused, retried on the next tap
let hold = null

function speakerName(msg) {
  if (typeof msg.speaker === 'string' && msg.speaker) return msg.speaker
  return speakers.get(msg.reply_id) || ''
}

function renderAnswer(msg) {
  const box = $('#answer .photo-box')
  const name = speakerName(msg)
  const url = msg.photo ? `${hubBase()}${msg.photo}` : ''
  // TODO: reply_text is not in the /ws contract (architecture.md). We read an
  // optional field and show nothing if it is absent. Do not invent a line.
  $('#answer .reply').textContent = typeof msg.reply_text === 'string' ? msg.reply_text : ''

  if (url) {
    // Photo path: show the image; name goes on the plate under the frame.
    box.innerHTML = `<img alt="" />`
    const img = box.querySelector('img')
    img.onerror = () => showNameInFrame(box, name) // broken image -> name in frame
    img.src = url
    $('#answer .name').textContent = name
    $('#answer .name').style.display = ''
  } else {
    // No photo: the name sits inside the empty frame; no plate underneath.
    showNameInFrame(box, name)
  }
  show('answer')
}

function showNameInFrame(box, name) {
  box.innerHTML = `<div class="fallback-name"></div>`
  box.querySelector('.fallback-name').textContent = name
  $('#answer .name').textContent = ''
  $('#answer .name').style.display = 'none'
}

function cancelHold() {
  clearTimeout(hold)
  hold = null
}

function playReply(msg) {
  cancelHold()
  // Always finish a clip in progress; stash the newest answer for after it.
  if (current && !current.ended) { pending = msg; return }
  startClip(msg)
}

function startClip(msg) {
  cancelHold()
  blocked = null
  renderAnswer(msg) // show the picture as its clip begins
  if (!msg.reply_audio) { current = null; afterClip(); return }
  const audio = new Audio(`${hubBase()}${msg.reply_audio}`)
  audio.volume = 0
  current = audio
  audio.addEventListener('ended', () => clipDone(audio))
  audio.addEventListener('error', () => clipDone(audio))
  audio.play().then(() => fadeIn(audio)).catch(() => {
    if (current !== audio) return
    current = null
    blocked = audio
    afterClip()
  })
}

function clipDone(audio) {
  if (audio !== current && audio !== blocked) return
  blocked = null
  afterClip()
}

function retryBlocked() {
  if (!blocked) return
  const audio = blocked
  blocked = null
  current = audio
  cancelHold()
  audio.play().then(() => fadeIn(audio)).catch(() => { if (current === audio) afterClip() })
}
document.addEventListener('pointerdown', retryBlocked)
document.addEventListener('click', retryBlocked)

function fadeIn(audio) {
  const steps = 10
  let i = 0
  const t = setInterval(() => {
    audio.volume = Math.min(MAX_VOLUME, (++i / steps) * MAX_VOLUME)
    if (i >= steps) clearInterval(t)
  }, FADE_IN_MS / steps)
}

function afterClip() {
  current = null
  if (pending) { const next = pending; pending = null; startClip(next); return }
  cancelHold()
  hold = setTimeout(() => { hold = null; blocked = null; show('waiting') }, HOLD_MS)
}

// ---- Event handling ----
function onEvent(msg) {
  if (!msg || typeof msg !== 'object') return
  switch (msg.event) {
    case 'heard':
      // A real heard (dropped false) means Lola is being listened to.
      // TODO contract gap: the hub routes `heard` to backstage only, so lola
      // never receives it today. Handled here so Listening works if that changes.
      if (!msg.dropped) show('listening')
      break
    case 'play_reply':
      playReply(msg)
      break
    case 'decided':
      // comfort brings its own play_reply (above). Any other action with no
      // answer returns Lola to Waiting (no text, urgent included). Never
      // interrupt a clip to do so.
      if (msg.action !== 'comfort' && !current && !pending) {
        cancelHold()
        blocked = null
        show('waiting')
      }
      break
    // health and anything else: nothing for Lola to see.
  }
}

// ---- Connect: reconnect only after the hub socket closes or errors ----
const ON_HUB = params.get('feed') === 'hub'
let feed = null
let feedOpen = false
let feedGen = 0
let attempt = 0
let retry = null

function connect() {
  clearTimeout(retry)
  retry = null
  if (feed && !feedOpen) { try { feed.close() } catch {} }
  feedOpen = false
  const gen = ++feedGen
  const onStatus = (status) => { if (gen === feedGen) feedStatus(status) }
  try {
    feed = openFeed('lola', onEvent, {
      url: params.get('hub') ? `${hubBase().replace(/^http/, 'ws')}/ws?screen=lola` : undefined,
      onStatus,
    })
  } catch { scheduleReconnect() }
}

function feedStatus(status) {
  if (status === 'open') { feedOpen = true; attempt = 0; return }
  feedOpen = false
  scheduleReconnect()
}

function scheduleReconnect() {
  if (retry) return
  const wait = BACKOFF_MS[Math.min(attempt, BACKOFF_MS.length - 1)]
  attempt++
  retry = setTimeout(connect, wait)
}

// ---- Screen wake lock (Safari 16.4+); every failure stays silent ----
async function keepAwake() {
  try { if (navigator.wakeLock) await navigator.wakeLock.request('screen') } catch {}
}

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState !== 'visible') return
  keepAwake()
  if (ON_HUB && !params.has('test') && !feedOpen) connect()
})

// ?test exposes a seam that pushes synthetic events through the REAL onEvent,
// so screenshot tests exercise the same handlers Lola's screen uses. In test
// mode the auto feed is suppressed so injected events are deterministic.
if (params.has('test')) {
  window.__lola = { send: onEvent, show }
} else {
  connect()
}

// ---- Start sheet + FAKE label ----
let audioCtx = null
$('#start-btn').textContent = pair(STRINGS.start)
$('#start-btn').addEventListener('click', () => {
  $('#start-sheet').classList.add('gone') // fades away; it is the only button
  // iOS Safari unlocks media playback only inside a user tap.
  new Audio(SILENT_WAV).play().catch(() => {})
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext
    if (Ctx) {
      audioCtx = audioCtx || new Ctx()
      audioCtx.resume().catch(() => {})
    }
  } catch {}
  keepAwake()
})

// FAKE label: ink on paper, shown only while the practice feed is active.
if (IS_FAKE && !ON_HUB) {
  const el = $('#fake-label'); el.textContent = STRINGS.fake.tl; el.classList.remove('hidden')
}
