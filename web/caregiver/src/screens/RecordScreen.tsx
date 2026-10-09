import { useState } from 'react'
import type { Entry } from '../types'
import type { T } from '../i18n/i18n'
import { useRecorder } from '../data/recorder'
import { saveReply } from '../data/hub'
import { Waveform } from '../components/bits'
import { Back, Mic, Play, Redo } from '../components/Icons'

// RecordReply: answer one yellow card in your own voice. Save = POST /questions.
export function RecordScreen({ t, entry, me, onBack, onSaved }: { t: T; entry: Entry; me: string; onBack: () => void; onSaved: (fake: boolean) => void }) {
  const r = useRecorder()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const micLabel = r.state === 'recording' ? t.btn('stopBtn') : r.state === 'done' ? t.btn('againBtn') : t.btn('recordBtn')
  const status = r.state === 'denied' ? t.two('micDenied') : r.state === 'recording' ? t.two('recording') : r.state === 'done' ? t.two('doneRec') : t.two('ready')

  const onMic = () => (r.state === 'recording' ? r.stop() : void r.start())
  const save = async () => {
    if (!r.blob) return
    setSaving(true)
    setError('')
    try {
      const res = await saveReply({ transcript: entry.transcript, speaker: me, audio: r.blob })
      onSaved(res === 'fake')
    } catch (e) {
      setError(t.two('saveFailed', { why: e instanceof Error ? e.message : String(e) }))
      setSaving(false)
    }
  }

  return (
    <>
      <div className="sn-subhead">
        <button type="button" className="sn-icon-btn" aria-label={t.one('back')} onClick={onBack}><Back /></button>
        <h2>{t.one('record')}</h2>
      </div>
      <div className="sn-scroll">
        <div className="sn-record">
          <div className="sn-askband">
            <p className="sn-entry__status"><span className="sn-dot sn-dot--paper" aria-hidden="true" />{t.one('lolaAsked')}</p>
            <p className="sn-entry__quote">“{entry.transcript}”</p>
          </div>
          <Waveform levels={r.levels} />
          <p className="sn-state pl" role="status">{status}</p>
          <div className="sn-record__row">
            <button type="button" className="sn-icon-btn" aria-label={t.one('startOver')} onClick={r.reset}><Redo /></button>
            <button type="button" className={`sn-mic${r.state === 'recording' ? ' is-rec' : ''}`} onClick={onMic}>
              <Mic /><span className="pl">{micLabel.replace(' / ', '\n')}</span>
            </button>
            <button type="button" className="sn-icon-btn" aria-label={t.one('play')} disabled={!r.url}
              onClick={() => { void new Audio(r.url).play().catch(() => undefined) }}><Play /></button>
          </div>
          <p className="sn-tip pl">{t.two('tip')}</p>
          {error ? <p className="sn-note pl" role="alert">{error}</p> : null}
          {r.state === 'done' ? (
            <button type="button" className="sn-btn sn-btn--wide sn-btn--big" disabled={saving} onClick={() => void save()}>
              {saving ? t.one('saving') : t.btn('save')}
            </button>
          ) : null}
        </div>
      </div>
    </>
  )
}
