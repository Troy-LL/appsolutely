import { useState } from 'react'
import type { Person, Question } from '../types'
import type { T } from '../i18n/i18n'
import { Heading } from '../components/bits'
import { Plus, Trash } from '../components/Icons2'
import { addSafetyWord } from '../data/hub'
import { cleanSafetyWord, safetyWordIssue, type SafetyIssue } from '../data/safetyWords'

interface Props {
  t: T
  questions: Question[] | null
  loadError: string
  people: Person[]
  todayCount: number
  onOpenLog: () => void
  builtinWords: string[]
  customWords: string[]
  onAdded: (word: string) => void
}

// "What Sino knows". The hub has no delete route yet, so the trash button only says so
// on screen and deletes nothing (TODO: contract gap, post in the team chat before wiring it).
export function KnowsScreen({ t, questions, loadError, people, todayCount, onOpenLog, builtinWords, customWords, onAdded }: Props) {
  const [cantRemove, setCantRemove] = useState('')
  const [adding, setAdding] = useState(false)
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
        {builtinWords.map((w) => <span className="sn-word-tag" key={w}>▲ {w}</span>)}
        {customWords.map((w) => <span className="sn-word-tag" key={w}>▲ {w}</span>)}
        <button type="button" className="sn-word-tag sn-word-add" aria-label={t.one('addWord')} onClick={() => setAdding(true)}>
          <Plus />
        </button>
      </div>
      {adding ? (
        <AddWordSheet t={t} existing={[...builtinWords, ...customWords]} onClose={() => setAdding(false)} onAdded={onAdded} />
      ) : null}

      <Heading main={hL.main} sub={hL.sub} />
      <div className="sn-logcard">
        <span className="sn-logcard__n">{todayCount}</span>
        <span className="sn-logcard__t"><b>{t.one('logCount')}</b>{t.one('logHint')}</span>
      </div>
      <button type="button" className="sn-btn sn-btn--quiet sn-btn--wide" onClick={onOpenLog}>{t.btn('seeLog')}</button>
    </div>
  )
}

function issueText(t: T, issue: SafetyIssue): string {
  switch (issue) {
    case 'empty':
      return t.two('addWordEmpty')
    case 'short':
      return t.two('addWordShort')
    case 'long':
      return t.two('addWordLong')
    case 'duplicate':
      return t.two('addWordDup')
    default: {
      const _never: never = issue
      return _never
    }
  }
}

function AddWordSheet({ t, existing, onClose, onAdded }: {
  t: T
  existing: string[]
  onClose: () => void
  onAdded: (word: string) => void
}) {
  const [value, setValue] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const save = async () => {
    const issue = safetyWordIssue(value, existing)
    if (issue) {
      setError(issueText(t, issue))
      return
    }
    setSaving(true)
    setError('')
    try {
      const saved = await addSafetyWord(value)
      onAdded(saved === 'fake' ? cleanSafetyWord(value) : saved.word)
      onClose()
    } catch (err) {
      const why = err instanceof Error ? err.message : String(err)
      const known = why === 'empty' || why === 'short' || why === 'long' || why === 'duplicate' ? why : null
      setError(known ? issueText(t, known) : t.two('saveFailed', { why }))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="sn-sheet-bg" onClick={onClose}>
      <div className="sn-sheet" role="dialog" aria-modal="true" aria-labelledby="add-word-title"
        onClick={(e) => e.stopPropagation()}>
        <h2 id="add-word-title" className="sn-sheet__title">{t.btn('addWord')}</h2>
        <form onSubmit={(e) => { e.preventDefault(); void save() }}>
          <label className="sn-field__label" htmlFor="add-word">{t.one('addWordLabel')}</label>
          <input id="add-word" className="sn-input" value={value} autoFocus maxLength={40}
            placeholder={t.one('addWordPh')}
            onChange={(e) => { setValue(e.target.value); setError('') }}
            onKeyDown={(e) => { if (e.key === 'Escape') onClose() }} />
          {error ? <p className="sn-sheet__err pl" role="status">{error}</p> : null}
          <div className="sn-row">
            <button type="submit" className="sn-btn" disabled={saving}>{t.btn('saveWord')}</button>
            <button type="button" className="sn-btn sn-btn--quiet" onClick={onClose}>{t.btn('cancel')}</button>
          </div>
        </form>
      </div>
    </div>
  )
}
