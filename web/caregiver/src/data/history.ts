// Phone-only notes (a walk, not a meal) stay on this phone. Decisions, meals, and
// urgent cards come from GET /log. On the fake feed the earlier days are sample data.
import type { Entry } from '../types'

const KEY = 'sino.caregiver.log.v1'
export const KEEP_DAYS = 7
export const DAY = 24 * 60 * 60 * 1000

export function startOfDay(ms: number, back = 0): number {
  const d = new Date(ms)
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() - back)
  return d.getTime()
}

// Whole days between the day of `ms` and today (0 = today).
export function daysAgo(ms: number, now = Date.now()): number {
  return Math.round((startOfDay(now) - startOfDay(ms)) / DAY)
}

export function loadSaved(): Entry[] {
  try {
    const raw = localStorage.getItem(KEY)
    const list = raw ? (JSON.parse(raw) as Entry[]) : []
    const oldest = startOfDay(Date.now(), KEEP_DAYS - 1)
    return Array.isArray(list) ? list.filter((e) => e && typeof e.at === 'number' && e.at >= oldest) : []
  } catch {
    return []
  }
}

export function save(entries: Entry[]) {
  try {
    const oldest = startOfDay(Date.now(), KEEP_DAYS - 1)
    localStorage.setItem(KEY, JSON.stringify(entries.filter((e) => e.at >= oldest)))
  } catch {
    /* storage full or blocked: the log still works for this session */
  }
}

// Sample earlier days for the fake feed. Lola's words come from brain/seed.json.
export function demoHistory(now = Date.now()): Entry[] {
  const at = (back: number, h: number, m: number) => startOfDay(now, back) + (h * 60 + m) * 60 * 1000
  const e = (id: string, back: number, h: number, m: number, kind: Entry['kind'], transcript: string, extra: Partial<Entry> = {}): Entry =>
    ({ id: `demo-${id}`, kind, transcript, at: at(back, h, m), count: 1, ...extra })
  return [
    e('1', 1, 18, 40, 'answered', 'Nasaan si Nanay?', { speaker: 'Joy' }),
    e('2', 1, 12, 10, 'note', 'Kumain', { label: ['Kumain', 'Ate a meal'], preset: 'ate' }),
    e('3', 1, 9, 20, 'answered', 'Sino ka?', { speaker: 'Troy' }),
    e('4', 2, 15, 5, 'needs', 'Nasaan yung aso?', { count: 2 }),
    e('5', 2, 10, 45, 'answered', 'Si Mama asan?', { speaker: 'Joy' }),
    e('6', 3, 19, 15, 'seen', 'Nahulog ako'),
    e('7', 3, 17, 0, 'note', 'Naglakad', { label: ['Naglakad', 'Went for a walk'], preset: 'walk' }),
    e('8', 5, 16, 20, 'answered', 'Nasaan si Joy?', { speaker: 'Joy' }),
    e('9', 6, 14, 30, 'needs', 'Gusto ko nang umuwi'),
  ]
}
