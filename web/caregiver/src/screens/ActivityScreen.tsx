import type { ReactNode } from "react"
import { useState } from 'react'
import type { Entry } from '../types'
import { timeInWords, type Key, type T } from '../i18n/i18n'
import { daysAgo, startOfDay } from '../data/history'
import { Plus, Receipt, Sliders, X } from '../components/Icons2'
import { mealKey, voiceOf } from '../feed/events'

type Kind = 'all' | 'urgent' | 'needs' | 'ok' | 'note'
type Range = 'today' | 'week' | 'date'

// Quick picks for "Add activity". [Tagalog, English]. Logged on this phone only.
const PRESETS: { id: string; label: [string, string] }[] = [
  { id: 'ate', label: ['Kumain', 'Ate a meal'] },
  { id: 'water', label: ['Uminom ng tubig', 'Drank water'] },
  { id: 'bath', label: ['Naligo', 'Took a bath'] },
  { id: 'nap', label: ['Natulog', 'Took a nap'] },
  { id: 'walk', label: ['Naglakad', 'Went for a walk'] },
  { id: 'visit', label: ['May bumisita', 'Had a visitor'] },
]

const isUrgent = (e: Entry) => e.kind === 'urgent' || e.kind === 'seen'
const MATCH: Record<Kind, (e: Entry) => boolean> = {
  all: () => true,
  urgent: isUrgent,
  needs: (e) => e.kind === 'needs',
  ok: (e) => e.kind === 'answered',
  note: (e) => e.kind === 'note',
}
const KINDS: { id: Kind; key: Key; mark: string }[] = [
  { id: 'all', key: 'filterEverything', mark: '' },
  { id: 'urgent', key: 'filterUrgent', mark: '▲' },
  { id: 'needs', key: 'filterNeeds', mark: '●' },
  { id: 'ok', key: 'filterAnswered', mark: '✓' },
  { id: 'note', key: 'filterAct', mark: '+' },
]
const RANGES: { id: Range; key: Key; hint: Key }[] = [
  { id: 'today', key: 'rangeToday', hint: 'rangeTodayHint' },
  { id: 'week', key: 'rangeWeek', hint: 'rangeWeekHint' },
  { id: 'date', key: 'rangeDate', hint: 'rangeDateHint' },
]

const iso = (ms: number) => {
  const d = new Date(ms)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

interface Props {
  t: T
  entries: Entry[] // every card this phone knows, up to 7 days, newest first
  demoDays: boolean // fake feed: earlier days are sample data
  lastNote: Entry | null
  onRecord: (id: string) => void
  onAddNote: (label: [string, string], preset: string) => void
  onUndoNote: () => void
  onReceipt: () => void
}

// The whole log as a timeline. One Filter button (what + when) replaces the old chips.
export function ActivityScreen({ t, entries, demoDays, lastNote, onRecord, onAddNote, onUndoNote, onReceipt }: Props) {
  const now = Date.now()
  const [kind, setKind] = useState<Kind>('all')
  const [range, setRange] = useState<Range>('today')
  const [date, setDate] = useState(iso(startOfDay(now, 1)))
  const [filterOpen, setFilterOpen] = useState(false)
  const [addOpen, setAddOpen] = useState(false)
  const [pick, setPick] = useState<string | null>(null)
  const [other, setOther] = useState('')

  const say = (pair: [string, string]) => (t.lang === 'en' ? pair[1] : pair[0])
  const dayName = (back: number) => {
    if (back === 0) return t.one('rangeToday')
    if (back === 1) return t.one('yesterday')
    try {
      return new Date(startOfDay(now, back)).toLocaleDateString(t.lang === 'en' ? 'en-PH' : 'fil-PH', { weekday: 'long', day: 'numeric', month: 'long' })
    } catch {
      return new Date(startOfDay(now, back)).toDateString()
    }
  }

  const pool = entries.filter((e) => {
    const back = daysAgo(e.at, now)
    if (range === 'today') return back === 0
    if (range === 'week') return back >= 0 && back < 7
    return iso(e.at) === date
  })
  const shown = pool.filter(MATCH[kind])
  const grouped = range !== 'today'

  const status = (e: Entry) =>
    e.kind === 'urgent' ? t.one('urgentHead')
      : e.kind === 'seen' ? t.one('seenTitle')
        : e.kind === 'needs' ? t.one('needs')
          : e.kind === 'note' ? t.one('noteWord')
            : t.one('answered')
  const voiceLine = (e: Entry) => {
    const voice = voiceOf(e)
    if (!voice) return ''
    if (voice.type === 'meal') return t.one(mealKey(voice.variant))
    return t.one('voicePlayed', { name: voice.name })
  }
  const sub = (e: Entry) =>
    e.kind === 'needs' && e.count > 1 ? t.one('timesSince', { n: e.count, time: timeInWords(e.firstAt ?? e.at, t.lang) })
      : e.kind === 'answered' && e.savedByYou ? t.one('yourVoiceSaved')
        : e.kind === 'answered' ? voiceLine(e)
          : e.kind === 'seen' ? t.one('seenSub')
            : e.kind === 'note' ? t.one('addedBy') : ''
  const mark = (e: Entry) => (isUrgent(e) ? '▲' : e.kind === 'needs' ? '●' : e.kind === 'note' ? '+' : '✓')
  const node = (e: Entry) => (e.kind === 'urgent' ? 'urgent' : e.kind === 'seen' ? 'seen' : e.kind === 'needs' ? 'needs' : e.kind === 'note' ? 'note' : 'ok')
  const words = (e: Entry) => (e.kind === 'note' && e.label ? say(e.label) : e.transcript)

  const saveNote = () => {
    const preset = PRESETS.find((p) => p.id === pick)
    const label: [string, string] = preset ? preset.label : [other.trim(), other.trim()]
    if (!label[0]) return
    onAddNote(label, preset?.id ?? '')
    setAddOpen(false); setPick(null); setOther('')
  }

  const activeCount = (kind !== 'all' ? 1 : 0) + (range !== 'today' ? 1 : 0)
  const kindInfo = KINDS.find((k) => k.id === kind)!
  const rangeLabel = range === 'date'
    ? (() => { const back = daysAgo(new Date(`${date}T12:00:00`).getTime(), now); return back >= 0 && back < 7 ? dayName(back) : date })()
    : t.one(RANGES.find((r) => r.id === range)!.key)
  const receiptReady = new Date(now).getHours() >= 21

  // rows with a day heading before each new day (when grouped)
  const rows: ReactNode[] = []
  let lastBack = -1
  for (const e of shown) {
    const back = daysAgo(e.at, now)
    if (grouped && back !== lastBack) {
      lastBack = back
      const n = shown.filter((x) => daysAgo(x.at, now) === back).length
      rows.push(<li key={`day-${back}`} className="sn-tl__day"><span>{dayName(back)}</span><small>{t.one('moments', { n })}</small></li>)
    }
    const s = sub(e)
    rows.push(
      <li key={e.id} className="sn-tl__row">
        <span className="sn-tl__time">{timeInWords(e.at, t.lang)}</span>
        <span className={`sn-tl__node sn-tl__node--${node(e)}`} aria-hidden="true">{mark(e)}</span>
        <div className="sn-tl__body">
          <p className={`sn-tl__status${node(e) === 'ok' ? ' sn-tl__status--ok' : ''}`}>{status(e)}</p>
          <p className="sn-tl__quote">“{words(e)}”</p>
          {s ? <p className="sn-tl__sub">{s}</p> : null}
          {e.kind === 'needs' && back === 0 ? (
            <button type="button" className="sn-btn sn-btn--sm" onClick={() => onRecord(e.id)}>{t.btn('record')}</button>
          ) : null}
        </div>
      </li>,
    )
  }

  const hFilter = t.head('filterTitle')
  const hAdd = t.head('addAct')

  return (
    <div className="sn-scroll">
      <div className="sn-hello"><h1 className="sn-greet sn-greet--tight">{t.one('activityTitle')}</h1></div>
      <p className="sn-intro pl">{t.two('activityIntro')}</p>

      <div className="sn-actbar">
        <button type="button" className={`sn-btn${addOpen ? ' is-open' : ''}`} aria-expanded={addOpen}
          onClick={() => { setAddOpen(!addOpen); setPick(null); setOther('') }}><Plus />{t.one('addAct')}</button>
        <button type="button" className="sn-btn sn-btn--quiet" onClick={onReceipt}><Receipt />{t.one('receipt')}</button>
      </div>
      {receiptReady ? <p className="sn-receipt-ready"><span className="sn-check" aria-hidden="true">✓</span><span>{t.one('receiptReady')}</span></p> : null}

      {addOpen ? (
        <section className="sn-addact" aria-label={hAdd.main}>
          <div className="sn-addact__head"><p>{hAdd.main}{hAdd.sub ? <small>{hAdd.sub}</small> : null}</p></div>
          <div className="sn-addact__body">
            <p className="sn-field__label">{t.one('addActPick')}</p>
            <div className="sn-choice">
              {PRESETS.map((p) => (
                <button key={p.id} type="button" aria-pressed={pick === p.id} className={pick === p.id ? 'is-on' : ''}
                  onClick={() => { setPick(pick === p.id ? null : p.id); setOther('') }}>{say(p.label)}</button>
              ))}
            </div>
            <label className="sn-field__label" htmlFor="sn-actnote" style={{ marginTop: 16 }}>{t.one('addActOther')}</label>
            <input id="sn-actnote" className="sn-input" type="text" autoComplete="off" maxLength={120} value={other}
              placeholder={t.one('addActPh')} onChange={(e) => { setOther(e.target.value); setPick(null) }} />
            <p className="sn-tip sn-tip--left">{t.one('addActNow')}</p>
            <div className="sn-row" style={{ marginTop: 16 }}>
              <button type="button" className="sn-btn" disabled={!pick && !other.trim()} onClick={saveNote}>{t.btn('saveAct')}</button>
              <button type="button" className="sn-btn sn-btn--quiet" onClick={() => setAddOpen(false)}>{t.btn('cancel')}</button>
            </div>
          </div>
        </section>
      ) : null}

      {lastNote ? (
        <div className="sn-undo">
          <span>{lastNote.sentToHub ? t.one('loggedHub') : `${t.one('actAdded')}: ${lastNote.label ? say(lastNote.label) : lastNote.transcript}`}</span>
          <button type="button" className="sn-btn sn-btn--quiet" onClick={onUndoNote}>{t.btn('undo')}</button>
        </div>
      ) : null}

      <div className="sn-filterbar">
        <button type="button" className={`sn-filterbtn${filterOpen ? ' is-open' : ''}`} aria-expanded={filterOpen} onClick={() => setFilterOpen(!filterOpen)}>
          <Sliders />{t.one('filter')}{activeCount ? <span className="sn-filter__n">{activeCount}</span> : null}
        </button>
        <div className="sn-activechips">
          {kind !== 'all' ? (
            <span className={`sn-achip sn-achip--${kind}`}>{kindInfo.mark} {t.one(kindInfo.key)}
              <button type="button" aria-label={`${t.one('clearF')}: ${t.one(kindInfo.key)}`} onClick={() => setKind('all')}><X /></button>
            </span>
          ) : null}
          <span className={`sn-achip${range === 'today' ? ' sn-achip--plain' : ''}`}>{rangeLabel}
            {range !== 'today' ? <button type="button" aria-label={`${t.one('clearF')}: ${rangeLabel}`} onClick={() => setRange('today')}><X /></button> : null}
          </span>
        </div>
      </div>

      {filterOpen ? (
        <section className="sn-fpanel" aria-label={hFilter.main}>
          <div className="sn-fpanel__head"><p>{hFilter.main}{hFilter.sub ? <small>{hFilter.sub}</small> : null}</p></div>
          <div className="sn-fpanel__body">
            <p className="sn-fpanel__label">{t.one('filterWhat')}</p>
            <div className="sn-fopts" role="radiogroup" aria-label={t.one('filterWhat')}>
              {KINDS.map((k) => (
                <button key={k.id} type="button" role="radio" aria-checked={kind === k.id}
                  className={`sn-fopt${kind === k.id ? ' is-on' : ''}`} onClick={() => setKind(k.id)}>
                  <span className={`sn-fopt__mark m-${k.id}`} aria-hidden="true">{k.mark}</span>
                  <span className="sn-fopt__label">{t.one(k.key)}</span>
                  <span className="sn-fopt__n">{pool.filter(MATCH[k.id]).length}</span>
                </button>
              ))}
            </div>
            <p className="sn-fpanel__label">{t.one('filterWhen')}</p>
            <div className="sn-fopts" role="radiogroup" aria-label={t.one('filterWhen')}>
              {RANGES.map((r) => (
                <button key={r.id} type="button" role="radio" aria-checked={range === r.id}
                  className={`sn-fopt${range === r.id ? ' is-on' : ''}`} onClick={() => setRange(r.id)}>
                  <span className="sn-fopt__radio" aria-hidden="true">{range === r.id ? '✓' : ''}</span>
                  <span className="sn-fopt__label">{t.one(r.key)}<small>{t.one(r.hint)}</small></span>
                </button>
              ))}
            </div>
            {range === 'date' ? (
              <div className="sn-field">
                <label className="sn-field__label" htmlFor="sn-fdate">{t.one('rangeDate')}</label>
                <input id="sn-fdate" className="sn-input" type="date" value={date}
                  min={iso(startOfDay(now, 6))} max={iso(now)} onChange={(e) => setDate(e.target.value)} />
              </div>
            ) : null}
            <div className="sn-row" style={{ marginTop: 18 }}>
              <button type="button" className="sn-btn" onClick={() => setFilterOpen(false)}>{t.one('showN', { n: shown.length })}</button>
              <button type="button" className="sn-btn sn-btn--quiet" onClick={() => { setKind('all'); setRange('today'); setFilterOpen(false) }}>{t.btn('clearF')}</button>
            </div>
          </div>
        </section>
      ) : null}

      {demoDays && range !== 'today' ? <p className="sn-calm sn-calm--small">{t.one('demoDays')}</p> : null}
      {rows.length ? <ol className="sn-tl">{rows}</ol> : (
        <p className="sn-calm pl">{range === 'date' ? t.two('noDateMoments') : t.two('activityEmpty')}</p>
      )}
    </div>
  )
}
