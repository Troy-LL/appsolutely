// lola.js — Lola's wall. Plain ES module, no build step. States: Waiting
// (clock) -> Listening (ring) -> Answer (framed photo). One language at a time.
// Behavior: task spec; look: docs/sino/design-system.md.
// Options: ?lang=tl|en, ?big, ?time=17:15, ?hub=host:port, ?feed=hub, ?mic=off.
import { openFeed, IS_FAKE } from '../fake-feed/index.js'
import { STRINGS, LANGS, DEFAULT_LANG, LANG_NAMES, t, dayPartKey } from './strings.js'
import { startMic } from './mic.js'

// SAFETY (sound): never louder than MAX_VOLUME; clips fade in over FADE_IN_MS.
// TODO: decision D5 — the real volume is set together on the iPad at test time.
const MAX_VOLUME = 0.8
const FADE_IN_MS = 300
const AFTER_CLIP_MS = 1000 // after a family reply finishes, back to the clock this soon
const HOLD_MS = 8000 // no recording, or the iPad blocked the sound: keep the answer up so a tap can play it
const BACKOFF_MS = [500, 1000, 2000, 4000, 8000]
const SILENT_WAV = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YQAAAAA='
const params = new URLSearchParams(location.search)
const $ = (sel) => document.querySelector(sel)
if (params.has('big')) document.documentElement.classList.add('big')
const stage = { waiting: $('#waiting'), listening: $('#listening'), answer: $('#answer') }

const LANG_KEY = 'sino.lola.lang'
const readSaved = () => { try { return localStorage.getItem(LANG_KEY) } catch { return null } }
const savePick = (l) => { try { localStorage.setItem(LANG_KEY, l) } catch { /* storage off */ } }
let lang = [params.get('lang'), readSaved(), DEFAULT_LANG].find((l) => LANGS.includes(l)) || DEFAULT_LANG

function renderCopy() {
  document.documentElement.setAttribute('lang', lang)
  $('#waiting .reassure').textContent = t(STRINGS.waitingReassurance, lang)
  $('#listening .caption').textContent = t(STRINGS.listening, lang)
  $('#start-btn').textContent = t(STRINGS.start, lang)
  const help = $('#start-help')
  if (help) help.textContent = t(STRINGS.startHelp, lang)
  drawClock()
}

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
  const h12 = now.h % 12 === 0 ? 12 : now.h % 12
  $('#waiting .time').textContent = `${h12}:${String(now.min).padStart(2, '0')}`
  $('#waiting .daypart').textContent = t(STRINGS.dayParts[dayPartKey(now.h)], lang)
}

renderCopy()
if (!fixedTime()) {
  const toNextMinute = (60 - new Date().getSeconds()) * 1000
  setTimeout(function tick() { drawClock(); setInterval(drawClock, 60000) }, toNextMinute)
}

function show(name) {
  for (const key of Object.keys(stage)) {
    stage[key].classList.toggle('show', key === name)
    stage[key].setAttribute('aria-hidden', key === name ? 'false' : 'true')
  }
}
show('waiting')

const speakers = new Map()
const hubBase = () => (params.get('hub') ? `${location.protocol}//${params.get('hub')}` : '')
async function loadSpeakers() {
  try {
    const res = await fetch(`${hubBase()}/questions`)
    if (!res.ok) return
    for (const q of await res.json()) if (q && q.id) speakers.set(q.id, q.speaker || '')
  } catch { /* offline / not served */ }
}
loadSpeakers()

let current = null
let pending = null
let blocked = null
let hold = null
let reassuring = false
let replyKey = ''

// One audio element for every reply. iPadOS only plays sound from an element that was first
// played inside a tap, so the Simulan tap unlocks this one and every reply reuses it. A new
// Audio() made later, outside a tap, can stay silent (the answer showed but no voice played).
const player = new Audio()
player.preload = 'auto'
player.addEventListener('ended', clipDone)
player.addEventListener('error', clipDone)
let clipId = 0 // so a late answer from an older play() can't touch the current clip

function speakerName(msg) {
  if (typeof msg.speaker === 'string' && msg.speaker) return msg.speaker
  return speakers.get(msg.reply_id) || ''
}

function renderAnswer(msg) {
  const box = $('#answer .photo-box')
  const name = speakerName(msg)
  const url = msg.photo ? `${hubBase()}${msg.photo}` : ''
  $('#answer .reply').textContent = typeof msg.reply_text === 'string' ? msg.reply_text : ''

  if (url) {
    box.innerHTML = `<img alt="" />`
    const img = box.querySelector('img')
    img.onerror = () => showNameInFrame(box, name)
    img.src = url
    $('#answer .name').textContent = name
    $('#answer .name').style.display = ''
  } else {
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
  if (current && !current.ended) { pending = msg; return }
  startClip(msg)
}

function startClip(msg) {
  cancelHold()
  blocked = null
  reassuring = msg.event === 'urgent_reply'
  renderAnswer(msg)
  if (!msg.reply_audio) { current = null; afterClip(HOLD_MS); return }
  const id = ++clipId
  player.src = `${hubBase()}${msg.reply_audio}`
  player.volume = 0
  current = player
  player.play().then(() => { if (id === clipId) fadeIn(player) }).catch(() => {
    if (id !== clipId || current !== player) return
    current = null
    blocked = player
    afterClip(HOLD_MS)
  })
}

function clipDone() {
  if (current !== player && blocked !== player) return // e.g. the silent unlock clip ending
  blocked = null
  afterClip(AFTER_CLIP_MS)
}

function retryBlocked() {
  if (!blocked) return
  blocked = null
  current = player
  cancelHold()
  const id = clipId
  player.play().then(() => { if (id === clipId) fadeIn(player) }).catch(() => {
    // A finger tap fires pointerdown before the browser counts it as a tap, so play() can be
    // refused there. Keep the reply blocked so the click from the same tap can play it.
    if (id === clipId && current === player) { blocked = player; afterClip(HOLD_MS) }
  })
}
document.addEventListener('pointerdown', retryBlocked)
document.addEventListener('click', retryBlocked)

function fadeIn(audio) {
  const steps = 10
  let i = 0
  const timer = setInterval(() => {
    audio.volume = Math.min(MAX_VOLUME, (++i / steps) * MAX_VOLUME)
    if (i >= steps) clearInterval(timer)
  }, FADE_IN_MS / steps)
}

function afterClip(delay = AFTER_CLIP_MS) {
  current = null
  if (pending) { const next = pending; pending = null; startClip(next); return }
  cancelHold()
  hold = setTimeout(() => { hold = null; blocked = null; reassuring = false; show('waiting') }, delay)
}

function onEvent(msg) {
  if (!msg || typeof msg !== 'object') return
  switch (msg.event) {
    case 'heard':
      if (!msg.dropped) show('listening')
      break
    case 'play_reply':
      playReply(msg)
      break
    case 'urgent_reply': {
      const text = typeof msg.text === 'string' ? msg.text : ''
      const speaker = typeof msg.speaker === 'string' ? msg.speaker : ''
      const audio = typeof msg.reply_audio === 'string' ? msg.reply_audio : ''
      const key = `${speaker}\0${text}\0${audio}`
      if (key === replyKey && reassuring) break
      replyKey = key
      playReply({ event: 'urgent_reply', reply_audio: audio, photo: '', speaker, reply_text: text })
      break
    }
    case 'decided':
      if (reassuring) break
      if (msg.action !== 'comfort' && !current && !pending) {
        cancelHold()
        blocked = null
        show('waiting')
      }
      break
  }
}

const ON_HUB = params.get('feed') === 'hub'
let feed = null
let feedOpen = false
let feedGen = 0
let attempt = 0
let retry = null

function connect() {
  clearTimeout(retry)
  retry = null
  const state = feed && feed.readyState
  if (state === 0 || state === 1) return
  if (feed) { try { feed.close() } catch { /* already closed */ } }
  feed = null
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
  if (status === 'open') {
    clearTimeout(retry)
    retry = null
    feedOpen = true
    attempt = 0
    return
  }
  if (status !== 'closed') return
  feedOpen = false
  scheduleReconnect()
}

function scheduleReconnect() {
  if (retry) return
  const wait = BACKOFF_MS[Math.min(attempt, BACKOFF_MS.length - 1)]
  attempt++
  retry = setTimeout(connect, wait)
}

async function keepAwake() {
  try { if (navigator.wakeLock) await navigator.wakeLock.request('screen') } catch {}
}

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState !== 'visible') return
  keepAwake()
  if (ON_HUB && !params.has('test') && !feedOpen) connect()
})

if (params.has('test')) {
  window.__lola = { send: onEvent, show }
} else {
  connect()
}

const langButtons = [...document.querySelectorAll('.lang-btn')]
const markLang = () => langButtons.forEach((b) => b.setAttribute('aria-pressed', b.dataset.lang === lang ? 'true' : 'false'))
for (const b of langButtons) {
  b.textContent = LANG_NAMES[b.dataset.lang] || b.dataset.lang
  b.addEventListener('click', () => { lang = b.dataset.lang; savePick(lang); markLang(); renderCopy() })
}
markLang()

let audioCtx = null
$('#start-btn').addEventListener('click', () => {
  $('#start-sheet').classList.add('gone')
  // Unlock the reply player inside this tap (iPadOS rule) by playing a silent clip on it.
  if (!current) { player.src = SILENT_WAV; player.play().catch(() => {}) }
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext
    if (Ctx) {
      audioCtx = audioCtx || new Ctx()
      audioCtx.resume().catch(() => {})
    }
  } catch {}
  keepAwake()
  // The iPad listens (real hub only, mic.js). The mic prompt must come from this tap.
  // isPlaying: a family reply is playing, so the mic must not send it to the hub.
  if (ON_HUB && params.get('mic') !== 'off') {
    startMic({ ctx: audioCtx, hubBase, isPlaying: () => !!current && !current.paused })
  }
})

if (IS_FAKE && !ON_HUB) {
  const el = $('#fake-label'); el.textContent = t(STRINGS.fake, lang); el.classList.remove('hidden')
}
