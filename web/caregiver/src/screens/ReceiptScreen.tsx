import type { Entry } from '../types'
import { dateLine, timeInWords, type T } from '../i18n/i18n'

// Lola's day printed like a torn paper receipt: every moment today, oldest first,
// and the day's totals at the bottom. "Print or save" uses the phone's print sheet
// (on iPhone that can save a PDF or share it). Nothing is sent anywhere.
// Zigzag torn edge, 342 wide: teeth point up (top of the strip) or down (bottom).
const tear = (top: boolean) => {
  const tip = top ? 0 : 12
  const base = top ? 12 : 0
  let d = `M0 ${base} L0 6`
  for (let i = 0; i < 36; i++) d += ` L${(i * 9.5 + 4.75).toFixed(2)} ${tip} L${((i + 1) * 9.5).toFixed(2)} 6`
  return `${d} L342 ${base} Z`
}

export function ReceiptScreen({ t, today }: { t: T; today: Entry[] }) {
  const now = Date.now()
  const rows = [...today].sort((a, b) => a.at - b.at)
  const isUrgent = (e: Entry) => e.kind === 'urgent' || e.kind === 'seen'
  const count = (f: (e: Entry) => boolean) => today.filter(f).length
  const totals = [
    { n: count((e) => e.kind === 'answered'), label: t.one('filterAnswered'), cls: 'sn-total--ok' },
    { n: count((e) => e.kind === 'needs'), label: t.one('filterNeeds'), cls: '' },
    { n: count(isUrgent), label: t.one('filterUrgent'), cls: '' },
    { n: count((e) => e.kind === 'note'), label: t.one('filterAct'), cls: '' },
  ]
  const complete = new Date(now).getHours() >= 21
  const node = (e: Entry) => (e.kind === 'urgent' ? 'urgent' : e.kind === 'seen' ? 'seen' : e.kind === 'needs' ? 'needs' : e.kind === 'note' ? 'note' : 'ok')
  const mark = (e: Entry) => (isUrgent(e) ? '▲' : e.kind === 'needs' ? '●' : e.kind === 'note' ? '+' : '✓')
  const status = (e: Entry) => (isUrgent(e) ? t.one('urgentHead') : e.kind === 'needs' ? t.one('needs') : e.kind === 'note' ? t.one('noteWord') : t.one('answered'))
  const words = (e: Entry) => (e.kind === 'note' && e.label ? (t.lang === 'en' ? e.label[1] : e.label[0]) : e.transcript)

  return (
    <>
      <div className="sn-scroll sn-receipt-wrap">
        <p className="sn-intro pl sn-noprint" style={{ marginTop: 20 }}>{t.two(complete ? 'receiptDone' : 'receiptSoFar')}</p>
        <svg className="sn-tear" viewBox="0 0 342 12" preserveAspectRatio="none" aria-hidden="true"><path d={tear(true)} /></svg>
        <div className="sn-receipt">
          <div className="sn-receipt__head">
            <div><p className="sn-receipt__date">{dateLine(now, t.lang)}</p><p className="sn-receipt__title">{t.one('receiptHead')}</p></div>
            <span className="sn-offline">{t.one('receiptOffline')}</span>
          </div>
          {rows.length ? (
            <ol className="sn-rlist">
              {rows.map((e) => (
                <li key={e.id} className="sn-rrow">
                  <span className="sn-rrow__time">{timeInWords(e.at, t.lang)}</span>
                  <span className={`sn-tl__node sn-tl__node--${node(e)}`} aria-hidden="true">{mark(e)}</span>
                  <div><p className="sn-rrow__kick">{status(e)}</p><p className="sn-rrow__what">“{words(e)}”</p></div>
                </li>
              ))}
            </ol>
          ) : <p className="sn-receipt__empty pl">{t.two('noMoments')}</p>}
          <div className="sn-receipt__total">
            {totals.map((x) => (
              <div key={x.label} className={x.cls}><span className="sn-total__n">{x.n}</span><span className="sn-total__l">{x.label}</span></div>
            ))}
          </div>
          <p className="sn-receipt__thanks pl">{t.two('receiptThanks')}</p>
        </div>
        <svg className="sn-tear sn-tear--bottom" viewBox="0 0 342 12" preserveAspectRatio="none" aria-hidden="true"><path d={tear(false)} /></svg>
        <button type="button" className="sn-btn sn-btn--wide sn-btn--big sn-noprint" style={{ marginTop: 24 }} onClick={() => window.print()}>{t.btn('receiptPrint')}</button>
      </div>
    </>
  )
}
