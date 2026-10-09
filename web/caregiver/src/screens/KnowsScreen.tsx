import { useState } from 'react'
import type { Person, Question } from '../types'
import type { T } from '../i18n/i18n'
import { Heading } from '../components/bits'
import { Trash } from '../components/Icons2'
import { SAFETY_WORDS } from '../data/safetyWords'

interface Props {
  t: T
  questions: Question[] | null
  loadError: string
  people: Person[]
  todayCount: number
  onOpenLog: () => void
}

// "What Sino knows". The hub has no delete route yet, so the trash button only says so
// on screen and deletes nothing (TODO: contract gap, post in the team chat before wiring it).
export function KnowsScreen({ t, questions, loadError, people, todayCount, onOpenLog }: Props) {
  const [cantRemove, setCantRemove] = useState('')
  const colorOf = (name: string) => people.find((p) => p.name === name)?.color ?? 'green'
  const hQ = t.head('questions')
  const hS = t.head('safety')
  const hL = t.head('log')
  return (
    <div className="sn-scroll">
      <div className="sn-hello"><h1 className="sn-greet sn-greet--tight">{t.one('knows')}</h1></div>
      <p className="sn-intro pl">{t.two('knowsIntro')}</p>

      <Heading main={hQ.main} sub={hQ.sub}>{questions ? <span className="sn-tag sn-tag--ink">{questions.length}</span> : null}</Heading>
      {loadError ? <p className="sn-calm pl">{t.two('loadFailed', { why: loadError })}</p> : null}
      {!questions && !loadError ? <p className="sn-calm">{t.one('loading')}</p> : null}
      {cantRemove ? <p className="sn-calm sn-calm--small pl" role="status">{t.two('cantRemove', { q: cantRemove })}</p> : null}
      <div className="sn-stack">
        {(questions ?? []).map((q) => (
          <div className="sn-qcard" key={q.id}>
            <span className={`sn-mini c-${colorOf(q.speaker)}`} aria-hidden="true"><span>{q.speaker[0]?.toUpperCase()}</span></span>
            <div>
              <p className="sn-qcard__q">“{q.question}”</p>
              <div className="sn-qcard__tags">
                <span className={`sn-tag sn-tag--${colorOf(q.speaker)}`}>{q.speaker}</span>
                <span className="sn-tag">{t.one('phrasings', { n: q.phrasings.length })}</span>
              </div>
            </div>
            <button type="button" className="sn-trash" aria-label={t.one('removeQ', { q: q.question })}
              onClick={() => setCantRemove(q.question)}><Trash /></button>
          </div>
        ))}
      </div>

      <Heading main={hS.main} sub={hS.sub} />
      <p className="sn-intro pl sn-intro--tight">{t.two('safetyIntro')}</p>
      <div className="sn-words">
        {SAFETY_WORDS.map((w) => <span className="sn-word-tag" key={w}>▲ {w}</span>)}
      </div>

      <Heading main={hL.main} sub={hL.sub} />
      <div className="sn-logcard">
        <span className="sn-logcard__n">{todayCount}</span>
        <span className="sn-logcard__t"><b>{t.one('logCount')}</b>{t.one('logHint')}</span>
      </div>
      <button type="button" className="sn-btn sn-btn--quiet sn-btn--wide" onClick={onOpenLog}>{t.btn('seeLog')}</button>
    </div>
  )
}
