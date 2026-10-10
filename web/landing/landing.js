const doors = {
  'open-lola': '/lola/?feed=hub&mic=off&demo=1',
  'open-care': '/caregiver/?feed=hub&demo=1',
  'open-back': '/backstage/?feed=hub&demo=1',
}

fetch('/demo/state', { credentials: 'same-origin' })
  .then((res) => (res.ok ? res.json() : null))
  .then((body) => {
    const sid = body && typeof body.sid === 'string' ? body.sid : ''
    if (!sid) return
    const extra = '&sid=' + encodeURIComponent(sid)
    for (const id of Object.keys(doors)) {
      const el = document.getElementById(id)
      if (el) el.setAttribute('href', doors[id] + extra)
    }
  })
  .catch(() => {})
