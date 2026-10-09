// Hold-free recording for "Record a reply": tap to start, tap to stop.
// Uses the browser's MediaRecorder. No timer and no cutoff (design system rule 9).
import { useCallback, useEffect, useRef, useState } from 'react'

export type RecState = 'idle' | 'recording' | 'done' | 'denied'
export const BAR_COUNT = 26

export function useRecorder() {
  const [state, setState] = useState<RecState>('idle')
  const [levels, setLevels] = useState<number[]>([])
  const [blob, setBlob] = useState<Blob | null>(null)
  const [url, setUrl] = useState('')
  const rec = useRef<MediaRecorder | null>(null)
  const stream = useRef<MediaStream | null>(null)
  const raf = useRef(0)
  const ctx = useRef<AudioContext | null>(null)

  const cleanup = useCallback(() => {
    cancelAnimationFrame(raf.current)
    stream.current?.getTracks().forEach((t) => t.stop())
    stream.current = null
    ctx.current?.close().catch(() => undefined)
    ctx.current = null
  }, [])

  useEffect(() => () => cleanup(), [cleanup])
  useEffect(() => () => { if (url) URL.revokeObjectURL(url) }, [url])

  const start = useCallback(async () => {
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: true })
      stream.current = s
      const chunks: Blob[] = []
      const r = new MediaRecorder(s)
      r.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data) }
      r.onstop = () => {
        const b = new Blob(chunks, { type: r.mimeType || 'audio/webm' })
        setBlob(b)
        setUrl(URL.createObjectURL(b))
        setState('done')
        cleanup()
      }
      // loudness for the waveform bars
      const ac = new AudioContext()
      ctx.current = ac
      const an = ac.createAnalyser()
      an.fftSize = 512
      ac.createMediaStreamSource(s).connect(an)
      const buf = new Uint8Array(an.fftSize)
      let last = 0
      const tick = (now: number) => {
        if (now - last > 120) {
          last = now
          an.getByteTimeDomainData(buf)
          let peak = 0
          for (const v of buf) peak = Math.max(peak, Math.abs(v - 128))
          setLevels((l) => [...l, Math.min(1, peak / 64)].slice(-BAR_COUNT))
        }
        raf.current = requestAnimationFrame(tick)
      }
      raf.current = requestAnimationFrame(tick)
      setLevels([])
      setBlob(null)
      rec.current = r
      r.start()
      setState('recording')
    } catch {
      cleanup()
      setState('denied')
    }
  }, [cleanup])

  const stop = useCallback(() => { rec.current?.state === 'recording' && rec.current.stop() }, [])
  const reset = useCallback(() => {
    if (rec.current) rec.current.onstop = null // throw this take away
    if (rec.current?.state === 'recording') rec.current.stop()
    cleanup()
    setBlob(null)
    setLevels([])
    setState('idle')
  }, [cleanup])

  return { state, levels, blob, url, start, stop, reset }
}
