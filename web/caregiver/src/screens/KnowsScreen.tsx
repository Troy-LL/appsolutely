import { useRef, useState, type PointerEvent } from 'react'
import type { Person, Question } from '../types'
import type { T } from '../i18n/i18n'
import { Heading } from '../components/bits'
import { Plus, Trash } from '../components/Icons2'
import { addSafetyWord, isBuiltIn } from '../data/hub'
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
  onRemove: (id: string) => Promise<void>
}

export function KnowsScreen({
  t, questions, loadError, people, todayCount, onOpenLog, builtinWords, customWords, onAdded, onRemove,
}: Props) {
  const [armed, setArmed] = useState('')
  const [pressed, setPressed] = useState('')
  const [noteId, setNoteId] = useState('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [adding, setAdding] = useState(false)
  const pressedId = useRef('')
  const fromTouch = useRef(false)
  const colorOf = (name: string) => people.find((p) => p.name === name)?.color ?? 'green'
  const hQ = t.head('questions')
  const hS = t.head('safety')
  const hL = t.head('log')

  async function commit(q: Question) {
    if (busy) return
    setArmed('')
    setPressed('')
    pressedId.current = ''
    if (isBuiltIn(q.id)) {
      setNoteId(q.id)
      setNote(t.two('deleteKept'))
      return
    }
    setBusy(true)
    setNoteId('')
    try {
      await onRemove(q.id)
    } catch (err) {
      const why = err instanceof Error ? err.message : String(err)
      setNoteId(q.id)
      setNote(why.includes('built-in') ? t.two('deleteKept') : t.two('deleteFailed', { why }))
    } finally {
      setBusy(false)
    }
  }

  function armOrDelete(q: Question) {
    if (busy) return
    if (armed === q.id) {
      void commit(q)
      return
    }
    setNoteId('')
    setArmed(q.id)
  }

  function onPointerDown(e: PointerEvent<HTMLButtonElement>, id: string) {
    if (e.pointerType === 'mouse') fromTouch.current = false
    if (e.pointerType === 'mouse' && e.button !== 0) return
    if (e.pointerType !== 'mouse') e.preventDefault()
    try {
      e.currentTarget.setPointerCapture(e.pointerId)
    } catch {
      /* pointer already gone */
    }
    pressedId.current = id
    setPressed(id)
  }

  function onPointerUp(e: PointerEvent<HTMLButtonElement>, q: Question) {
    const hot = pressedId.current === q.id
    pressedId.current = ''
    setPressed('')
    if (e.pointerType === 'mouse' || !hot) return
    fromTouch.current = true
    armOrDelete(q)
  }

  function onClick(q: Question) {
    if (fromTouch.current) {
      fromTouch.current = false
      return
    }
    armOrDelete(q)
  }

  return (
    <div className="sn-scroll">
      <div className="sn-hello"><h1 className="sn-greet sn-greet--tight">{t.one('knows')}</h1></div>
      <p className="sn-intro pl">{t.two('knowsIntro')}</p>

      <Heading main={hQ.main} sub={hQ.sub}>{questions ? <span className="sn-tag sn-tag--ink">{questions.length}</span> : null}</Heading>
      {loadError ? <p className="sn-calm pl">{t.two('loadFailed', { why: loadError })}</p> : null}
      {!questions && !loadError ? <p className="sn-calm">{t.one('loading')}</p> : null}
      <div className="sn-stack">
        {(questions ?? []).map((q) => {
          const hot = pressed === q.id || armed === q.id
          return (
            <div className="sn-qcard" key={q.id}>
              <span className={`sn-mini c-${colorOf(q.speaker)}`} aria-hidden="true"><span>{q.speaker[0]?.toUpperCase()}</span></span>
              <div className="sn-qcard__main">
                <p className="sn-qcard__q">“{q.question}”</p>
                <div className="sn-qcard__tags">
                  <span className={`sn-tag sn-tag--${colorOf(q.speaker)}`}>{q.speaker}</span>
                  <span className="sn-tag">{t.one('phrasings', { n: q.phrasings.length })}</span>
                </div>
              </div>
              <button
                type="button"
                className={hot ? 'sn-trash is-hot' : 'sn-trash'}
                aria-pressed={armed === q.id}
                aria-label={armed === q.id ? t.btn('deleteAsk') : t.one('removeQ', { q: q.question })}
                onPointerDown={(e) => onPointerDown(e, q.id)}
                onPointerUp={(e) => onPointerUp(e, q)}
                onPointerCancel={() => { pressedId.current = ''; setPressed('') }}
                onClick={() => onClick(q)}
              ><Trash /></button>
              {armed === q.id ? (
                <div className="sn-qcard__confirm" role="status">
                  <button type="button" className="sn-qcard__go" onClick={() => void commit(q)}>{t.btn('deleteAsk')}</button>
                  <button type="button" className="sn-btn sn-btn--quiet sn-btn--sm" onClick={() => setArmed('')}>{t.btn('cancel')}</button>
                </div>
              ) : null}
              {noteId === q.id && note ? <p className="sn-qcard__note" role="status">{note}</p> : null}
            </div>
          )
        })}
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
