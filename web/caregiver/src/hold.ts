const HOLD = 'is-held'

const MATCH =
  'button.sn-btn, .sn-chip--ok, .sn-chip--needs, .sn-tab.is-on, .sn-me, .sn-mic, .sn-sendbtn, .sn-filter--needs.is-on, .sn-filter--answered.is-on'

function eventElement(target: EventTarget | null): Element | null {
  if (target instanceof Element) return target
  if (target instanceof Text) return target.parentElement
  return null
}

function fromField(el: Element): boolean {
  if (el.closest('input, textarea')) return true
  const node = el instanceof HTMLElement ? el : el.parentElement
  return node?.isContentEditable === true
}

function matchControl(target: EventTarget | null): HTMLElement | null {
  const el = eventElement(target)
  if (!el) return null
  const ctl = el.closest(MATCH)
  if (!(ctl instanceof HTMLElement)) return null
  if (ctl.matches(':disabled')) return null
  if (ctl.matches('button.sn-btn')) {
    if (ctl.classList.contains('sn-btn--quiet')) return null
    if (ctl.closest('.sn-scale, .sn-urgent')) return null
  }
  if (ctl.classList.contains('sn-mic') && ctl.classList.contains('is-rec')) return null
  return ctl
}

export function bindHoldRed(root: HTMLElement): () => void {
  let held: HTMLElement | null = null
  let pointerId = -1

  const clear = () => {
    held?.classList.remove(HOLD)
    held = null
    pointerId = -1
  }

  const onDown = (e: PointerEvent) => {
    if (e.button !== 0 && e.pointerType !== 'touch') return
    const el = eventElement(e.target)
    if (!el || fromField(el)) return
    const ctl = matchControl(el)
    if (!ctl) return
    clear()
    ctl.classList.add(HOLD)
    held = ctl
    pointerId = e.pointerId
    try {
      ctl.setPointerCapture(e.pointerId)
    } catch { /* already inactive */ }
  }

  const onUp = (e: PointerEvent) => {
    if (pointerId !== -1 && e.pointerId !== pointerId) return
    if (e.type === 'lostpointercapture' && held && e.target !== held) return
    clear()
  }

  const onMenu = (e: Event) => {
    if (matchControl(e.target)) e.preventDefault()
  }

  root.addEventListener('pointerdown', onDown)
  root.addEventListener('pointerup', onUp)
  root.addEventListener('pointercancel', onUp)
  root.addEventListener('lostpointercapture', onUp)
  root.addEventListener('contextmenu', onMenu)

  return () => {
    clear()
    root.removeEventListener('pointerdown', onDown)
    root.removeEventListener('pointerup', onUp)
    root.removeEventListener('pointercancel', onUp)
    root.removeEventListener('lostpointercapture', onUp)
    root.removeEventListener('contextmenu', onMenu)
  }
}
