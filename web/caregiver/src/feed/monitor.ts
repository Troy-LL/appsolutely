// "Turn on alerts" (one tap, real hub only). With no internet there is no push, so the
// alarm can only ring while this page is open and in front. The tap:
//   1. unlocks Web Audio (browsers allow sound only after a tap) and asks the iPhone to
//      ring even when the ring/silent switch is on silent (data/urgentSound.ts)
//   2. asks for a screen wake lock, so the screen does not dim and lock.
// The phone drops the wake lock whenever the page is hidden. When the page is visible
// again, or on the next tap, we ask again and check the sound still works. Errors are
// ignored; the status we report says what still works.
import { audioRunning, resumeAudio, ringEvenOnSilent, unlockAudio } from '../data/urgentSound'

// on: sound + screen kept on. nolock: sound only (set Auto-Lock to Never). off: no sound.
export type AlertStatus = 'on' | 'nolock' | 'off'

let report: (status: AlertStatus) => void = () => undefined
let lock: WakeLockSentinel | null = null
let watching = false

// True when the screen will stay on.
async function keepScreenOn(): Promise<boolean> {
  if (lock && !lock.released) return true
  if (!('wakeLock' in navigator)) return false // this browser has no wake lock
  try {
    lock = await navigator.wakeLock.request('screen')
    return true
  } catch {
    return false // the phone refused (for example Low Power Mode)
  }
}

async function check(): Promise<AlertStatus> {
  // both start right away, so a tap still counts as the tap for both
  const [screen, sound] = await Promise.all([keepScreenOn(), resumeAudio()])
  return !sound ? 'off' : screen ? 'on' : 'nolock'
}

async function recheck() {
  if (document.visibilityState !== 'visible') return
  report(await check())
}

export async function armAlerts(onStatus: (status: AlertStatus) => void): Promise<AlertStatus> {
  unlockAudio() // must run inside the tap, before any await
  ringEvenOnSilent()
  report = onStatus
  if (!watching) {
    watching = true
    document.addEventListener('visibilitychange', () => void recheck())
    window.addEventListener('pointerdown', () => {
      if (!audioRunning() || !lock || lock.released) void recheck()
    })
  }
  return check()
}
