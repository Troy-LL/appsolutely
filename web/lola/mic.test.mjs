// Tests the pure parts of mic.js: the loudness gate, the WAV encoder, the
// downsampler and the one-upload-at-a-time queue. No mic, no browser.
//   node web/lola/mic.test.mjs
import { readFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { Gate, encodeWav, downsample, makeSender, frameDbfs, FRAME_SECONDS } from './mic.js'

let failed = 0
function check(name, ok, detail = '') {
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${name}${detail ? `  (${detail})` : ''}`)
  if (!ok) failed++
}

const RATE = 48000 // a usual iPad AudioContext rate
const N = Math.round(RATE * FRAME_SECONDS) // samples in one 30 ms frame
let seed = 1 // fixed pseudo-random noise, so every run is the same
const rand = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648) * 2 - 1

// One 30 ms frame at an RMS level in dBFS: room noise, a 440 Hz tone, or exact zeros.
function makeFrame(kind, dbfs, t) {
  const f = new Float32Array(N)
  if (kind === 'zero') return f
  const amp = 10 ** (dbfs / 20) * (kind === 'tone' ? Math.SQRT2 : Math.sqrt(3))
  for (let i = 0; i < N; i++) f[i] = kind === 'tone' ? amp * Math.sin((2 * Math.PI * 440 * (t + i)) / RATE) : amp * rand()
  return f
}

// scene: [kind, seconds, dbfs, replyPlaying]. Returns the clips with their length in frames.
function run(scene) {
  const gate = new Gate()
  const clips = []
  let t = 0
  for (const [kind, seconds, dbfs, playing = false] of scene) {
    for (let i = 0; i < Math.round(seconds / FRAME_SECONDS); i++, t += N) {
      const clip = gate.feed(makeFrame(kind, dbfs, t), playing)
      if (clip) clips.push({ clip, frames: clip.length / N })
    }
  }
  return clips
}

// --- loudness ---
const sine = makeFrame('tone', 0, 0).map((s) => s / Math.SQRT2) // a full-scale sine
check('full-scale sine is about -3 dBFS', Math.abs(frameDbfs(sine) + 3.01) < 0.05, frameDbfs(sine).toFixed(2))

// --- gate ---
check('quiet room, 5 s: no clip', run([['noise', 5, -60]]).length === 0)
check('muted mic (exact zeros), 5 s: no clip', run([['zero', 5]]).length === 0)

{ // 2 s room, 1 s loud tone, 2 s room: one clip = 10 pre-roll + 33 tone + 27 quiet frames
  const clips = run([['noise', 2, -60], ['tone', 1, -20], ['noise', 2, -60]])
  check('1 s burst: exactly one clip', clips.length === 1, `${clips.length} clips`)
  if (clips.length === 1) {
    const { clip, frames } = clips[0]
    const level = (k) => frameDbfs(clip.subarray(k * N, (k + 1) * N))
    const pre = [...Array(10).keys()].every((k) => level(k) < -55)
    check('clip is 70 frames (2.1 s)', frames === 70, `${frames} frames`)
    check('clip starts with 0.3 s of room before the sound (pre-roll)', pre && level(10) > -25,
      `frame 9 ${level(9).toFixed(1)} dBFS, frame 10 ${level(10).toFixed(1)} dBFS`)
  }
}

check('0.3 s click: too short, no clip', run([['noise', 2, -60], ['tone', 0.3, -20], ['noise', 2, -60]]).length === 0)

{ // 12 s of loud sound: the first clip is cut at 8 s (267 frames), none is longer
  const clips = run([['noise', 2, -70], ['tone', 12, -10], ['noise', 2, -70]])
  const longest = Math.max(...clips.map((c) => c.frames))
  check('12 s sound: first clip cut at 8 s', clips.length >= 1 && clips[0].frames === 267,
    `${clips.length} clips, first ${clips[0] && clips[0].frames} frames, longest ${longest}`)
  const wav = encodeWav(downsample(clips[0].clip, RATE, 16000), 16000)
  check('8 s clip as 16 kHz WAV is under 2 MB', wav.byteLength < 2 * 1024 * 1024, `${wav.byteLength} bytes`)
}

check('burst while a reply plays (and 0.6 s after): no clip',
  run([['noise', 2, -60], ['tone', 2, -20, true], ['tone', 0.6, -20], ['noise', 2, -60]]).length === 0)
check('after the reply and its 1 s tail, the gate hears again',
  run([['noise', 2, -60], ['tone', 2, -20, true], ['noise', 1.5, -60], ['tone', 1, -20], ['noise', 2, -60]]).length === 1)

// --- WAV encoder ---
function parseWav(buf) { // a small WAV reader: finds the fmt and data chunks, skips others (LIST)
  const v = new DataView(buf.buffer, buf.byteOffset, buf.byteLength)
  const tag = (at) => String.fromCharCode(...buf.subarray(at, at + 4))
  const out = { riff: tag(0), riffSize: v.getUint32(4, true), wave: tag(8) }
  for (let at = 12; at + 8 <= buf.length; at += 8 + v.getUint32(at + 4, true) + (v.getUint32(at + 4, true) % 2)) {
    const size = v.getUint32(at + 4, true)
    if (tag(at) === 'fmt ') {
      Object.assign(out, { fmtSize: size, format: v.getUint16(at + 8, true), channels: v.getUint16(at + 10, true),
        rate: v.getUint32(at + 12, true), byteRate: v.getUint32(at + 16, true),
        blockAlign: v.getUint16(at + 20, true), bits: v.getUint16(at + 22, true) })
    }
    if (tag(at) === 'data') {
      out.dataSize = size
      out.samples = Float32Array.from({ length: size / 2 }, (_, i) => v.getInt16(at + 8 + i * 2, true) / 32768)
    }
  }
  return out
}

{
  const buf = new Uint8Array(encodeWav(Float32Array.from([0, 0.5, -0.5, 1, -1, 2]), 16000))
  const w = parseWav(buf)
  const v = new DataView(buf.buffer)
  const ints = [0, 1, 2, 3, 4, 5].map((i) => v.getInt16(44 + i * 2, true))
  check('WAV header: RIFF/WAVE, PCM, mono, 16-bit, 16 kHz',
    w.riff === 'RIFF' && w.wave === 'WAVE' && w.fmtSize === 16 && w.format === 1 && w.channels === 1 &&
    w.bits === 16 && w.rate === 16000 && w.byteRate === 32000 && w.blockAlign === 2)
  check('WAV sizes: file 56 bytes, RIFF size 48, data 12', buf.length === 56 && w.riffSize === 48 && w.dataSize === 12,
    `file ${buf.length}, riff ${w.riffSize}, data ${w.dataSize}`)
  check('WAV samples (2 is clipped to full scale)', ints.join() === '0,16384,-16384,32767,-32768,32767', ints.join())
}

// --- downsampler ---
{
  const flat = new Float32Array(48000).fill(0.25)
  const d48 = downsample(flat, 48000, 16000)
  const d44 = downsample(new Float32Array(44100), 44100, 16000)
  check('downsample 1 s: 48 kHz and 44.1 kHz both give 16000 samples', d48.length === 16000 && d44.length === 16000)
  check('downsample keeps the level', d48.every((s) => Math.abs(s - 0.25) < 1e-6))
  check('downsample at the same rate returns the input', downsample(flat, 16000, 16000) === flat)
}

// --- upload queue ---
{
  const sent = []
  let release = null
  const offer = makeSender((x) => { sent.push(x); return new Promise((r) => { release = r }) })
  const tick = () => new Promise((r) => setTimeout(r, 0))
  offer('a'); offer('b'); offer('c') // b and c finish while a uploads: only c waits
  await tick(); release(); await tick(); release(); await tick()
  offer('d'); await tick(); release(); await tick()
  check('one upload at a time, newest waiting clip wins', sent.join() === 'a,c,d', sent.join())
}

// --- a real recording: brain/tests/audio/lola/u07.wav ("Tulong naman") ---
const u07 = fileURLToPath(new URL('../../brain/tests/audio/lola/u07.wav', import.meta.url))
if (!existsSync(u07)) {
  console.log('skip u07.wav not found')
} else {
  const w = parseWav(new Uint8Array(readFileSync(u07)))
  const n = Math.round(w.rate * FRAME_SECONDS)
  // 1.5 s of room before and after, and room noise (-60 dBFS) under the voice too, as a real
  // mic hears it. (Spliced between exact silences, the file's -85 dBFS tail would drag the
  // floor down and the -60 dBFS room after it would count as loud.)
  const pad = Math.round(1.5 * w.rate)
  const all = Float32Array.from({ length: pad * 2 + w.samples.length }, () => 10 ** (-60 / 20) * Math.sqrt(3) * rand())
  w.samples.forEach((s, i) => { all[pad + i] += s })
  const gate = new Gate()
  const clips = []
  for (let k = 0; (k + 1) * n <= all.length; k++) {
    const clip = gate.feed(all.subarray(k * n, (k + 1) * n))
    if (clip) clips.push({ clip, start: (k + 1) * n - clip.length, end: (k + 1) * n })
  }
  const sec = (x) => (x / w.rate).toFixed(2)
  const c = clips[0]
  check(`u07.wav (${w.rate} Hz, ${sec(w.samples.length)} s) padded with room noise: exactly one clip`, clips.length === 1,
    c ? `clip ${sec(c.start)}-${sec(c.end)} s, speech file is ${sec(pad)}-${sec(pad + w.samples.length)} s` : `${clips.length} clips`)
  if (c) {
    check('u07 clip holds the whole recording', c.start <= pad && c.end >= pad + w.samples.length)
    const back = parseWav(new Uint8Array(encodeWav(c.clip, w.rate)))
    check('u07 clip encodes and reads back as WAV', back.samples.length === c.clip.length && back.rate === w.rate)
  }
}

console.log(failed ? `\n${failed} failed` : '\nall passed')
process.exit(failed ? 1 : 0)
