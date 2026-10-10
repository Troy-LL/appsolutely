import { Back } from './Icons'

export function SubHead({ title, label, onBack }: { title: string; label: string; onBack: () => void }) {
  return (
    <div className="sn-subhead">
      <button type="button" className="sn-icon-btn" aria-label={label} onClick={onBack}><Back /></button>
      <h2>{title}</h2>
    </div>
  )
}
