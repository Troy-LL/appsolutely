const doors = {
  'open-lola': '/lola/?feed=hub&mic=off&demo=1',
  'open-care': '/caregiver/?feed=hub&demo=1',
  'open-back': '/backstage/?feed=hub&demo=1',
}

const wake = document.getElementById('wake')

function showWake() {
  if (wake) wake.hidden = false
}

function hideWake() {
  if (wake) wake.hidden = true
}

function loadSid() {
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
}

function pingHealth() {
  const slow = setTimeout(showWake, 400)
  fetch('/health', { cache: 'no-store' })
    .then((res) => {
      if (!res.ok) throw new Error('down')
      return res.json()
    })
    .then(() => {
      clearTimeout(slow)
      hideWake()
      loadSid()
    })
    .catch(() => {
      clearTimeout(slow)
      showWake()
      setTimeout(pingHealth, 3000)
    })
}

pingHealth()
