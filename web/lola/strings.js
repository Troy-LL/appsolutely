// strings.js — every word Lola's screen can show, in Tagalog + English.
// Nothing user-visible is hardcoded in the HTML or in lola.js. If a string
// is missing here, it does not appear on screen.
//
// Pairs are written "Tagalog / English" the way the design system asks
// ("Nandito lang po kami. / We're right here."). The screen shows the whole
// pair; it does not pick one language.

export const STRINGS = {
  // Waiting state.
  // The day-part line reads: "<dayPart.tl> / <dayPart.en>".
  dayParts: {
    // Chosen so the sample times verify as asked:
    //   00:05 -> umaga, 11:59 -> umaga, 12:30 -> tanghali,
    //   17:15 -> hapon, 21:00 -> gabi.
    umaga:    { tl: 'ng umaga',    en: 'in the morning' },   // hour 0–11
    tanghali: { tl: 'ng tanghali', en: 'at noon' },          // hour 12
    hapon:    { tl: 'ng hapon',    en: 'in the afternoon' },  // hour 13–17
    gabi:     { tl: 'ng gabi',     en: 'in the evening' },    // hour 18–23
  },
  // The reassurance line under the clock.
  waitingReassurance: { tl: 'Nandito lang po kami.', en: "We're right here." },

  // Listening state.
  listening: { tl: 'Nakikinig po ako.', en: "I'm listening." },

  // Start sheet. The only button on the whole screen.
  start: { tl: 'Simulan', en: 'Start' },

  // The small "this is the practice feed, not the hub" label.
  fake: { tl: 'FAKE', en: '' },
}

// Join a {tl, en} pair into one display string: "Tagalog / English".
// If one side is empty (like the FAKE label's en), show just the other.
export function pair(s) {
  if (!s) return ''
  if (s.tl && s.en) return `${s.tl} / ${s.en}`
  return s.tl || s.en || ''
}

// Pick the day-part key for a given hour (0–23).
// Boundaries are documented above and checked at the sample times.
export function dayPartKey(hour) {
  if (hour < 12) return 'umaga'
  if (hour === 12) return 'tanghali'
  if (hour < 18) return 'hapon'
  return 'gabi'
}
