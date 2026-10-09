import type { MemberColor } from '../types'

// MemoryFrame: how Sino shows a person, everywhere. Ink moulding, paper mat, name plate.
// The member colour only shows on hover / focus (or when `show` is set).
interface Props {
  name: string
  meta?: string
  color?: MemberColor
  photo?: string // a /media/... url; the first letter shows until there is one
  size?: 'm' | 'l' | 'wall'
  tilt?: 'l' | 'r' | ''
  show?: boolean
  onClick?: () => void
  ariaLabel?: string
}

export function Frame({ name, meta, color, photo, size = 'm', tilt = '', show, onClick, ariaLabel }: Props) {
  const cls = ['sn-frame', `sn-frame--${size}`, color ? `c-${color}` : '', tilt ? `tilt-${tilt}` : '', show ? 'is-show' : '']
    .filter(Boolean).join(' ')
  const inner = (
    <>
      <span className="sn-frame__box">
        <span className="sn-frame__photo">
          {photo ? <img src={photo} alt="" /> : name.trim().split(' ').pop()?.[0]?.toUpperCase()}
        </span>
      </span>
      <span className="sn-frame__plate">{name}</span>
      {meta ? <span className="sn-frame__meta">{meta}</span> : null}
    </>
  )
  return onClick ? (
    <button type="button" className={cls} onClick={onClick} aria-label={ariaLabel}>{inner}</button>
  ) : (
    <span className={cls}>{inner}</span>
  )
}

export function AddFrame({ label, hint, onClick }: { label: string; hint: string; onClick: () => void }) {
  return (
    <button type="button" className="sn-frame sn-frame--wall sn-frame--add" onClick={onClick}>
      <span className="sn-frame__box"><span className="sn-frame__photo">+</span></span>
      <span className="sn-frame__plate">{label}</span>
      <span className="sn-frame__meta">{hint}</span>
    </button>
  )
}
