// Fake-feed stand-in for brain/ask.py (answer_about_lola), so Sino AI works without the hub.
// Same idea: counts and her exact words from today's cards, and no room is ever guessed
// (no camera). Never a diagnosis or a mood. On the real hub, ask.py answers instead.
import type { AskIntent, Entry } from '../types'
import { timeBoth, type T } from '../i18n/i18n'

// Typed questions: pick the intent from a few words. (ask.py uses rules first, then Qwen.)
export function intentOf(text: string): AskIntent {
  const x = ` ${text.toLowerCase().replace(/[^a-z0-9ñ ]+/g, ' ')} `
  const has = (words: string[]) => words.some((w) => x.includes(` ${w}`))
  if (has(['nasaan', 'asan', 'saan', 'where'])) return 'where'
  if (has(['kumain', 'kain', 'ate ', 'eat', 'meal', 'almusal', 'tanghalian', 'hapunan', 'breakfast', 'lunch', 'dinner'])) return 'ate'
  if (has(['sinabi', 'sabi', 'tanong', 'tinanong', 'saying', 'said', 'asking', 'asked', 'words'])) return 'saying'
  if (has(['kamusta', 'kumusta', 'how', 'lagay'])) return 'how'
  return 'unknown'
}

// `today` = today's cards only.
export function answerLocally(intent: AskIntent, today: Entry[], t: T): string {
  if (intent === 'where') return t.two('askWhereAnswer')
  if (intent === 'unknown') return t.two('askNoAnswer')
  if (intent === 'ate') {
    const meal = today.find((e) => e.kind === 'note' && e.preset === 'ate')
    return meal ? t.two('askAteYes', { time: timeBoth(meal.at) }) : t.two('askAteNo')
  }
  const spoken = today.filter((e) => e.kind !== 'note')
  if (!spoken.length) return t.two('askNothingYet')
  if (intent === 'how') {
    const ok = spoken.filter((e) => e.kind === 'answered').length
    const needs = spoken.filter((e) => e.kind === 'needs').length
    const urgent = spoken.filter((e) => e.kind === 'urgent' || e.kind === 'seen').length
    const asked = spoken.reduce((n, e) => n + (e.kind === 'needs' ? e.count : 1), 0)
    return t.two('askHowAnswer', { asked, ok, needs, urgent })
  }
  const words = [...spoken]
    .sort((a, b) => b.count - a.count)
    .slice(0, 5)
    .map((e) => `“${e.transcript}”${e.count > 1 ? ` ×${e.count}` : ''}`)
    .join(', ')
  return t.two('askSayingAnswer', { words })
}

// The quick questions. The Tagalog wording matches the rules in brain/ask.py.
export const ASK_QUESTIONS: { intent: AskIntent; tl: string; en: string }[] = [
  { intent: 'how', tl: 'Kamusta si Lola?', en: 'How is Lola?' },
  { intent: 'saying', tl: 'Ano mga tanong niya?', en: 'What has she been asking?' },
  { intent: 'where', tl: 'Nasaan si Lola?', en: 'Where is Lola?' },
]
