// The two chips under the sala card. Each opens a small panel with what it counts.
import type { Entry } from '../types'
import { timeInWords, type T } from '../i18n/i18n'
import { Caret, Close } from './Icons'

interface Props {
  t: T
  answered: Entry[]
  needs: Entry[]
  open: 'ok' | 'needs' | null
  setOpen: (w: 'ok' | 'needs' | null) => void
  onRecord: (id: string) => void
}

export function SummaryChips({ t, answered, needs, open, setOpen, onRecord }: Props) {
  const toggle = (w: 'ok' | 'needs') => setOpen(open === w ? null : w)
  const hAns = t.head('answeredToday')
  const hNeeds = t.head('needs')
  return (
    <>
      <div className="sn-chips">
        <button type="button" className={`sn-chip sn-chip--ok${open === 'ok' ? ' is-open' : ''}`}
          onClick={() => toggle('ok')} aria-expanded={open === 'ok'}>
          ✓ {t.one('chipAnswered', { n: answered.length })}<Caret open={open === 'ok'} />
        </button>
        {needs.length ? (
          <button type="button" className={`sn-chip sn-chip--needs${open === 'needs' ? ' is-open' : ''}`}
            onClick={() => toggle('needs')} aria-expanded={open === 'needs'}>
            <span className="sn-dot sn-dot--paper" aria-hidden="true" />{t.one('chipNeeds', { n: needs.length })}<Caret open={open === 'needs'} />
          </button>
        ) : (
          <span className="sn-chip sn-chip--calm">{t.one('allCalm')}</span>
        )}
      </div>

      {open === 'ok' ? (
        <section className="sn-widget" aria-label={hAns.main}>
          <div className="sn-widget__head sn-widget__head--ok">
            <p>✓ {hAns.main}{hAns.sub ? <small>{hAns.sub}</small> : null}</p>
            <button type="button" className="sn-widget__close" onClick={() => setOpen(null)} aria-label={t.one('close')}><Close /></button>
          </div>
          {answered.length ? (
            <ul>
              {answered.map((e) => (
                <li key={e.id}>
                  <span className="sn-widget__time">{timeInWords(e.at, t.lang)}</span>
                  <div>
                    <p className="sn-widget__q">“{e.transcript}”</p>
                    {e.speaker ? <p className="sn-widget__who">{t.one('voicePlayed', { name: e.speaker })}</p> : null}
                  </div>
                </li>
              ))}
            </ul>
          ) : <p className="sn-widget__empty pl">{t.two('noMoments')}</p>}
          <div className="sn-widget__foot"><p className="sn-widget__who pl">{t.two('answeredFoot')}</p></div>
        </section>
      ) : null}

      {open === 'needs' ? (
        <section className="sn-widget" aria-label={hNeeds.main}>
          <div className="sn-widget__head sn-widget__head--needs">
            <p>{hNeeds.main}{hNeeds.sub ? <small>{hNeeds.sub}</small> : null}</p>
            <button type="button" className="sn-widget__close" onClick={() => setOpen(null)} aria-label={t.one('close')}><Close /></button>
          </div>
          <ul>
            {needs.map((e) => (
              <li key={e.id}>
                <span className="sn-widget__time">{timeInWords(e.at, t.lang)}</span>
                <div>
                  <p className="sn-widget__q">“{e.transcript}”</p>
                  <button type="button" className="sn-btn sn-btn--sm sn-widget__act" onClick={() => onRecord(e.id)}>{t.btn('record')}</button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </>
  )
}
