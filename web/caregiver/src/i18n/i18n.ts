import { tl } from './tl'
import { en } from './en'
import type { Lang } from '../types'

export type Key = keyof typeof tl
// A value can be one string for both languages, or [Tagalog, English].
type Vars = Record<string, string | number | [string, string]>

const fill = (s: string, i: 0 | 1, v?: Vars) =>
  v ? s.replace(/\{(\w+)\}/g, (_, k: string) => { const x = v[k]; return Array.isArray(x) ? x[i] : String(x ?? '') }) : s

// Helpers for the three language modes.
//   one(): a single line (Tagalog in "both" mode). For headings, labels, chips.
//   two(): both languages on two lines in "both" mode. For sentences.
//   btn(): "Tagalog / English" in "both" mode. For buttons.
//   head(): { main, sub } so a heading can show English small under it.
export function makeT(lang: Lang) {
  const pick = (k: Key, v?: Vars) => ({ a: fill(tl[k], 0, v), b: fill(en[k], 1, v) })
  return {
    lang,
    one: (k: Key, v?: Vars) => (lang === 'en' ? pick(k, v).b : pick(k, v).a),
    two: (k: Key, v?: Vars) => {
      const p = pick(k, v)
      return lang === 'tl' ? p.a : lang === 'en' ? p.b : `${p.a}\n${p.b}`
    },
    btn: (k: Key, v?: Vars) => {
      const p = pick(k, v)
      return lang === 'tl' ? p.a : lang === 'en' ? p.b : `${p.a} / ${p.b}`
    },
    head: (k: Key, v?: Vars) => {
      const p = pick(k, v)
      return lang === 'tl' ? { main: p.a, sub: '' } : lang === 'en' ? { main: p.b, sub: '' } : { main: p.a, sub: p.b }
    },
  }
}
export type T = ReturnType<typeof makeT>

// Times are written in words, never "PM" (design system: Content fundamentals).
export function timeInWords(ms: number, lang: Lang): string {
  const d = new Date(ms)
  const h = d.getHours()
  const clock = `${h % 12 || 12}:${String(d.getMinutes()).padStart(2, '0')}`
  const tlPart = h < 5 ? 'ng madaling-araw' : h < 12 ? 'ng umaga' : h < 13 ? 'ng tanghali' : h < 18 ? 'ng hapon' : 'ng gabi'
  const enPart = h < 5 ? 'early in the morning' : h < 12 ? 'in the morning' : h < 13 ? 'at noon' : h < 18 ? 'in the afternoon' : 'in the evening'
  return `${clock} ${lang === 'en' ? enPart : tlPart}`
}

// Both spellings of a time, for strings that mention one.
export const timeBoth = (ms: number): [string, string] => [timeInWords(ms, 'tl'), timeInWords(ms, 'en')]

export function greetingKey(ms: number): Key {
  const h = new Date(ms).getHours()
  return h < 12 ? 'greetMorning' : h < 13 ? 'greetNoon' : h < 18 ? 'greetAfternoon' : 'greetEvening'
}

export function dateLine(ms: number, lang: Lang): string {
  const locale = lang === 'en' ? 'en-PH' : 'fil-PH'
  try {
    return new Date(ms).toLocaleDateString(locale, { weekday: 'long', day: 'numeric', month: 'long' })
  } catch {
    return new Date(ms).toDateString()
  }
}
