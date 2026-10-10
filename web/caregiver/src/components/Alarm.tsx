// The phone as an alarm (real hub). AlertsBar: the one-tap "Turn on alerts", then a
// small "Alerts on" line. AlarmScreen: the newest red card, full screen, with Lola's
// exact words. Its only button is the red card's own "Papunta na ako / On my way" (or
// a voice reply), which sends urgent_reply and stops the alarm. It stays up after the
// 2-minute sound cap until someone answers.
import type { Alarm, Entry } from '../types'
import type { AlertStatus } from '../feed/monitor'
import type { T } from '../i18n/i18n'
import { UrgentCard } from './Cards'

export function AlertsBar({ t, status, onArm }: { t: T; status: AlertStatus | 'arming'; onArm: () => void }) {
  if (status === 'on' || status === 'nolock') {
    return (
      <div className="sn-monitor sn-monitor--on" role="status">
        <p className="sn-armed"><span className="sn-check" aria-hidden="true">✓</span>{t.btn('alertsOn')}</p>
        {status === 'nolock' ? <p className="sn-armed__hint pl">{t.two('autoLockHint')}</p> : null}
      </div>
    )
  }
  return (
    <div className="sn-monitor">
      <p className="sn-armed__why pl">{t.two('armWhy')}</p>
      <button type="button" className="sn-btn sn-btn--wide" disabled={status === 'arming'} onClick={onArm}>
        {t.btn(status === 'arming' ? 'arming' : 'armAlerts')}
      </button>
    </div>
  )
}

export function AlarmScreen({ t, alarm, entry, onReply }: { t: T; alarm: Alarm; entry: Entry; onReply: (audio?: Blob) => void }) {
  return (
    <div className="sn-alarm" role="alertdialog" aria-modal="true" aria-label={t.one('urgentHead')}>
      <div className="sn-alarm__in">
        <UrgentCard t={t} entry={entry} onReply={onReply} />
        {alarm.silent ? <p className="sn-alarm__note pl">{t.two('alarmSilent')}</p> : null}
        {!alarm.ringing ? <p className="sn-alarm__note pl">{t.two('alarmCapped')}</p> : null}
      </div>
    </div>
  )
}
