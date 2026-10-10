import type { T } from './i18n'

export type Pair = { readonly tl: string; readonly en: string }

export const copy = {
  addFace: { tl: 'Magdagdag ng mukha', en: 'Add face' },
  title: { tl: 'Mukha ni {name}', en: "{name}'s face" },
  straight: { tl: 'Tumingin nang diretso', en: 'Look straight' },
  left: { tl: 'Bahagyang lumingon sa kaliwa', en: 'Turn slightly left' },
  right: { tl: 'Bahagyang lumingon sa kanan', en: 'Turn slightly right' },
  chin: { tl: 'Itaas nang kaunti ang baba', en: 'Chin up a little' },
  smile: { tl: 'Ngumiti', en: 'Smile' },
  missing: {
    tl: 'Hindi pa handa ang mukha ni Sino.',
    en: "Sino's face match is not on this hub yet.",
  },
  privacy: { tl: 'Dito lang sa bahay ang mga litrato.', en: 'These frames stay on the hub.' },
  retake: { tl: 'Ulitin', en: 'Try again' },
  choose: { tl: 'Pumili ng litrato', en: 'Choose photos' },
  doneLine: { tl: 'Kilala na ni Sino si {name}', en: 'Sino knows {name} now.' },
  doneBtn: { tl: 'Tapos', en: 'Done' },
  denied: {
    tl: 'Sarado muna ang camera. Pumili ng litrato.',
    en: 'The camera is off for now. Choose photos.',
  },
  loading: { tl: 'Sandali lang.', en: 'One moment.' },
  kept: { tl: '{n} litrato ang naitago.', en: '{n} photos were kept.' },
} as const

function fill(s: string, vars?: Record<string, string | number>): string {
  if (!vars) return s
  return s.replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k] ?? ''))
}

export function say(t: T, pair: Pair, vars?: Record<string, string | number>): string {
  const a = fill(pair.tl, vars)
  const b = fill(pair.en, vars)
  if (t.lang === 'en') return b
  if (t.lang === 'tl') return a
  return `${a}\n${b}`
}

export function slash(t: T, pair: Pair): string {
  if (t.lang === 'en') return pair.en
  if (t.lang === 'tl') return pair.tl
  return `${pair.tl} / ${pair.en}`
}

export function head(t: T, pair: Pair, vars?: Record<string, string | number>): { main: string; sub: string } {
  const a = fill(pair.tl, vars)
  const b = fill(pair.en, vars)
  if (t.lang === 'en') return { main: b, sub: '' }
  if (t.lang === 'tl') return { main: a, sub: '' }
  return { main: a, sub: b }
}
