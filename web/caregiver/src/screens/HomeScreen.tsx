import { useState } from 'react'
import '../styles/monitor.css'
import type { Entry, Health, Person } from '../types'
import { dateLine, greetingKey, type T } from '../i18n/i18n'
import { SalaScene } from '../components/SalaScene'
import { SummaryChips } from '../components/SummaryChips'
import { DoneCard, NeedsCard, UrgentCard } from '../components/Cards'
import { Frame } from '../components/Frame'
import { Heading } from '../components/bits'

interface Props {
  t: T
  me: string
  now: number
  health: Health | null
  entries: Entry[]
  people: Person[]
  replyCount: (name: string) => number
  onRecord: (id: string) => void
  onReply: (audio?: Blob) => void
  onUnread: (id: string) => void
  onPerson: (name: string) => void
  onFamily: () => void
  lastNote: Entry | null
  onAte: () => void
  onUndoNote: () => void
  onMonitor?: () => void
}

const TILTS = ['l', '', 'r'] as const

export function HomeScreen(p: Props) {
  const { t } = p
  const [widget, setWidget] = useState<'ok' | 'needs' | null>(null)
  const urgent = p.entries.filter((e) => e.kind === 'urgent')
  const needs = p.entries.filter((e) => e.kind === 'needs')
  const done = p.entries.filter((e) => e.kind === 'answered' || e.kind === 'seen')
  const answered = done.filter((e) => e.kind === 'answered')

  // health light: which parts are down, said in plain words
  const down = p.health
    ? [
        !p.health.mic && t.one('partMic'),
        !p.health.whisper && t.one('partWhisper'),
        !p.health.ollama && t.one('partModel'),
        !p.health.server && t.one('partServer'),
      ].filter(Boolean)
    : []
  const ok = down.length === 0

  const hNeeds = t.head('needs')
  const hFam = t.head('family')
  const hAns = t.head('answeredToday')
  const sala = (
    <>
      <SalaScene
        initials={p.people.slice(0, 3).map((x) => x.name[0]?.toUpperCase() ?? '')}
        photos={p.people.slice(0, 3).map((x) => x.photo ?? '')}
      />
      <div className={`sn-salabar${ok ? '' : ' is-down'}`}>
        <div>
          <b>{ok ? t.one('salaOn') : t.one('salaDown')}</b>
          <span>{ok ? t.one('salaSub') : t.one('salaDownSub', { parts: down.join(', ') })}</span>
        </div>
        <span className="sn-live" aria-hidden="true" />
      </div>
    </>
  )

  return (
    <div className="sn-scroll">
      <div className="sn-hello">
        <p className="sn-eyebrow">{dateLine(p.now, t.lang)}</p>
        <h1 className="sn-greet">{t.one(greetingKey(p.now))}, {p.me}</h1>
      </div>

      {p.onMonitor
        ? <button type="button" className="sn-salacard sn-salacard--tap" onClick={p.onMonitor}>{sala}</button>
        : <div className="sn-salacard">{sala}</div>}

      <button type="button" className="sn-btn sn-btn--wide sn-ate" onClick={p.onAte}>{t.btn('kumainNa')}</button>
      {p.lastNote?.preset === 'ate' ? (
        <div className="sn-undo">
          <span>{p.lastNote.sentToHub ? t.one('loggedHub') : `${t.one('actAdded')}: ${p.lastNote.label ? (t.lang === 'en' ? p.lastNote.label[1] : p.lastNote.label[0]) : p.lastNote.transcript}`}</span>
          <button type="button" className="sn-btn sn-btn--quiet" onClick={p.onUndoNote}>{t.btn('undo')}</button>
        </div>
      ) : null}

      {urgent.map((e) => <UrgentCard key={e.id} t={t} entry={e} onReply={p.onReply} />)}

      <div className="sn-block">
        <Heading main={hNeeds.main} sub={hNeeds.sub} />
        {needs.length ? (
          <ul className="sn-log">{needs.map((e) => <NeedsCard key={e.id} t={t} entry={e} onRecord={() => p.onRecord(e.id)} />)}</ul>
        ) : <p className="sn-calm pl">{t.two('needsEmpty')}</p>}
      </div>

      <div className="sn-block">
        <Heading main={hAns.main} sub={hAns.sub} />
        {done.length ? (
          <ul className="sn-log">{done.map((e) => <DoneCard key={e.id} t={t} entry={e} onUnread={() => p.onUnread(e.id)} />)}</ul>
        ) : <p className="sn-calm pl">{t.two('noMoments')}</p>}
      </div>

      <SummaryChips t={t} answered={answered} needs={needs} open={widget} setOpen={setWidget} onRecord={p.onRecord} />

      <div className="sn-block">
        <Heading main={hFam.main} sub={hFam.sub}>
          <button type="button" className="sn-link" onClick={p.onFamily}>{t.one('seeAll')}</button>
        </Heading>
        <div className="sn-wall">
          {p.people.map((x, i) => (
            <Frame key={x.name} name={x.name} color={x.color} photo={x.photo} tilt={TILTS[i % 3]}
              meta={t.one('replies', { n: p.replyCount(x.name) })}
              ariaLabel={t.one('personReplies', { name: x.name })} onClick={() => p.onPerson(x.name)} />
          ))}
        </div>
      </div>
    </div>
  )
}
