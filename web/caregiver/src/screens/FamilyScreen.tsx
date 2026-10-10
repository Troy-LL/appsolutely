import type { Person } from '../types'
import type { T } from '../i18n/i18n'
import { AddFrame, Frame } from '../components/Frame'
import { WallFloor } from '../components/SalaScene'

interface Props {
  t: T
  people: Person[]
  replyCount: (name: string) => number
  justAdded: Person | null
  onUndoAdd: () => void
  onPerson: (name: string) => void
  onAdd: () => void
}

const TILTS = ['l', '', 'r'] as const

// One nail and a V-shaped string above each frame.
const Nail = ({ empty }: { empty?: boolean }) => (
  <svg width="70" height="26" viewBox="0 0 70 26" aria-hidden="true">
    {empty ? (
      <circle cx="35" cy="6" r="4" fill="none" stroke="#2b2420" strokeWidth="2" />
    ) : (
      <>
        <path d="M35 0 V6 M35 6 L12 26 M35 6 L58 26" stroke="#2b2420" strokeWidth="2" />
        <circle cx="35" cy="6" r="4" fill="#2b2420" />
      </>
    )}
  </svg>
)

export function FamilyScreen({ t, people, replyCount, justAdded, onUndoAdd, onPerson, onAdd }: Props) {
  return (
    <div className="sn-scroll sn-scroll--flush">
      <div className="sn-hello"><h1 className="sn-greet sn-greet--tight">{t.one('family')}</h1></div>
      <p className="sn-intro pl">{t.two('familyIntro')}</p>
      {justAdded ? (
        <div className="sn-undo">
          <span>{t.one('addedOnWall', { name: justAdded.name })}</span>
          <button type="button" className="sn-btn sn-btn--quiet" onClick={onUndoAdd}>{t.btn('undo')}</button>
        </div>
      ) : null}
      <div className="sn-house">
        <div className="sn-house__rail" />
        <div className="sn-house__wall">
          {people.map((x, i) => (
            <div className="sn-hang" key={x.name}>
              <Nail />
              <Frame name={x.name} color={x.color} size="wall" tilt={TILTS[i % 3]} photo={x.photo}
                meta={t.one('replies', { n: replyCount(x.name) })}
                ariaLabel={t.one('personReplies', { name: x.name })} onClick={() => onPerson(x.name)} />
            </div>
          ))}
          <div className="sn-hang">
            <Nail empty />
            <AddFrame label={t.one('addShort')} hint={t.one('addHint')} onClick={onAdd} />
          </div>
        </div>
        <div className="sn-house__wain" aria-hidden="true"><span /><span /><span /><span /></div>
        <WallFloor />
      </div>
    </div>
  )
}
