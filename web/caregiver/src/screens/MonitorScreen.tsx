import { useEffect, useRef, useState } from 'react'
import '../styles/monitor.css'
import type { Health } from '../types'
import { timeBoth, timeInWords, type T } from '../i18n/i18n'
import { SubHead } from '../components/SubHead'
import type { LiveFace, LiveRow } from '../feed/live'

interface RoomInfo {
  id: string
  tl: string
  en: string
  file: boolean
  detected: boolean
  clip_offset_s: number | null
  scanned_at: string
}

const FALLBACK: RoomInfo[] = [
  { id: 'hagdan', tl: 'Hagdan', en: 'Stairs', file: false, detected: false, clip_offset_s: null, scanned_at: '' },
  { id: 'kainan', tl: 'Kainan', en: 'Dining', file: false, detected: false, clip_offset_s: null, scanned_at: '' },
  { id: 'balkonahe', tl: 'Balkonahe', en: 'Balcony', file: false, detected: false, clip_offset_s: null, scanned_at: '' },
]

function clipClock(seconds: number | null): string {
  const total = Math.max(0, Math.round(seconds ?? 0))
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

type Pair = { main: string; sub: string }

function words(lang: T['lang'], tl: string, en: string): Pair {
  switch (lang) {
    case 'tl':
      return { main: tl, sub: '' }
    case 'en':
      return { main: en, sub: '' }
    case 'both':
      return { main: tl, sub: en }
    default: {
      const _never: never = lang
      return _never
    }
  }
}

function clock(lang: T['lang'], ms: number): Pair {
  switch (lang) {
    case 'tl':
      return { main: timeInWords(ms, 'tl'), sub: '' }
    case 'en':
      return { main: timeInWords(ms, 'en'), sub: '' }
    case 'both': {
      const [tl, en] = timeBoth(ms)
      return { main: tl, sub: en }
    }
    default: {
      const _never: never = lang
      return _never
    }
  }
}

function lastEvent(raw: string | undefined, lang: T['lang']): Pair {
  const text = (raw ?? '').trim()
  if (!text) return words(lang, 'Wala pa', 'None yet')
  const ms = Date.parse(text)
  if (Number.isNaN(ms)) return { main: text, sub: '' }
  return clock(lang, ms)
}

function actionCopy(row: LiveRow): [string, string] {
  switch (row.action) {
    case 'comfort':
      return ['Aliw', 'Comfort']
    case 'caregiver':
      return ['Tagapag-alaga', 'Caregiver']
    case 'urgent':
      return ['Kailangan ngayon', 'Urgent']
    case 'silent':
      return ['Tahimik', 'Silent']
    case 'dropped':
      return row.tv ? ['Tahimik', 'Silent'] : ['Hindi pinansin', 'Set aside']
    default: {
      const _never: never = row.action
      return _never
    }
  }
}

function Bits({ text }: { text: Pair }) {
  return (
    <span>
      <b>{text.main}</b>
      {text.sub ? <small>{text.sub}</small> : null}
    </span>
  )
}

function Status({ t, health }: { t: T; health: Health | null }) {
  const home = health?.server
    ? words(t.lang, 'Nandito sa bahay', 'On the home network')
    : words(t.lang, 'Hindi nandito', 'Not on the home network')
  const online = health?.offline === false
  const net = online
    ? words(t.lang, 'May internet', 'Internet is up')
    : words(t.lang, 'Walang internet', 'Offline from the internet')
  const mic = health?.mic ? words(t.lang, 'Bukas', 'On') : words(t.lang, 'Sarado', 'Off')
  const modelWord = typeof health?.model === 'string' ? health.model.trim() : ''
  const model = modelWord ? { main: modelWord, sub: '' } : words(t.lang, 'Wala pa', 'None yet')
  return (
    <ul className="sn-mon">
      <li><Bits text={words(t.lang, 'Bahay', 'Home network')} /><span className="sn-mon-val"><Bits text={home} /></span></li>
      <li>
        <Bits text={words(t.lang, 'Internet', 'Internet')} />
        <span className={online ? 'sn-mon-tag sn-mon-tag--amber' : 'sn-mon-tag'}><Bits text={net} /></span>
      </li>
      <li><Bits text={words(t.lang, 'Mikropono', 'Microphone')} /><span className="sn-mon-val"><Bits text={mic} /></span></li>
      <li><Bits text={words(t.lang, 'Modelo', 'Model')} /><span className="sn-mon-val"><Bits text={model} /></span></li>
      <li><Bits text={words(t.lang, 'Huling pangyayari', 'Last event')} /><span className="sn-mon-val"><Bits text={lastEvent(health?.last_event_at, t.lang)} /></span></li>
    </ul>
  )
}

function LiveList({ t, rows }: { t: T; rows: LiveRow[] }) {
  if (!rows.length) {
    return (
      <p className="sn-mon-empty" role="status">
        <Bits text={words(t.lang, 'Wala pang naririnig.', 'Nothing heard yet.')} />
      </p>
    )
  }
  return (
    <ul className="sn-mon-live">
      {rows.map((row) => {
        const [tl, en] = actionCopy(row)
        return (
          <li key={row.id} className={row.action === 'urgent' ? 'sn-mon-row sn-mon-row--urgent' : 'sn-mon-row'}>
            <p className="sn-mon-quote">“{row.transcript}”</p>
            <p className="sn-mon-meta">
              <Bits text={words(t.lang, tl, en)} />
              {row.tv ? <span className="sn-mon-tag">TV</span> : null}
              <span className="sn-mon-time"><Bits text={clock(t.lang, row.at)} /></span>
            </p>
          </li>
        )
      })}
    </ul>
  )
}

function RoomReel({ t, hub }: { t: T; hub: boolean }) {
  const [rooms, setRooms] = useState<RoomInfo[]>(FALLBACK)
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const start = useRef<{ x: number; y: number } | null>(null)
  const swiped = useRef(false)
  const count = rooms.length || 1
  const room = rooms[((index % count) + count) % count] ?? FALLBACK[0]

  useEffect(() => {
    if (!hub) return
    let stop = false
    fetch('/clips/rooms')
      .then((res) => (res.ok ? res.json() : null))
      .then((body: { rooms?: RoomInfo[] } | null) => {
        if (stop || !body || !Array.isArray(body.rooms) || body.rooms.length === 0) return
        setRooms(body.rooms)
      })
      .catch(() => undefined)
    return () => { stop = true }
  }, [hub])

  const move = (dir: number) => {
    setPlaying(false)
    setIndex((i) => (i + dir + count) % count)
  }

  const name = words(t.lang, room.tl, room.en)
  const empty = words(t.lang, 'Wala pang recording', 'No recording yet.')
  const person = room.detected
    ? words(t.lang, 'May tao sa recording', 'A person was in the recording')
    : words(t.lang, 'Walang tao', 'No person detected')
  const when = room.scanned_at ? lastEvent(room.scanned_at, t.lang) : words(t.lang, 'Wala pa', 'None yet')

  return (
    <section className="sn-room" aria-label={name.main}>
      <div
        className="sn-room-stage"
        onPointerDown={(e) => {
          if ((e.target as HTMLElement).closest('.sn-room-arrow')) return
          start.current = { x: e.clientX, y: e.clientY }
        }}
        onPointerUp={(e) => {
          const from = start.current
          start.current = null
          if (!from) return
          const dx = e.clientX - from.x
          const dy = e.clientY - from.y
          if (Math.abs(dx) < 48 || Math.abs(dx) < Math.abs(dy)) return
          swiped.current = true
          move(dx < 0 ? 1 : -1)
        }}
      >
        <button type="button" className="sn-btn sn-room-arrow" aria-label={t.lang === 'en' ? 'Previous room' : 'Nakaraang kwarto'} onClick={() => move(-1)}>‹</button>
        <div className="sn-room-frame">
          {playing && room.file ? (
            <video className="sn-room-video" src={`/clips/file/${room.id}`} controls autoPlay playsInline />
          ) : room.file ? (
            <button type="button" className="sn-room-still" onClick={() => {
              if (swiped.current) { swiped.current = false; return }
              setPlaying(true)
            }}>
              {room.detected ? (
                <img src={`/clips/snapshot?room=${room.id}`} alt="" />
              ) : (
                <span className="sn-room-mat" />
              )}
            </button>
          ) : (
            <p className="sn-room-empty" role="status">
              <b>{empty.main}</b>
              {empty.sub ? <span>{empty.sub}</span> : null}
            </p>
          )}
        </div>
        <button type="button" className="sn-btn sn-room-arrow" aria-label={t.lang === 'en' ? 'Next room' : 'Susunod na kwarto'} onClick={() => move(1)}>›</button>
      </div>
      <p className="sn-room-name"><Bits text={name} /></p>
      <div className="sn-room-dots" aria-hidden="true">
        {rooms.map((item, i) => <i key={item.id} className={i === ((index % count) + count) % count ? 'is-on' : ''} />)}
      </div>
      <p className="sn-room-label">RECORDED CLIP · DEMO</p>
      {room.detected ? (
        <p className="sn-mon-tag" style={{ maxWidth: 'none', justifySelf: 'center' }}>
          {`Huling nakita: ${room.tl} ${clipClock(room.clip_offset_s)}`}
        </p>
      ) : null}
      <p className="sn-room-meta">
        <Bits text={{ main: `Clip ${clipClock(room.clip_offset_s)}`, sub: '' }} />
        <Bits text={person} />
        {room.detected ? <Bits text={when} /> : null}
      </p>
    </section>
  )
}

function FaceLine({ t, face }: { t: T; face: LiveFace }) {
  const name = face.who
    ? { main: face.who, sub: '' }
    : words(t.lang, 'Walang nakilala', 'No one recognized')
  return (
    <p className="sn-mon-face">
      <Bits text={words(t.lang, 'Huling mukha', 'Last face')} />
      <Bits text={name} />
      <span className="sn-mon-score">{face.score.toFixed(2)}</span>
    </p>
  )
}

export function MonitorScreen(props: {
  t: T
  health: Health | null
  link: 'open' | 'reconnecting'
  hub: boolean
  rows: LiveRow[]
  face: LiveFace | null
  onBack: () => void
  preview?: boolean
}): JSX.Element {
  const { t } = props
  const title = words(t.lang, 'Buhay na tanaw', 'Live monitor')
  const reachable = props.preview || (props.hub && props.link === 'open')
  const miss = words(t.lang, 'Hindi maabot ang hub', 'The hub is not reachable from this phone.')
  return (
    <>
      <div className={title.sub ? 'sn-mon-both' : undefined}>
        <SubHead title={title.sub ? `${title.main}\n${title.sub}` : title.main} label={t.one('back')} onBack={props.onBack} />
      </div>
      <div className="sn-scroll">
        {reachable ? (
          <div className="sn-mon-body">
            <RoomReel t={t} hub={props.preview || props.hub} />
            <Status t={t} health={props.health} />
            <LiveList t={t} rows={props.rows} />
            {props.face ? <FaceLine t={t} face={props.face} /> : null}
          </div>
        ) : (
          <div className="sn-mon-body">
            <div className="sn-mon-calm" role="status">
              <b>{miss.main}</b>
              {miss.sub ? <span>{miss.sub}</span> : null}
            </div>
          </div>
        )}
      </div>
    </>
  )
}
