import { useState } from 'react'
import type { MemberColor, Person } from '../types'
import type { T } from '../i18n/i18n'
import { Frame } from '../components/Frame'
import { Camera, Close } from '../components/Icons'

// Adds a frame to the family wall on this phone only. The hub stores people only as a
// question's `speaker`, so their replies are recorded in /setup (Ayen). Not sent anywhere.
const CALLS = ['Ate', 'Kuya', 'Tita', 'Tito', 'Apo', 'Anak']
const COLORS: { id: MemberColor; key: 'colorGreen' | 'colorAmber' | 'colorRed' }[] = [
  { id: 'green', key: 'colorGreen' }, { id: 'amber', key: 'colorAmber' }, { id: 'red', key: 'colorRed' },
]

export function AddPersonScreen({ t, onCancel, onDone }: { t: T; onCancel: () => void; onDone: (p: Person) => void }) {
  const [step, setStep] = useState(1)
  const [call, setCall] = useState('Ate')
  const [name, setName] = useState('')
  const [photo, setPhoto] = useState('')
  const [color, setColor] = useState<MemberColor>('green')
  const [tried, setTried] = useState(false)
  const full = `${call} ${name.trim() || '…'}`

  const next = () => {
    if (step === 1 && !name.trim()) return setTried(true)
    if (step < 3) return setStep(step + 1)
    onDone({ name: `${call} ${name.trim()}`, color, local: true })
  }
  const back = () => (step === 1 ? onCancel() : setStep(step - 1))
  const pickPhoto = (f: File | undefined) => { if (f) setPhoto(URL.createObjectURL(f)) }

  return (
    <>
      <div className="sn-subhead">
        <button type="button" className="sn-icon-btn" aria-label={t.one('cancel')} onClick={onCancel}><Close /></button>
        <h2>{t.one('addTitle')}</h2>
      </div>
      <div className="sn-scroll sn-steps">
        <p className="sn-step__count">{t.one('stepOf', { n: step })}</p>
        <div className="sn-progress">{[1, 2, 3].map((i) => <span key={i} className={i <= step ? 'is-done' : ''} />)}</div>
        <div className="sn-preview"><Frame name={full} color={color} photo={photo} size="wall" show /></div>

        {step === 1 ? (
          <>
            <h3 className="sn-step__q">{t.one('s1')}</h3>
            <p className="sn-step__help pl">{t.two('s1help')}</p>
            <div className="sn-field">
              <span className="sn-field__label" id="call-label">{t.one('callLabel')}</span>
              <div className="sn-choice" role="radiogroup" aria-labelledby="call-label">
                {CALLS.map((c) => (
                  <button key={c} type="button" role="radio" aria-checked={call === c}
                    className={call === c ? 'is-on' : ''} onClick={() => setCall(c)}>{c}</button>
                ))}
              </div>
            </div>
            <div className="sn-field">
              <label className="sn-field__label" htmlFor="sn-name">{t.one('nameLabel')}</label>
              <input id="sn-name" className="sn-input" type="text" autoComplete="off" value={name}
                placeholder={t.one('namePh')} onChange={(e) => { setName(e.target.value); setTried(false) }} />
            </div>
            {tried && !name.trim() ? <p className="sn-note pl"><span className="sn-dot" aria-hidden="true" />{t.two('nameFirst')}</p> : null}
          </>
        ) : null}

        {step === 2 ? (
          <>
            <h3 className="sn-step__q">{t.one('s2')}</h3>
            <p className="sn-step__help pl">{t.two('s2help')}</p>
            <label className={`sn-photo${photo ? ' is-done' : ''}`}>
              <Camera />{photo ? t.btn('photoChosen') : t.btn('photoPick')}
              <input type="file" accept="image/*" className="sn-visually-hidden" onChange={(e) => pickPhoto(e.target.files?.[0])} />
            </label>
          </>
        ) : null}

        {step === 3 ? (
          <>
            <h3 className="sn-step__q">{t.one('s3')}</h3>
            <p className="sn-step__help pl">{t.two('s3help')}</p>
            <div className="sn-swatches" role="radiogroup" aria-label={t.one('s3')}>
              {COLORS.map((c) => (
                <button key={c.id} type="button" role="radio" aria-checked={color === c.id}
                  className={`sn-sw${color === c.id ? ' is-on' : ''}`} onClick={() => setColor(c.id)}>
                  <span className={`sn-sw__chip ${c.id}`} aria-hidden="true" />
                  <span>{t.one(c.key)}</span>
                  <span className="sn-sw__mark" aria-hidden="true">{color === c.id ? '✓' : ''}</span>
                </button>
              ))}
            </div>
            <p className="sn-step__help pl" style={{ marginTop: 16 }}>{t.two('localOnly')}</p>
          </>
        ) : null}
      </div>
      <div className="sn-foot">
        <button type="button" className="sn-btn sn-btn--quiet" onClick={back}>{t.btn('back')}</button>
        <button type="button" className="sn-btn" onClick={next}>{step === 3 ? t.btn('hang') : t.btn('next')}</button>
      </div>
    </>
  )
}
