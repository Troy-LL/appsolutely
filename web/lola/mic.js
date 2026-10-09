// mic.js — the iPad listens. Plain ES module, no build step, no packages.
// Lola speaks to the iPad. After the "Simulan" tap the screen asks for the
// microphone, cuts a short clip whenever someone speaks (a loudness gate, the
// same one as hub/always.py) and uploads it to the hub (POST /listen/audio).
// The hub runs Whisper, the junk filter and decide(); results come back on /ws
// like any other line. Nothing is shown on Lola's screen and no audio is kept.

// Gate defaults: the same numbers as hub/always.py, so both mics behave alike.
export const FRAME_SECONDS = 0.03 // the gate looks at 30 ms of audio at a time
export const GATE_MARGIN_DB = 12 // speech starts when a frame is this many dB louder than the noise floor
export const PRE_ROLL_SECONDS = 0.3 // audio kept from just before speech starts, so "Tulong" is not cut
export const SILENCE_SECONDS = 0.8 // this much quiet in a row ends the clip
export const MAX_CLIP_SECONDS = 8 // the clip is cut here even if the sound goes on
export const MIN_SPEECH_SECONDS = 0.5 // shorter sounds (a cough, a cup put down) are thrown away
export const WARMUP_SECONDS = 1.0 // after the mic starts, only learn how loud the room is
export const REPLY_TAIL_SECONDS = 1.0 // after a family reply ends, stay deaf this long (its echo)
export const UPLOAD_RATE = 16000 // clips go up as 16 kHz mono 16-bit WAV: 8 s is about 256 KB (hub max 2 MB)
const UPLOAD_TIMEOUT_MS = 10000 // give up on one upload after this long so the next clip can go
const LEVEL_MIN = -100 // an all-zero frame counts as -100 dBFS so the noise floor stays a number
// The noise floor follows quieter frames fast and louder frames slowly (share of the gap per
// frame), so words barely move it but a fan that stays on becomes the new "quiet" in seconds.
const FLOOR_FALL = 0.1
const FLOOR_RISE = 0.005

const frames = (seconds) => Math.max(1, Math.round(seconds / FRAME_SECONDS))

// Loudness (RMS) of one frame of samples (-1..1) in dBFS: 0 is full scale, -Infinity is all zeros.
export function frameDbfs(frame) {
  let power = 0
  for (const s of frame) power += s * s
  power /= frame.length || 1
  return power ? 10 * Math.log10(power) : -Infinity
}

// Cuts clips out of a stream of 30 ms frames by loudness alone (a copy of hub/always.py Gate).
// feed(frame, playing) returns a finished clip (one Float32Array) or null.
// playing = a family reply is playing now: the gate throws the audio away until
// REPLY_TAIL_SECONDS after it ends, so the iPad never sends its own reply to the hub.
export class Gate {
  constructor() {
    this.silenceFrames = frames(SILENCE_SECONDS)
    this.maxFrames = frames(MAX_CLIP_SECONDS)
    this.minFrames = frames(MIN_SPEECH_SECONDS)
    this.warmup = frames(WARMUP_SECONDS)
    this.keep = frames(PRE_ROLL_SECONDS) + 1 // the pre-roll plus the current frame
    this.seen = 0 // frames fed so far (deaf frames not counted)
    this.floor = null // noise floor in dBFS
    this.recent = [] // the last frames heard: the pre-roll ring
    this.clip = null // frames of the clip being cut, or null while waiting for speech
    this.speech = 0 // frames from the first loud frame to the last loud one
    this.quiet = 0 // quiet frames in a row since the last loud one
    this.deaf = 0 // frames left to ignore after a reply ended
  }

  feed(frame, playing = false) {
    if (playing) this.deaf = frames(REPLY_TAIL_SECONDS)
    if (playing || this.deaf > 0) { // drop everything heard, pre-roll too; the floor is not moved
      if (!playing) this.deaf--
      this.clip = null
      this.recent = []
      return null
    }
    const level = Math.max(frameDbfs(frame), LEVEL_MIN)
    this.recent.push(frame)
    if (this.recent.length > this.keep) this.recent.shift()
    this.seen++
    if (this.floor === null) this.floor = level
    if (this.seen <= this.warmup) { // first second: only learn the room, never start a clip
      this.floor += (level - this.floor) * FLOOR_FALL
      return null
    }
    const loud = level > this.floor + GATE_MARGIN_DB
    this.floor += (level - this.floor) * (level < this.floor ? FLOOR_FALL : FLOOR_RISE)
    if (this.clip === null) {
      if (loud) { // speech starts: keep the pre-roll too
        this.clip = [...this.recent]
        this.speech = 1
        this.quiet = 0
      }
      return null
    }
    this.clip.push(frame)
    if (loud) {
      this.speech += this.quiet + 1 // a short pause between words counts as speech
      this.quiet = 0
    } else {
      this.quiet++
    }
    if (this.quiet < this.silenceFrames && this.clip.length < this.maxFrames) return null
    const clip = this.clip
    this.clip = null
    return this.speech >= this.minFrames ? joinFrames(clip) : null
  }
}

function joinFrames(list) {
  const out = new Float32Array(list.reduce((n, f) => n + f.length, 0))
  let at = 0
  for (const f of list) { out.set(f, at); at += f.length }
  return out
}

// Lowers the sample rate (e.g. 48000 -> 16000). Each new sample is the average of the
// old samples it covers, a simple low-pass. Equal rates return the samples unchanged.
export function downsample(samples, fromRate, toRate) {
  if (fromRate <= toRate) return samples
  const ratio = fromRate / toRate
  const out = new Float32Array(Math.floor(samples.length / ratio))
  for (let i = 0; i < out.length; i++) {
    const start = Math.floor(i * ratio)
    const end = Math.min(samples.length, Math.floor((i + 1) * ratio))
    let sum = 0
    for (let j = start; j < end; j++) sum += samples[j]
    out[i] = end > start ? sum / (end - start) : 0
  }
  return out
}

// 16-bit PCM mono WAV: a 44-byte header, then the samples, little-endian. Returns an ArrayBuffer.
export function encodeWav(samples, rate) {
  const bytes = samples.length * 2
  const view = new DataView(new ArrayBuffer(44 + bytes))
  const text = (at, s) => { for (let i = 0; i < s.length; i++) view.setUint8(at + i, s.charCodeAt(i)) }
  text(0, 'RIFF')
  view.setUint32(4, 36 + bytes, true) // size of everything after this field
  text(8, 'WAVE')
  text(12, 'fmt ')
  view.setUint32(16, 16, true) // fmt chunk size
  view.setUint16(20, 1, true) // 1 = PCM
  view.setUint16(22, 1, true) // mono
  view.setUint32(24, rate, true) // samples per second
  view.setUint32(28, rate * 2, true) // bytes per second
  view.setUint16(32, 2, true) // bytes per sample
  view.setUint16(34, 16, true) // bits per sample
  text(36, 'data')
  view.setUint32(40, bytes, true)
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(44 + i * 2, Math.round(s < 0 ? s * 0x8000 : s * 0x7fff), true)
  }
  return view.buffer
}

// One upload at a time. A clip that finishes during an upload waits; if another one
// finishes too, only the newest waits (the older one is dropped, as the hub does).
export function makeSender(send) {
  let busy = false
  let waiting = null
  async function run() {
    busy = true
    while (waiting) {
      const next = waiting
      waiting = null
      try { await send(next) } catch { /* send logs its own failures */ }
    }
    busy = false
  }
  return (clip) => { waiting = clip; if (!busy) run() }
}

// One plain status line in the console when it changes. Never audio or words.
let lastNote = ''
function note(line) {
  if (line !== lastNote) console.info(line)
  lastNote = line
}

// Sends one WAV clip. The hub needs the .wav filename to know the format.
async function upload(base, wav) {
  const fd = new FormData()
  fd.append('audio', new Blob([wav], { type: 'audio/wav' }), 'clip.wav')
  fd.append('source', 'ipad')
  try {
    const signal = AbortSignal.timeout ? AbortSignal.timeout(UPLOAD_TIMEOUT_MS) : undefined
    const res = await fetch(`${base}/listen/audio`, { method: 'POST', body: fd, signal })
    note(res.ok ? 'mic: clip sent' : `mic: hub answered ${res.status}`)
  } catch {
    note('mic: hub not reachable')
  }
}

const MIC_OPTIONS = { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
let mic = null // the live audio nodes, kept here so Safari does not garbage-collect them

// Call from the "Simulan" tap: iPadOS shows its microphone prompt only for a tap, so
// getUserMedia runs before any await. ctx is the AudioContext created in that same tap.
// isPlaying() is true while a family reply plays. Never throws: on any failure it logs
// one line and Lola's screen carries on exactly as before (nothing red, no error text).
export async function startMic({ ctx, hubBase, isPlaying }) {
  if (mic) return
  mic = { ctx }
  let stream = null
  try {
    if (!ctx || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      note('mic: off (needs HTTPS and Web Audio)')
      return
    }
    stream = await navigator.mediaDevices.getUserMedia({ audio: MIC_OPTIONS })
    listen(ctx, stream, hubBase, isPlaying)
    document.addEventListener('visibilitychange', wake)
    note('mic: on')
  } catch (err) {
    if (stream) stream.getTracks().forEach((t) => t.stop()) // don't hold the mic if we can't use it
    note(`mic: off (${(err && err.name) || 'error'})`)
  }
}

function listen(ctx, stream, hubBase, isPlaying) {
  const gate = new Gate()
  const rate = Math.min(ctx.sampleRate, UPLOAD_RATE)
  const frameLen = Math.round(ctx.sampleRate * FRAME_SECONDS)
  const send = makeSender((wav) => upload(hubBase(), wav))
  let frame = new Float32Array(frameLen)
  let fill = 0
  // ScriptProcessorNode works in every Safari. It hands over 4096 mic samples at a
  // time (~85 ms at 48 kHz); they are cut into 30 ms frames for the gate.
  const proc = ctx.createScriptProcessor(4096, 1, 1)
  proc.onaudioprocess = (e) => {
    const input = e.inputBuffer.getChannelData(0)
    const playing = isPlaying()
    for (let i = 0; i < input.length; i++) {
      frame[fill++] = input[i]
      if (fill < frameLen) continue
      const clip = gate.feed(frame, playing)
      frame = new Float32Array(frameLen)
      fill = 0
      if (clip) send(encodeWav(downsample(clip, ctx.sampleRate, rate), rate))
    }
  }
  // The processor only runs when it is wired to the speakers; a zero-volume gain keeps it silent.
  const mute = ctx.createGain()
  mute.gain.value = 0
  proc.connect(mute)
  mute.connect(ctx.destination)
  const source = ctx.createMediaStreamSource(stream)
  source.connect(proc)
  mic = { ctx, stream, source, proc, mute }
  if (ctx.state !== 'running') ctx.resume().catch(() => {})
}

// iPadOS can pause the audio or stop the mic (screen lock, a call, Siri). When the page
// is visible again: wake the audio, and if the mic track ended, ask for the mic again.
async function wake() {
  if (document.visibilityState !== 'visible' || !mic || !mic.source) return
  if (mic.ctx.state !== 'running') mic.ctx.resume().catch(() => {})
  if (!mic.stream.getAudioTracks().every((t) => t.readyState === 'ended')) return
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: MIC_OPTIONS })
    mic.source.disconnect()
    mic.source = mic.ctx.createMediaStreamSource(stream)
    mic.source.connect(mic.proc)
    mic.stream = stream
    note('mic: on again')
  } catch (err) {
    note(`mic: off (${(err && err.name) || 'error'})`)
  }
}
