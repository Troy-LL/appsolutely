import { unlockAudio } from '../data/urgentSound'

export async function startMonitoring(): Promise<void> {
  unlockAudio()
  const locks = navigator.wakeLock
  if (!locks) return
  try {
    await locks.request('screen')
  } catch {
    /* unsupported, or the phone refused the lock */
  }
}
