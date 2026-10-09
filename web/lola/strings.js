// strings.js — every word Lola's screen can show, one key per word, with a
// value per language. The screen shows ONE language at a time (chosen by the
// family on the Start sheet), never a "Tagalog / English" pair.
//
// Adding a language (e.g. Bisaya) is local to this file: add a `ceb` value to
// each entry below and list `ceb` in LANGS. No other file needs to change.
// A missing value for the chosen language falls back to `tl`.
//
// Names and reply lines are the family's own words and are NOT in this file;
// they are never translated.

export const LANGS = ['tl', 'en'] // add 'ceb' here (and a ceb: value below) later
export const DEFAULT_LANG = 'tl'

export const STRINGS = {
  // Waiting state — the day-part line, keyed by hour (see dayPartKey).
  dayParts: {
    // Chosen so the sample times verify: 00:05 umaga, 11:59 umaga,
    // 12:30 tanghali, 17:15 hapon, 21:00 gabi.
    umaga:    { tl: 'ng umaga',    en: 'in the morning' },   // hour 0–11
    tanghali: { tl: 'ng tanghali', en: 'at noon' },          // hour 12
    hapon:    { tl: 'ng hapon',    en: 'in the afternoon' },  // hour 13–17
    gabi:     { tl: 'ng gabi',     en: 'in the evening' },    // hour 18–23
  },
  // The reassurance line under the clock.
  waitingReassurance: { tl: 'Nandito lang po kami.', en: "We're right here." },

  // Listening state.
  listening: { tl: 'Nakikinig po ako.', en: "I'm listening." },

  // Start sheet (family only, before Guided Access).
  start:     { tl: 'Simulan', en: 'Start' },
  startHelp: { tl: 'Piliin ang wika, pagkatapos pindutin ang Simulan.', en: 'Choose the language, then press Start.' },

  // The small "practice feed, not the hub" label.
  fake: { tl: 'FAKE', en: 'FAKE' },
}

// Each language's own name, shown on its own button ("Tagalog", "English").
// These are proper names, written the same in any UI language.
export const LANG_NAMES = { tl: 'Tagalog', en: 'English' }

// Look up one string in one language. Falls back to the default language, then
// to any value present, so a half-translated entry never shows blank.
export function t(entry, lang) {
  if (!entry) return ''
  return entry[lang] || entry[DEFAULT_LANG] || entry.tl || entry.en || ''
}

// Pick the day-part key for a given hour (0–23). Boundaries checked at the
// sample times above.
export function dayPartKey(hour) {
  if (hour < 12) return 'umaga'
  if (hour === 12) return 'tanghali'
  if (hour < 18) return 'hapon'
  return 'gabi'
}
