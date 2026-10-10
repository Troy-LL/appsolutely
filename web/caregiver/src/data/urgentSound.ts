// The urgent alarm on the caregiver phone. The red alert is the only thing on this
// phone that makes a sound (architecture.md "alert"; design system "Sound"). It is made
// with Web Audio, so there is no audio file to ship. Browsers only allow sound after a
// tap on the page: "Turn on alerts" (feed/monitor.ts) unlocks it, and so does the first
// tap anywhere on the page.

let ctx: AudioContext | null = null

export function unlockAudio() {
  if (!ctx) ctx = new AudioContext()
  void ctx.resume()
  const buffer = ctx.createBuffer(1, 1, 22050)
  const source = ctx.createBufferSource()
  source.buffer = buffer
  source.connect(ctx.destination)
  source.start()
}

if (typeof window !== 'undefined') window.addEventListener('pointerdown', unlockAudio, { once: true })

// True when the alarm can make a sound right now.
export const audioRunning = () => ctx?.state === 'running'

// After the phone was locked, or a call took the sound, the audio can be paused.
// Try to start it again, waiting at most 1 second. True when the alarm can sound.
export async function resumeAudio(): Promise<boolean> {
  if (!ctx) return false
  await Promise.race([ctx.resume().catch(() => undefined), new Promise((done) => window.setTimeout(done, 1000))])
  return ctx.state === 'running'
}

// iPhone: Web Audio is muted by the ring/silent switch unless the page asks for
// "playback" sound (Safari's Audio Session API, navigator.audioSession, newer iOS).
// Where Safari does not have it, the silent switch still mutes the alarm.
// One rule: "playback" once alerts are on or while the alarm rings, except while a
// recording has the mic ("auto" then, so the recording is not affected). The alarm
// also skips its beeps while the mic is on, so a voice reply does not record the alarm.
type WithAudioSession = Navigator & { audioSession?: { type: string } }
let ringOnSilent = false // set by "Turn on alerts"
let micUsers = 0 // recorders holding the mic right now (data/recorder.ts)

function applySoundMode() {
  const session = typeof navigator === 'undefined' ? undefined : (navigator as WithAudioSession).audioSession
  if (!session) return
  try {
    session.type = (ringOnSilent || alarmRinging()) && micUsers === 0 ? 'playback' : 'auto'
  } catch {
    /* not allowed here: keep the default */
  }
}

export function ringEvenOnSilent() {
  ringOnSilent = true
  applySoundMode()
}

// Each recorder calls this once with true when it opens the mic and once with false after.
export function setMicInUse(on: boolean) {
  micUsers = Math.max(0, micUsers + (on ? 1 : -1))
  applySoundMode()
}

// The alarm: a high tone then a low tone, once a second. Square waves sound much louder
// than the old soft sine "ding" at the same level.
export const ALARM_EVERY_MS = 1000
export const ALARM_MAX_MS = 2 * 60 * 1000 // safety cap: the sound stops by itself after 2 minutes
const HIGH_HZ = 1400
const LOW_HZ = 1050
const TONE_S = 0.4 // each tone lasts 0.4 s; the low one starts at 0.45 s, so they never overlap
// 0.8 is loud but under 1.0, where sound clips. Rendered offline in desktop Chrome
// (Sat Oct 10) one beep peaked at 0.79; on the iPhone it is to verify.
export const ALARM_GAIN = 0.8

// Schedules one high-low beep starting at time t. Works on any audio context, also an
// OfflineAudioContext, which lets us measure the loudest sample without playing it.
export function scheduleBeep(ac: BaseAudioContext, t: number): OscillatorNode[] {
  return [HIGH_HZ, LOW_HZ].map((hz, i) => {
    const start = t + i * 0.45
    const osc = ac.createOscillator()
    const gain = ac.createGain()
    osc.type = 'square'
    osc.frequency.value = hz
    // 10 ms fade in and out, so the tone starts and stops without a click
    gain.gain.setValueAtTime(0, start)
    gain.gain.linearRampToValueAtTime(ALARM_GAIN, start + 0.01)
    gain.gain.setValueAtTime(ALARM_GAIN, start + TONE_S - 0.01)
    gain.gain.linearRampToValueAtTime(0, start + TONE_S)
    osc.connect(gain).connect(ac.destination)
    osc.start(start)
    osc.stop(start + TONE_S + 0.01)
    return osc
  })
}

let ringTimer = 0 // the once-a-second timer; 0 when the alarm is quiet
let capTimer = 0 // the 2-minute safety cap
let playing: OscillatorNode[] = [] // the beep in flight, so "On my way" can cut it short

function beep() {
  if (!ctx || micUsers > 0) return // sound never unlocked on this page, or a voice reply is recording
  if (ctx.state !== 'running') {
    void ctx.resume().catch(() => undefined) // paused: try to wake it, beep again next second
    return
  }
  playing = scheduleBeep(ctx, ctx.currentTime + 0.02)
}

// Ring until stopAlarm(). If it is already ringing, do nothing, so a second alert never
// starts a second alarm on top. After ALARM_MAX_MS it stops by itself and calls onMax().
export function startAlarm(onMax: () => void) {
  if (ringTimer) return
  ringTimer = window.setInterval(beep, ALARM_EVERY_MS)
  capTimer = window.setTimeout(() => {
    stopAlarm()
    onMax()
  }, ALARM_MAX_MS)
  applySoundMode()
  beep()
}

// Stops the sound at once (also the beep already playing). The one stop for the alarm.
export function stopAlarm() {
  if (!ringTimer) return
  window.clearInterval(ringTimer)
  window.clearTimeout(capTimer)
  ringTimer = 0
  capTimer = 0
  for (const osc of playing) {
    try {
      osc.stop()
    } catch {
      /* already stopped */
    }
  }
  playing = []
  applySoundMode()
}

export function alarmRinging() {
  return ringTimer !== 0
}
