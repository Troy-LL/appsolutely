const FAMILY = ['troy', 'joy', 'donita'] as const
export type FacePersonId = (typeof FAMILY)[number]

export function faceId(name: string): FacePersonId | null {
  const last = name.trim().split(/\s+/).pop()?.toLowerCase() ?? ''
  for (const id of FAMILY) if (id === last) return id
  return null
}

export function photoFor(
  name: string,
  questions: { speaker?: string; photo?: string; by_person?: Record<string, { photo?: string }> }[] | null,
): string {
  const id = faceId(name)
  if (id && questions) {
    for (const q of questions) {
      const photo = q.by_person?.[id]?.photo
      if (photo) return photo
    }
  }
  for (const q of questions ?? []) {
    if (q.speaker === name && q.photo) return q.photo
  }
  return ''
}

export interface EnrollFrame {
  ok: boolean
  reason?: string
}

export interface EnrollResult {
  person?: string
  engine?: string
  frames: EnrollFrame[]
  count?: number
}

export const OVAL_VAR_MIN = 64
export const STILL_MAD_MAX = 12
export const STILL_MS = 400

export function lumaVariance(samples: ArrayLike<number>): number {
  const n = samples.length
  if (n < 8) return 0
  let sum = 0
  for (let i = 0; i < n; i++) sum += samples[i]
  const mean = sum / n
  let acc = 0
  for (let i = 0; i < n; i++) {
    const d = samples[i] - mean
    acc += d * d
  }
  return acc / n
}

export function meanAbsDiff(a: ArrayLike<number>, b: ArrayLike<number>): number {
  if (a.length === 0 || a.length !== b.length) return Number.POSITIVE_INFINITY
  let sum = 0
  for (let i = 0; i < a.length; i++) sum += Math.abs(a[i] - b[i])
  return sum / a.length
}

export function ovalLumas(data: Uint8ClampedArray, w: number, h: number): Float32Array {
  const cx = (w - 1) / 2
  const cy = (h - 1) / 2
  const rx = w * 0.28
  const ry = h * 0.36
  const bucket: number[] = []
  for (let y = 0; y < h; y += 2) {
    const ny = (y - cy) / ry
    const ny2 = ny * ny
    if (ny2 > 1) continue
    const row = y * w
    for (let x = 0; x < w; x += 2) {
      const nx = (x - cx) / rx
      if (nx * nx + ny2 > 1) continue
      const i = (row + x) * 4
      bucket.push(data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114)
    }
  }
  return Float32Array.from(bucket)
}

export function sampleOval(video: HTMLVideoElement, canvas: HTMLCanvasElement): Float32Array | null {
  const vw = video.videoWidth
  const vh = video.videoHeight
  if (video.readyState < 2 || !vw || !vh) return null
  const w = 160
  const h = Math.max(1, Math.round((w * vh) / vw))
  if (canvas.width !== w) canvas.width = w
  if (canvas.height !== h) canvas.height = h
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  if (!ctx) return null
  ctx.drawImage(video, 0, 0, w, h)
  return ovalLumas(ctx.getImageData(0, 0, w, h).data, w, h)
}

export function watchFrame(
  lumas: Float32Array,
  prev: Float32Array | null,
  stillSince: number | null,
  now: number,
): { prev: Float32Array; stillSince: number | null; ready: boolean } {
  const centered = lumaVariance(lumas) >= OVAL_VAR_MIN
  const calm = prev !== null && meanAbsDiff(prev, lumas) <= STILL_MAD_MAX
  if (!centered || !calm) return { prev: lumas, stillSince: null, ready: false }
  const since = stillSince === null ? now : stillSince
  return { prev: lumas, stillSince: since, ready: now - since >= STILL_MS }
}

export function jpegFromVideo(video: HTMLVideoElement): Promise<Blob | null> {
  const vw = video.videoWidth
  const vh = video.videoHeight
  if (!vw || !vh) return Promise.resolve(null)
  const scale = Math.min(1, 720 / Math.max(vw, vh))
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.round(vw * scale))
  canvas.height = Math.max(1, Math.round(vh * scale))
  const ctx = canvas.getContext('2d')
  if (!ctx) return Promise.resolve(null)
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
  return new Promise((resolve) => {
    canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.85)
  })
}

export async function loadGallery(): Promise<{ engine?: string }> {
  const res = await fetch('/face/gallery')
  if (!res.ok) throw new Error('gallery')
  const data: unknown = await res.json()
  if (!data || typeof data !== 'object') return {}
  const engine = (data as { engine?: unknown }).engine
  return { engine: typeof engine === 'string' ? engine : undefined }
}

function asResult(data: unknown): EnrollResult {
  if (!data || typeof data !== 'object') return { frames: [] }
  const row = data as Record<string, unknown>
  const frames = Array.isArray(row.frames)
    ? row.frames.map((item) => {
        const frame = item && typeof item === 'object' ? (item as Record<string, unknown>) : {}
        return {
          ok: frame.ok === true,
          reason: typeof frame.reason === 'string' ? frame.reason : undefined,
        }
      })
    : []
  return {
    person: typeof row.person === 'string' ? row.person : undefined,
    engine: typeof row.engine === 'string' ? row.engine : undefined,
    frames,
    count: typeof row.count === 'number' ? row.count : undefined,
  }
}

export async function enrollFrames(personId: FacePersonId, files: Blob[], replace: boolean): Promise<EnrollResult> {
  const form = new FormData()
  files.forEach((file, i) => {
    const filename = file instanceof File && file.name ? file.name : `frame-${i + 1}.jpg`
    form.append('frames', file, filename)
  })
  if (replace) form.append('replace', '1')
  const res = await fetch(`/face/enroll/${personId}`, { method: 'POST', body: form })
  if (!res.ok) throw new Error('enroll')
  return asResult(await res.json())
}
