const NANAY = 'Nasaan si Nanay?'
const TV_LINE = 'Nasaan si Nanay? Abangan sa susunod na kabanata!'
const MEAL = 'Kumain na ba ako?'
const URGENT = 'Hirap huminga ako.'
const REPLY = 'Papunta na ako'

const $ = (id) => document.getElementById(id)
const frames = {
  lola: $('frame-lola'),
  caregiver: $('frame-caregiver'),
  backstage: $('frame-backstage'),
}
const views = {
  lola: $('view-lola'),
  caregiver: $('view-caregiver'),
  backstage: $('view-backstage'),
}

let sid = ''
let reloadToken = ''
let socket = null
let outbox = []
let replyWhenAlert = false
let replied = false
let index = -1
let busy = false
let skipped = false

const steps = [
  {
    kicker: '1 of 5',
    copy: 'Lola asks where Mother is. Watch her screen. Tap it once if you want the voice.',
    frame: 'lola',
    async run() { await postListen(NANAY) },
  },
  {
    kicker: '2 of 5',
    copy: 'A television line. Sino stays quiet. Watch backstage.',
    frame: 'backstage',
    async run() { await postListen(TV_LINE) },
  },
  {
    kicker: '3 of 5',
    copy: 'The caregiver logs the meal, then Lola asks if she has eaten.',
    frame: 'caregiver',
    async run() {
      highlight('caregiver')
      sendCaregiver({ event: 'meal_logged' })
      // The hub appends meal_logged on this socket before decide() reads the log.
      await wait(400)
      if (skipped) return
      highlight('lola')
      await postListen(MEAL)
    },
  },
  {
    kicker: '4 of 5',
    copy: 'Lola says she is having trouble breathing. The phone answers, Papunta na ako.',
    frame: 'caregiver',
    async run() {
      replyWhenAlert = true
      await postListen(URGENT)
    },
  },
  {
    kicker: '5 of 5',
    copy: 'Ask Sino how Lola is. The answer is today’s log, not a diagnosis.',
    frame: 'caregiver',
    async run() {
      sendCaregiver({ event: 'ask_about_lola', question: 'Kamusta si Lola?' })
    },
  },
]

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function frameSrc(path) {
  let url = `${path}?feed=hub&demo=1&mic=off`
  if (sid) url += `&sid=${encodeURIComponent(sid)}`
  if (reloadToken) url += `&reload=${reloadToken}`
  return url
}

function applyFrames() {
  views.lola.src = frameSrc('/lola/')
  views.caregiver.src = frameSrc('/caregiver/')
  views.backstage.src = frameSrc('/backstage/')
}

function highlight(name) {
  for (const key of Object.keys(frames)) frames[key].classList.toggle('is-on', key === name)
  const el = frames[name]
  if (!el) return
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  el.scrollIntoView({ block: 'nearest', behavior: motion ? 'auto' : 'smooth' })
}

function clearHighlight() {
  for (const el of Object.values(frames)) el.classList.remove('is-on')
}

function showStep(step) {
  $('tour').hidden = false
  $('tour-kicker').textContent = step.kicker
  $('tour-copy').textContent = step.copy
  $('tour-status').textContent = ''
  $('tour-next').textContent = index === steps.length - 1 ? 'Done' : 'Next'
}

function closeTour() {
  skipped = true
  $('tour').hidden = true
  clearHighlight()
}

async function postListen(text) {
  try {
    const res = await fetch('/listen', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: 'typed', text }),
    })
    if (res.status !== 202) {
      $('tour-status').textContent = 'The hub did not take that.'
      return false
    }
    return true
  } catch {
    $('tour-status').textContent = 'The hub did not take that.'
    return false
  }
}

function socketUrl() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const extra = sid ? `&sid=${encodeURIComponent(sid)}` : ''
  return `${proto}//${location.host}/ws?screen=caregiver${extra}`
}

function flush() {
  if (!socket || socket.readyState !== WebSocket.OPEN) return
  for (const raw of outbox) socket.send(raw)
  outbox = []
}

function onHub(raw) {
  let msg
  try { msg = JSON.parse(raw) } catch { return }
  if (!msg || typeof msg !== 'object') return
  if (msg.event === 'alert' && replyWhenAlert && !replied) {
    replied = true
    sendCaregiver({ event: 'urgent_reply', text: REPLY, speaker: 'Joy', reply_audio: '' })
  }
  if (msg.event === 'about_lola' && index === 4 && typeof msg.answer === 'string' && msg.answer) {
    $('tour-status').textContent = msg.answer
  }
}

function openSocket() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return
  const next = new WebSocket(socketUrl())
  socket = next
  next.onopen = () => { if (socket === next) flush() }
  next.onmessage = (e) => { if (socket === next) onHub(String(e.data)) }
  next.onclose = () => { if (socket === next) socket = null }
}

function sendCaregiver(obj) {
  const raw = JSON.stringify(obj)
  openSocket()
  if (socket && socket.readyState === WebSocket.OPEN) socket.send(raw)
  else outbox.push(raw)
}

async function go(nextIndex) {
  if (busy) return
  if (nextIndex >= steps.length) {
    closeTour()
    return
  }
  busy = true
  skipped = false
  index = nextIndex
  const step = steps[index]
  showStep(step)
  highlight(step.frame)
  try { await step.run() } catch { /* the status line names a failed post */ }
  busy = false
}

function whenLoaded(frame) {
  return new Promise((resolve) => {
    let settled = false
    const done = () => {
      if (settled) return
      settled = true
      resolve()
    }
    frame.addEventListener('load', done, { once: true })
    try {
      if (frame.contentDocument && frame.contentDocument.readyState === 'complete') done()
    } catch { /* the load event still fires */ }
  })
}

async function readSid() {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), 2000)
  try {
    const res = await fetch('/demo/state', { credentials: 'same-origin', signal: ctrl.signal })
    if (!res.ok) return ''
    const body = await res.json()
    return body && typeof body.sid === 'string' ? body.sid : ''
  } catch {
    return ''
  } finally {
    clearTimeout(timer)
  }
}

$('tour-next').addEventListener('click', () => { void go(index + 1) })
$('tour-skip').addEventListener('click', closeTour)
$('start-tour').addEventListener('click', () => { void go(0) })

$('reset').addEventListener('click', async () => {
  try {
    await fetch('/demo/reset', { method: 'POST', credentials: 'same-origin' })
  } catch { /* reload the frames either way */ }
  replyWhenAlert = false
  replied = false
  reloadToken = String(Date.now())
  applyFrames()
})

function nextLoad(frame) {
  return new Promise((resolve) => {
    frame.addEventListener('load', () => resolve(), { once: true })
  })
}

sid = await readSid()
openSocket()
if (sid) {
  const loads = Object.values(views).map(nextLoad)
  applyFrames()
  await Promise.all(loads)
} else {
  await Promise.all(Object.values(views).map(whenLoaded))
}
// Each iframe opens its own /ws after the document loads.
await wait(700)
if (new URLSearchParams(location.search).get('tour') === '1') void go(0)
