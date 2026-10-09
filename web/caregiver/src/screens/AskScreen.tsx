import { useEffect, useRef, useState } from 'react'
import type { AskIntent, ChatMsg } from '../types'
import { timeInWords, type T } from '../i18n/i18n'
import { ASK_QUESTIONS } from '../data/askLocal'
import { Chat } from '../components/Icons'
import { Send } from '../components/Icons2'

interface Props {
  t: T
  me: string
  messages: ChatMsg[]
  busy: boolean
  // question: the words to send; intent: known when a quick question was tapped
  onAsk: (question: string, intent?: AskIntent) => void
}

// Sino AI = Ask Sino about Lola (T7). Three fixed questions, answers built from the log.
// Thread: your question on the right (green), Sino's answer on the left (paper bubble).
export function AskScreen({ t, me, messages, busy, onAsk }: Props) {
  const end = useRef<HTMLDivElement>(null)
  const [text, setText] = useState('')
  const submit = () => { if (!busy && text.trim()) { onAsk(text.trim()); setText('') } }
  useEffect(() => { end.current?.scrollIntoView({ block: 'end' }) }, [messages])

  const metaFor = (m: ChatMsg) => {
    if (m.error || m.pending) return ''
    const src = m.source === 'model' ? t.one('askFromModel') : m.source === 'fake' ? t.one('fakeFeed') : t.one('askFromLog')
    const secs = typeof m.latencyMs === 'number' && m.source !== 'fake'
      ? ` · ${t.one('askSeconds', { s: (m.latencyMs / 1000).toFixed(1) })}` : ''
    return src + secs
  }

  return (
    <>
      <div className="sn-scroll sn-ask">
        <div className="sn-hello"><h1 className="sn-greet sn-greet--tight">{t.one('askTitle')}</h1></div>
        <p className="sn-intro pl">{t.two('askIntro')}</p>

        <div className="sn-thread" aria-live="polite">
          {messages.length === 0 ? (
            <div className="sn-ask__empty">
              <span className="sn-ask__mark" aria-hidden="true"><Chat size={28} /></span>
              <p className="pl">{t.two('askEmpty')}</p>
            </div>
          ) : null}
          {messages.map((m) => m.from === 'you' ? (
            <div key={m.id} className="sn-msg sn-msg--you">
              <p className="sn-msg__who">{me} · {timeInWords(m.at, t.lang)}</p>
              <div className="sn-msg__bubble"><p>{m.text}</p></div>
            </div>
          ) : (
            <div key={m.id} className={`sn-msg sn-msg--sino${m.error ? ' is-error' : ''}`}>
              <p className="sn-msg__who"><span className="sn-msg__avatar" aria-hidden="true">S</span>Sino</p>
              <div className="sn-msg__bubble">
                {m.pending ? (
                  <p className="sn-msg__thinking"><span className="sn-dots" aria-hidden="true"><i /><i /><i /></span>{t.one('askThinking')}</p>
                ) : (
                  <p className="pl">{m.error ? <><span className="sn-dot" aria-hidden="true" /> </> : null}{m.text}</p>
                )}
              </div>
              {metaFor(m) ? <p className="sn-msg__meta">{metaFor(m)}</p> : null}
            </div>
          ))}
          <div ref={end} />
        </div>
      </div>

      <div className="sn-askbar">
        <p className="sn-askbar__label">{messages.length ? t.one('askAgain') : t.one('askPick')}</p>
        <div className="sn-askbar__chips">
          {ASK_QUESTIONS.map((q) => (
            <button key={q.intent} type="button" className="sn-askchip" disabled={busy}
              onClick={() => onAsk(t.lang === 'en' ? q.en : q.tl, q.intent)}>
              {t.lang === 'en' ? q.en : q.tl}
            </button>
          ))}
        </div>
        <form className="sn-askform" onSubmit={(e) => { e.preventDefault(); submit() }}>
          <label className="sn-visually-hidden" htmlFor="sn-askinput">{t.one('askType')}</label>
          <input id="sn-askinput" className="sn-input sn-askform__input" type="text" autoComplete="off" maxLength={300}
            value={text} placeholder={t.one('askType')} onChange={(e) => setText(e.target.value)} />
          <button type="submit" className="sn-sendbtn" disabled={busy || !text.trim()} aria-label={t.one('send')}><Send /></button>
        </form>
      </div>
    </>
  )
}
