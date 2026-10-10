// The three kinds of moment on the caregiver phone (design system: LogEntry).
// Status is always mark + word + colour.
import { useEffect, useRef } from 'react'
import type { Entry } from '../types'
import { timeBoth, timeInWords, type T } from '../i18n/i18n'
import { USING_HUB } from '../data/hub'
import { useRecorder } from '../data/recorder'
import { mealKey, voiceOf } from '../feed/events'

export function UrgentCard({ t, entry, onReply }: { t: T; entry: Entry; onReply: (audio?: Blob) => void }) {
  const rec = useRecorder()
  const onReplyRef = useRef(onReply)
  const sentVoice = useRef(false)
  onReplyRef.current = onReply
  useEffect(() => {
    if (sentVoice.current || rec.state !== 'done' || !rec.blob) return
    sentVoice.current = true
    onReplyRef.current(rec.blob)
  }, [rec.state, rec.blob])
  const h = t.head('urgentHead')
  const micLabel = rec.state === 'recording' ? t.btn('stopBtn') : t.btn('recordBtn')
  return (
    <section className="sn-urgent" aria-label={h.main} role="alert">
      <p className="sn-urgent__head">
        <span className="sn-urgent__badge" aria-hidden="true">▲</span>
        <span>{h.main}{h.sub ? <small>{h.sub}</small> : null}</span>
      </p>
      <div className="sn-bubble">
        <div className="sn-bubble__top">
          <p className="sn-bubble__who">{t.one('saidLola')}</p>
          <p className="sn-bubble__time">{timeInWords(entry.at, t.lang)}</p>
        </div>
        <p className="sn-urgent__quote">“{entry.transcript}”</p>
        {entry.alertKind ? <p className="sn-urgent__kind">{entry.alertKind}</p> : null}
      </div>
      <div className="sn-urgent__meta">
        <span className="sn-urgent__tag"><i aria-hidden="true">✓</i><span className="pl">{t.two('ipadSame')}</span></span>
      </div>
      <button type="button" className="sn-btn sn-btn--wide sn-btn--big" onClick={() => onReply()}>{t.btn('onMyWay')}</button>
      <button type="button" className="sn-btn sn-btn--wide" style={{ marginTop: 10 }}
        onClick={() => (rec.state === 'recording' ? rec.stop() : void rec.start())}>{micLabel}</button>
    </section>
  )
}

export function NeedsCard({ t, entry, onRecord }: { t: T; entry: Entry; onRecord: () => void }) {
  return (
    <li className="sn-entry sn-entry--needs">
      <div className="sn-entry__row">
        <p className="sn-entry__status"><span className="sn-dot" aria-hidden="true" />{t.one('askedLola')}</p>
        <p className="sn-entry__time">{timeInWords(entry.at, t.lang)}</p>
      </div>
      <p className="sn-entry__quote">“{entry.transcript}”</p>
      {entry.count > 1 ? <p className="sn-entry__sub pl">{t.two('timesSince', { n: entry.count, time: timeBoth(entry.firstAt ?? entry.at) })}</p> : <div style={{ height: 8 }} />}
      <button type="button" className="sn-btn sn-btn--wide sn-btn--big" onClick={onRecord}>{t.btn('record')}</button>
    </li>
  )
}

export function answeredLine(t: T, entry: Entry): string {
  if (entry.kind === 'seen') return t.two('seenSub')
  if (entry.savedByYou) return t.two(USING_HUB ? 'yourVoiceSaved' : 'fakeSaved')
  const voice = voiceOf(entry)
  if (!voice) return ''
  if (voice.type === 'meal') return t.two(mealKey(voice.variant))
  return t.two('voicePlayed', { name: voice.name })
}

export function DoneCard({ t, entry, onUnread }: { t: T; entry: Entry; onUnread: () => void }) {
  const seen = entry.kind === 'seen'
  const sub = answeredLine(t, entry)
  return (
    <li className={`sn-entry${seen ? '' : ' sn-entry--ok'}`}>
      <div className="sn-entry__row">
        {seen ? (
          <p className="sn-entry__status">▲ {t.one('seenTitle')}</p>
        ) : (
          <p className="sn-entry__status sn-ok"><span className="sn-check" aria-hidden="true">✓</span>{t.one('answered')}</p>
        )}
        <p className="sn-entry__time">{timeInWords(entry.at, t.lang)}</p>
      </div>
      <p className="sn-entry__what">“{entry.transcript}”</p>
      {sub ? <p className="sn-entry__sub pl">{sub}</p> : null}
      {seen ? <button type="button" className="sn-btn sn-btn--quiet sn-btn--sm" onClick={onUnread}>{t.btn('undo')}</button> : null}
    </li>
  )
}
