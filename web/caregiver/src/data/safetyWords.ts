// Fallback copy of URGENT_STEMS in brain/decide.py. GET /safety-words replaces this on the hub.
export const SAFETY_WORDS = [
  'natumba', 'nadulas', 'nadapa', 'nahulog', 'bumagsak',
  'masakit', 'sumasakit', 'ang sakit ng dibdib', 'masakit dibdib',
  'di makahinga', 'hindi makahinga', 'hirap huminga', 'nahihirapan huminga',
  'tulungan', 'tulong', 'saklolo',
]

export type SafetyIssue = 'empty' | 'short' | 'long' | 'duplicate'

// Same cleanup decide.normalize does: lower case, punctuation to spaces.
export function cleanSafetyWord(raw: string): string {
  return raw.toLowerCase().replace(/[^\p{L}\p{N}\s]+/gu, ' ').replace(/\s+/g, ' ').trim()
}

export function safetyWordIssue(raw: string, existing: string[]): SafetyIssue | null {
  const word = cleanSafetyWord(raw)
  if (!word) return 'empty'
  const letters = (word.match(/\p{L}/gu) ?? []).length
  if (letters < 4) return 'short'
  if (word.length > 40) return 'long'
  if (existing.includes(word)) return 'duplicate'
  return null
}
