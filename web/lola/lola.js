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

function renderAnswer(msg) {
  const box = $('#answer .photo-box')
  const name = speakers.get(msg.reply_id) || ''
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

function playReply(msg) {
  // Always finish a clip in progress; stash the newest answer for after it.
  if (current && !current.ended) { pending = msg; return }
  startClip(msg)
}

function startClip(msg) {
  renderAnswer(msg) // show the picture as its clip begins
  if (!msg.reply_audio) { current = null; afterClip(); return }
  const audio = new Audio(`${hubBase()}${msg.reply_audio}`)
  audio.volume = 0
  current = audio
  audio.addEventListener('ended', afterClip)
  audio.addEventListener('error', afterClip)
  audio.play().then(() => fadeIn(audio)).catch(() => { current = null }) // autoplay may need the Start tap
}

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
  if (pending) { const next = pending; pending = null; startClip(next) }
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
      if (msg.action !== 'comfort' && !current && !pending) show('waiting')
      break
    // health and anything else: nothing for Lola to see.
  }
}

// ---- Connect (quiet reconnect every 3s) ----
let feed = null
function connect() {
  try {
    feed = openFeed('lola', onEvent, { url: hubBase() ? `${hubBase().replace(/^http/, 'ws')}/ws?screen=lola` : undefined })
  } catch { /* keep trying quietly */ }
}
// ?test exposes a seam that pushes synthetic events through the REAL onEvent,
// so screenshot tests exercise the same handlers Lola's screen uses. In test
// mode the auto feed is suppressed so injected events are deterministic.
if (params.has('test')) {
  window.__lola = { send: onEvent, show }
} else {
  connect()
  // Quietly remake the real socket every 3s if it drops (only ?feed=hub drops).
  setInterval(() => {
    if (params.get('feed') === 'hub') { try { feed && feed.close() } catch {} ; connect() }
  }, 3000)
}

// ---- Start sheet + FAKE label ----
$('#start-btn').textContent = pair(STRINGS.start)
$('#start-btn').addEventListener('click', () => {
  $('#start-sheet').classList.add('gone') // fades away; it is the only button
  new Audio().play().catch(() => {})      // a silent play unlocks iOS audio
})

// FAKE label: ink on paper, shown only while the practice feed is active.
if (IS_FAKE && params.get('feed') !== 'hub') {
  const el = $('#fake-label'); el.textContent = STRINGS.fake.tl; el.classList.remove('hidden')
}
