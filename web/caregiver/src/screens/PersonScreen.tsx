import type { Person, Question } from '../types'
import type { T } from '../i18n/i18n'
import { Frame } from '../components/Frame'
import { Back, Play } from '../components/Icons'
import { faceId } from '../data/faceEnroll'
import { copy, slash } from '../i18n/calibrate'
import '../styles/calibrate.css'

// One family member's recorded replies, from GET /questions (speaker === name).
export function PersonScreen({ t, person, questions, onBack, onCalibrate }: {
  t: T
  person: Person
  questions: Question[]
  onBack: () => void
  onCalibrate?: () => void
}) {
  const mine = questions.filter((q) => q.speaker === person.name)
  const enrolled = faceId(person.name)
  const playable = (q: Question) => !!q.reply_audio
  const play = (q: Question) => { void new Audio(q.reply_audio).play().catch(() => undefined) }
  return (
    <>
      <div className="sn-subhead">
        <button type="button" className="sn-icon-btn" aria-label={t.one('back')} onClick={onBack}><Back /></button>
        <h2>{t.one('personReplies', { name: person.name })}</h2>
      </div>
      <div className="sn-scroll">
        <div className="sn-person">
          <Frame name={person.name} color={person.color} size="l" show photo={mine.find((q) => q.photo)?.photo} />
          <p className="sn-person__meta">{t.one('recordedReplies', { n: mine.filter(playable).length })}</p>
          {enrolled && onCalibrate ? (
            <button type="button" className="sn-btn sn-btn--wide" onClick={onCalibrate}>{slash(t, copy.addFace)}</button>
          ) : null}
        </div>
        {mine.length ? (
          <ul className="sn-list">
            {mine.map((q) => (
              <li key={q.id}>
                <span><b>“{q.question}”</b><small>{playable(q) ? t.one('phrasings', { n: q.phrasings.length }) : t.one('noAudioYet')}</small></span>
                <button type="button" className="sn-icon-btn" aria-label={`${t.one('play')}: ${q.question}`}
                  disabled={!playable(q)} onClick={() => play(q)}><Play /></button>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </>
  )
}
