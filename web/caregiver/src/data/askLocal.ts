// Fake-feed stand-in for brain/ask.py (answer_about_lola), so Sino AI works without the hub.
// Same idea: counts and her exact words from today's cards, and no room is ever guessed
// (no camera). Never a diagnosis or a mood. On the real hub, ask.py answers instead.
import type { AskIntent, Entry } from '../types'
import { timeBoth, type T } from '../i18n/i18n'

// Typed questions: pick the intent from a few words. (ask.py uses rules first, then Qwen.)
export function intentOf(text: string): AskIntent {
  const x = ` ${text.toLowerCase().replace(/[^a-z0-9ñ ]+/g, ' ')} `
  const has = (words: string[]) => words.some((w) => x.includes(` ${w}`))
  if (has(['kumain', 'nakakain', 'kinain', 'kumakain', 'kain', 'kumaen', 'eaten', 'eat', 'ate', 'meal', 'almusal', 'tanghalian', 'hapunan', 'breakfast', 'lunch', 'dinner'])) return 'ate'
  if (has(['nasaan', 'asan', 'saan', 'where'])) return 'where'
  if (has(['sinabi', 'sabi', 'tanong', 'tinanong', 'saying', 'said', 'asking', 'asked', 'words'])) return 'saying'
  if (has(['kamusta', 'kumusta', 'how', 'lagay'])) return 'how'
  return 'unknown'
}

const PROFANITY = /\b(shit|fuck|fucking|puta|putangina|gago|tangina|bitch)\b/i
const SAFETY = /\b(tulong|saklolo|tulungan|masakit|help)\b/i
const TAGALOG = new Set(['si', 'ang', 'ng', 'mga', 'ba', 'na', 'po', 'ano', 'nasaan', 'asan', 'saan', 'niya', 'siya', 'kamusta', 'kumusta', 'sa', 'yung', 'ako', 'ko', 'nang'])

function junkLine(entry: Entry): boolean {
  const text = entry.transcript
  const words = text.trim().split(/\s+/).filter(Boolean)
  if (words.length <= 2 && !SAFETY.test(text) && !entry.replyId) return true
  if (PROFANITY.test(text)) return true
  const tokens = text.toLowerCase().replace(/[^a-zñ\s]/g, ' ').split(/\s+/).filter(Boolean)
  if (tokens.length < 3) return false
  const tagalog = tokens.filter((word) => TAGALOG.has(word)).length
  if (tagalog >= 2) return false
  const ascii = tokens.filter((word) => /^[a-z]+$/.test(word)).length
  return ascii / tokens.length >= 0.6
}

function spokenLines(today: Entry[]): Entry[] {
  return today.filter((entry) => entry.kind !== 'note' && !junkLine(entry))
}

// `today` = today's cards only.
export function answerLocally(intent: AskIntent, today: Entry[], t: T): string {
  if (intent === 'where') return t.two('askWhereAnswer')
  if (intent === 'unknown') return `${t.two('askNoAnswer')} ${t.two('askChips')}`
  if (intent === 'ate') {
    const meal = today.find((e) => e.kind === 'note' && e.preset === 'ate')
    return meal ? t.two('askAteYes', { time: timeBoth(meal.at) }) : t.two('askAteNo')
  }
  const spoken = spokenLines(today)
  const meal = today.find((e) => e.kind === 'note' && e.preset === 'ate')
  const mealLine = meal ? t.two('askAteYes', { time: timeBoth(meal.at) }) : t.two('askAteNo')
  if (!spoken.length && intent === 'how') return `${t.two('askNothingYet')} ${mealLine}`
  if (!spoken.length) return t.two('askNothingYet')
  if (intent === 'how') {
    const ok = spoken.filter((e) => e.kind === 'answered').length
    const needs = spoken.filter((e) => e.kind === 'needs').length
    const urgent = spoken.filter((e) => e.kind === 'urgent' || e.kind === 'seen').length
    const asked = spoken.reduce((n, e) => n + (e.kind === 'needs' ? e.count : 1), 0)
    return `${t.two('askHowAnswer', { asked, ok, needs, urgent })} ${mealLine}`
  }
  const groups = new Map<string, { text: string; count: number }>()
  for (const entry of spoken) {
    const key = entry.transcript.trim()
    const add = entry.kind === 'needs' ? entry.count : 1
    const prev = groups.get(key)
    if (prev) prev.count += add
    else groups.set(key, { text: entry.transcript, count: add })
  }
  const repeated = [...groups.values()].filter((group) => group.count > 1).sort((a, b) => b.count - a.count).slice(0, 5)
  if (!repeated.length) return t.two('askNoRepeat')
  const items = repeated.map((group) => `• ${group.text} — ${group.count}`).join('\n')
  return `${t.two('askSayingIntro')}\n${items}`
}

// The quick questions. The Tagalog wording matches the rules in brain/ask.py.
export const ASK_QUESTIONS: { intent: AskIntent; tl: string; en: string }[] = [
  { intent: 'how', tl: 'Kamusta si Lola?', en: 'How is Lola?' },
  { intent: 'saying', tl: 'Ano mga tanong niya?', en: 'What has she been asking?' },
  { intent: 'where', tl: 'Nasaan si Lola?', en: 'Where is Lola?' },
]
