// The red card is the only card that makes a sound, and it repeats until read
// (architecture.md "alert"; design system "Sound"). A plain two-note tone made with
// Web Audio, so there is no audio file to ship. Browsers only allow sound after the
// first tap on the page, so we unlock the audio on the first pointer press.
import { useEffect } from 'react'

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

function ding() {
  if (!ctx || ctx.state !== 'running') return
  const now = ctx.currentTime
  ;[0, 0.35].forEach((offset, i) => {
    const osc = ctx!.createOscillator()
    const gain = ctx!.createGain()
    osc.frequency.value = i === 0 ? 880 : 660
    gain.gain.setValueAtTime(0.0001, now + offset)
    gain.gain.exponentialRampToValueAtTime(0.4, now + offset + 0.02)
    gain.gain.exponentialRampToValueAtTime(0.0001, now + offset + 0.3)
    osc.connect(gain).connect(ctx!.destination)
    osc.start(now + offset)
    osc.stop(now + offset + 0.32)
  })
}

export function useUrgentSound(active: boolean) {
  useEffect(() => {
    if (!active) return
    ding()
    const id = window.setInterval(ding, 4000)
    return () => window.clearInterval(id)
  }, [active])
}
