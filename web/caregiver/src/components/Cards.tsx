// The three kinds of moment on the caregiver phone (design system: LogEntry).
// Status is always mark + word + colour.
import type { Entry } from '../types'
import { timeBoth, timeInWords, type T } from '../i18n/i18n'
import { USING_HUB } from '../data/hub'

export function UrgentCard({ t, entry, onRead }: { t: T; entry: Entry; onRead: () => void }) {
  const h = t.head('urgentHead')
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
      </div>
      <div className="sn-urgent__meta">
        <span className="sn-urgent__tag"><i aria-hidden="true">✓</i><span className="pl">{t.two('ipadSame')}</span></span>
      </div>
      {/* docs/sino/design-system.md gap 1: calling is cut, so the one action is "Mark as read" (TODO: Troy) */}
      <button type="button" className="sn-btn sn-btn--wide sn-btn--big" onClick={onRead}>{t.btn('markRead')}</button>
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

export function DoneCard({ t, entry, onUnread }: { t: T; entry: Entry; onUnread: () => void }) {
  const seen = entry.kind === 'seen'
  const sub = seen
    ? t.two('seenSub')
    : entry.savedByYou
      ? t.two(USING_HUB ? 'yourVoiceSaved' : 'fakeSaved')
      : entry.speaker ? t.two('voicePlayed', { name: entry.speaker }) : ''
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
