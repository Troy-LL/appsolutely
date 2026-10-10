import { useEffect, useState } from 'react'

const LABEL = 'Demo mode · seeded data · simulated model'

export function DemoBanner() {
  const [on, setOn] = useState(() => new URLSearchParams(window.location.search).get('demo') === '1')
  useEffect(() => {
    if (on) return
    let gone = false
    fetch('/health')
      .then((res) => (res.ok ? res.json() : null))
      .then((body: unknown) => {
        if (gone || !body || typeof body !== 'object') return
        if ((body as { simulated?: unknown }).simulated === true) setOn(true)
      })
      .catch(() => undefined)
    return () => { gone = true }
  }, [on])
  if (!on) return null
  return <p className="sn-demo" role="status">{LABEL}</p>
}
