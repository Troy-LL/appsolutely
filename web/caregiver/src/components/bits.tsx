import type { ReactNode } from "react"
// Small shared pieces: section headings, the language options, text size, waveform.
import type { Lang, Scale } from '../types'
import type { T } from '../i18n/i18n'
import { BAR_COUNT } from '../data/recorder'

export function Heading({ main, sub, as: Tag = 'h2', children }: { main: string; sub?: string; as?: 'h1' | 'h2' | 'h3'; children?: ReactNode }) {
  return (
    <div className="sn-sec">
      <Tag className="sn-title">{main}{sub ? <small>{sub}</small> : null}</Tag>
      {children}
    </div>
  )
}

export function LangOptions({ t, lang, onPick }: { t: T; lang: Lang; onPick: (l: Lang) => void }) {
  const opts: { id: Lang; label: string; hint: string }[] = [
    { id: 'tl', label: 'Tagalog', hint: t.one('langTl') },
    { id: 'en', label: 'English', hint: t.one('langEn') },
    { id: 'both', label: 'Pareho · Both', hint: t.one('langBoth') },
  ]
  return (
    <div className="sn-seg" role="radiogroup" aria-label={t.one('lang')}>
      {opts.map((o) => (
        <button key={o.id} type="button" role="radio" aria-checked={lang === o.id}
          className={`sn-opt${lang === o.id ? ' is-on' : ''}`} onClick={() => onPick(o.id)}>
          <span>{o.label}<small>{o.hint}</small></span>
          <span className="sn-opt__mark" aria-hidden="true">{lang === o.id ? '✓' : ''}</span>
        </button>
      ))}
    </div>
  )
}

export function TextScale({ scale, onPick }: { scale: Scale; onPick: (s: Scale) => void }) {
  return (
    <div className="sn-scale">
      {(['A', 'A+', 'A++'] as const).map((label, i) => (
        <button key={label} type="button" aria-pressed={scale === i}
          className={`sn-btn${scale === i ? ' is-pressed' : ''}`} onClick={() => onPick(i as Scale)}>{label}</button>
      ))}
    </div>
  )
}

// Recorded part fills green. Heights follow the live loudness; idle shows flat bars.
export function Waveform({ levels }: { levels: number[] }) {
  const bars = Array.from({ length: BAR_COUNT }, (_, i) => levels[i])
  return (
    <div className="sn-wave" aria-hidden="true">
      {bars.map((v, i) => (
        <span key={i} className={v === undefined ? '' : 'is-heard'} style={{ height: `${v === undefined ? 14 : 12 + v * 46}px` }} />
      ))}
    </div>
  )
}
