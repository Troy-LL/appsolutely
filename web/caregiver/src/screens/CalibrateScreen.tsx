import { useEffect, useRef, useState } from 'react'
import type { T } from '../i18n/i18n'
import { Back } from '../components/Icons'
import { enrollFrames, jpegFromVideo, loadGallery, sampleOval, watchFrame } from '../data/faceEnroll'
import { copy, head, say, slash } from '../i18n/calibrate'
import '../styles/calibrate.css'

const STEPS = [copy.straight, copy.left, copy.right, copy.chin, copy.smile]

type Phase = 'loading' | 'missing' | 'denied' | 'camera' | 'done'

function clampStep(n: number): number {
  if (!Number.isFinite(n) || n <= 0) return 0
  if (n >= 4) return 4
  return Math.floor(n)
}

function revoke(url: string) {
  if (url.startsWith('blob:')) URL.revokeObjectURL(url)
}

export function CalibrateScreen(props: {
  t: T
  name: string
  personId: 'troy' | 'joy' | 'donita'
  onBack: () => void
  onEnrolled?: () => void
  preview?: { step: number; done?: boolean; engine?: 'ok' | 'missing' }
}): JSX.Element {
  const { t, name, personId, onBack, onEnrolled, preview } = props
  const previewing = preview !== undefined
  const [livePhase, setLivePhase] = useState<Phase>('loading')
  const [liveStep, setLiveStep] = useState(0)
  const [thumbs, setThumbs] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [retake, setRetake] = useState(false)
  const [kept, setKept] = useState<number | null>(null)
  const [arm, setArm] = useState(0)
  const [camOn, setCamOn] = useState(false)
  const replaced = useRef(false)
  const enrolledRef = useRef(onEnrolled)
  enrolledRef.current = onEnrolled
  const pauseRef = useRef(false)
  const posting = useRef(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const thumbsRef = useRef<string[]>([])
  const live = useRef(true)
  thumbsRef.current = thumbs

  const phase: Phase = preview
    ? preview.engine === 'missing'
      ? 'missing'
      : preview.done
        ? 'done'
        : 'camera'
    : livePhase
  const step = preview && phase === 'camera' ? clampStep(preview.step) : liveStep

  useEffect(() => {
    live.current = true
    return () => {
      live.current = false
      for (const url of thumbsRef.current) revoke(url)
    }
  }, [])

  useEffect(() => {
    pauseRef.current = previewing || busy || retake || kept !== null || phase !== 'camera'
  }, [previewing, busy, retake, kept, phase])

  useEffect(() => {
    if (previewing) return
    let cancel = false
    loadGallery()
      .then((body) => {
        if (cancel) return
        setLivePhase(body.engine === 'missing' ? 'missing' : 'camera')
      })
      .catch(() => {
        if (!cancel) setLivePhase('missing')
      })
    return () => {
      cancel = true
    }
  }, [previewing])

  useEffect(() => {
    if (phase !== 'camera' || previewing) return
    let cancel = false
    let stream: MediaStream | null = null
    setCamOn(false)
    const open = async () => {
      try {
        if (!navigator.mediaDevices?.getUserMedia) throw new Error('camera')
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false })
        if (cancel) {
          stream.getTracks().forEach((track) => track.stop())
          return
        }
        const video = videoRef.current
        if (!video) return
        video.srcObject = stream
        await video.play()
        if (!cancel) setCamOn(true)
      } catch {
        if (!cancel) setLivePhase('denied')
      }
    }
    void open()
    return () => {
      cancel = true
      setCamOn(false)
      stream?.getTracks().forEach((track) => track.stop())
      const video = videoRef.current
      if (video) video.srcObject = null
    }
  }, [phase, previewing])

  useEffect(() => {
    if (phase !== 'camera' || previewing || !camOn) return
    const video = videoRef.current
    if (!video) return
    const canvas = document.createElement('canvas')
    let raf = 0
    let last = 0
    let prev: Float32Array | null = null
    let stillSince: number | null = null
    let shot = false
    const take = async () => {
      if (posting.current) return
      posting.current = true
      setBusy(true)
      setRetake(false)
      setKept(null)
      try {
        const blob = await jpegFromVideo(video)
        if (!live.current) return
        if (!blob) {
          setBusy(false)
          setRetake(true)
          return
        }
        const url = URL.createObjectURL(blob)
        try {
          const body = await enrollFrames(personId, [blob], !replaced.current)
          if (!live.current) {
            revoke(url)
            return
          }
          if (body.engine === 'missing') {
            revoke(url)
            setBusy(false)
            setLivePhase('missing')
            return
          }
          if (body.frames[0]?.ok) {
            replaced.current = true
            enrolledRef.current?.()
            thumbsRef.current = [...thumbsRef.current, url]
            setThumbs(thumbsRef.current)
            setBusy(false)
            if (step >= 4) setLivePhase('done')
            else setLiveStep(step + 1)
            return
          }
          revoke(url)
          setBusy(false)
          setRetake(true)
        } catch {
          revoke(url)
          if (!live.current) return
          setBusy(false)
          setRetake(true)
        }
      } catch {
        if (!live.current) return
        setBusy(false)
        setRetake(true)
      } finally {
        posting.current = false
      }
    }
    const tick = (now: number) => {
      raf = requestAnimationFrame(tick)
      if (pauseRef.current || shot) return
      if (now - last < 100) return
      last = now
      const lumas = sampleOval(video, canvas)
      if (!lumas) {
        prev = null
        stillSince = null
        return
      }
      const watched = watchFrame(lumas, prev, stillSince, now)
      prev = watched.prev
      stillSince = watched.stillSince
      if (!watched.ready) return
      shot = true
      pauseRef.current = true
      void take()
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [phase, previewing, camOn, step, arm, personId])

  const rearm = () => {
    setRetake(false)
    setKept(null)
    setArm((n) => n + 1)
  }

  const sendLibrary = async (files: File[]) => {
    if (previewing || posting.current || !files.length) return
    posting.current = true
    pauseRef.current = true
    setBusy(true)
    setRetake(false)
    setKept(null)
    try {
      const body = await enrollFrames(personId, files, true)
      if (!live.current) return
      if (body.engine === 'missing') {
        setBusy(false)
        setLivePhase('missing')
        return
      }
      const ok = body.frames.filter((frame) => frame.ok).length
      if (ok > 0) {
        replaced.current = true
        enrolledRef.current?.()
      }
      if (body.frames.length === files.length && ok === files.length && ok > 0) {
        for (const url of thumbsRef.current) revoke(url)
        thumbsRef.current = files.map((file) => URL.createObjectURL(file))
        setThumbs(thumbsRef.current)
        setBusy(false)
        setLivePhase('done')
        return
      }
      setKept(ok)
      setBusy(false)
    } catch {
      if (!live.current) return
      setKept(0)
      setBusy(false)
    } finally {
      posting.current = false
    }
  }

  const onPick = (input: HTMLInputElement) => {
    const picked = Array.from(input.files ?? []).slice(0, 5)
    input.value = ''
    void sendLibrary(picked)
  }

  const title = head(t, copy.title, { name })
  const prompt = head(t, STEPS[step] ?? copy.straight)
  const keptLine = kept !== null ? <p className="sn-cal__card pl" role="status">{say(t, copy.kept, { n: kept })}</p> : null
  const actions = (
    <div className="sn-cal__actions">
      {busy ? <p className="sn-cal__wait pl" role="status">{say(t, copy.loading)}</p> : (
        <>
          {retake || (kept !== null && phase === 'camera') ? (
            <button type="button" className="sn-btn" onClick={rearm}>{slash(t, copy.retake)}</button>
          ) : null}
          <label className="sn-btn sn-btn--quiet sn-cal__pick">
            {slash(t, copy.choose)}
            <input
              type="file"
              accept="image/*"
              multiple
              className="sn-visually-hidden"
              onChange={(e) => onPick(e.currentTarget)}
            />
          </label>
        </>
      )}
    </div>
  )

  const shown = phase === 'done' && thumbs.length === 0 ? ['', '', '', '', ''] : thumbs

  let body: JSX.Element
  switch (phase) {
    case 'loading':
      body = <p className="sn-cal__card pl" role="status">{say(t, copy.loading)}</p>
      break
    case 'missing':
      body = <p className="sn-cal__card pl" role="status">{say(t, copy.missing)}</p>
      break
    case 'denied':
      body = (
        <div className="sn-cal__col">
          <p className="sn-cal__card pl" role="status">{say(t, copy.denied)}</p>
          {keptLine}
          {actions}
        </div>
      )
      break
    case 'camera':
      body = (
        <div className="sn-cal__col">
          <div
            className="sn-cal__stage"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={5}
            aria-valuenow={step}
            aria-labelledby="sn-cal-prompt"
          >
            <svg className="sn-cal__ring" viewBox="0 0 100 100" aria-hidden="true">
              <circle cx="50" cy="50" r="46" fill="none" stroke="currentColor" strokeWidth="2" />
              {step > 0 ? (
                <circle
                  cx="50"
                  cy="50"
                  r="46"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="4"
                  strokeLinecap="round"
                  strokeDasharray={2 * Math.PI * 46}
                  strokeDashoffset={2 * Math.PI * 46 * (1 - step / 5)}
                  transform="rotate(-90 50 50)"
                />
              ) : null}
            </svg>
            <div className="sn-cal__oval">
              {previewing ? <div className="sn-cal__mat" /> : (
                <video ref={videoRef} playsInline muted autoPlay />
              )}
            </div>
          </div>
          <h3 className="sn-cal__prompt" id="sn-cal-prompt" aria-live="polite">
            {prompt.main}{prompt.sub ? <small>{prompt.sub}</small> : null}
          </h3>
          <p className="sn-cal__privacy pl">{say(t, copy.privacy)}</p>
          {keptLine}
          {!previewing && !camOn && !busy ? <p className="sn-cal__wait pl" role="status">{say(t, copy.loading)}</p> : null}
          {actions}
        </div>
      )
      break
    case 'done':
      body = (
        <div className="sn-cal__col">
          <ul className="sn-cal__thumbs">
            {shown.map((src, i) => (
              <li key={`${i}-${src || 'mat'}`}>
                {src ? <img className="sn-cal__thumb" src={src} alt="" /> : <span className="sn-cal__thumb" />}
              </li>
            ))}
          </ul>
          <p className="sn-cal__card pl" role="status">{say(t, copy.doneLine, { name })}</p>
          <button type="button" className="sn-btn sn-btn--wide" onClick={onBack}>{slash(t, copy.doneBtn)}</button>
        </div>
      )
      break
    default: {
      const leftover: never = phase
      body = leftover
      break
    }
  }

  return (
    <>
      <div className="sn-subhead">
        <button type="button" className="sn-icon-btn" aria-label={t.one('back')} onClick={onBack}><Back /></button>
        <h2>{title.main}{title.sub ? <small>{title.sub}</small> : null}</h2>
      </div>
      <div className="sn-scroll">
        <div className="sn-cal">{body}</div>
      </div>
    </>
  )
}
