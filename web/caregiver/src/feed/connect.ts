// Hub socket for the caregiver phone. The URL comes from this page's location
// (same rule as web/fake-feed openHubFeed). Never a hard-coded ws:// host.
import type { HubEvent } from '../types'

const DELAYS = [500, 1000, 2000, 4000, 8000]

export type LinkStatus = 'open' | 'reconnecting'

function socketUrl(): string {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const sid = new URLSearchParams(location.search).get('sid')
  const extra = sid ? `&sid=${encodeURIComponent(sid)}` : ''
  return `${proto}//${location.host}/ws?screen=caregiver&monitor=1${extra}`
}

export function openCaregiverSocket(
  onEvent: (event: HubEvent) => void,
  hooks: { onStatus: (status: LinkStatus) => void; onVisible: () => void },
): { send(obj: unknown): void; close(): void } {
  let socket: WebSocket | null = null
  let closed = false
  let attempt = 0
  let timer = 0

  const connect = () => {
    if (closed) return
    const prev = socket
    socket = null
    if (prev && prev.readyState !== WebSocket.CLOSED) {
      prev.onmessage = null
      prev.onopen = null
      prev.onclose = null
      prev.onerror = null
      prev.close()
    }
    const next = new WebSocket(socketUrl())
    socket = next
    next.onmessage = (e) => {
      if (socket !== next) return
      try {
        onEvent(JSON.parse(String(e.data)) as HubEvent)
      } catch {
        /* ignore a bad frame */
      }
    }
    next.onopen = () => {
      if (socket !== next) return
      attempt = 0
      hooks.onStatus('open')
    }
    next.onclose = () => {
      if (closed || socket !== next) return
      hooks.onStatus('reconnecting')
      const delay = DELAYS[Math.min(attempt, DELAYS.length - 1)]
      attempt += 1
      timer = window.setTimeout(connect, delay)
    }
  }

  const onVis = () => {
    if (document.visibilityState !== 'visible') return
    hooks.onVisible()
    const state = socket?.readyState
    if (state === WebSocket.OPEN || state === WebSocket.CONNECTING) return
    window.clearTimeout(timer)
    attempt = 0
    connect()
  }

  document.addEventListener('visibilitychange', onVis)
  connect()

  return {
    send(obj) {
      if (socket && socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify(obj))
    },
    close() {
      closed = true
      window.clearTimeout(timer)
      document.removeEventListener('visibilitychange', onVis)
      socket?.close()
      socket = null
    },
  }
}
