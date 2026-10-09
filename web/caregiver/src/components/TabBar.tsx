import type { Screen } from '../types'
import type { T } from '../i18n/i18n'
import { Chat, Clock, Home } from './Icons'
import { Receipt } from './Icons2'

// Home, Activity, Ask, Receipt. Family, Knows and Account stay in the top-bar menu.
export const TAB_SCREENS: Screen[] = ['home', 'activity', 'ask', 'receipt']

export function TabBar({ t, screen, go, badge }: { t: T; screen: Screen; go: (s: Screen) => void; badge: number }) {
  const tabs = [
    { id: 'home' as const, label: t.one('tabHome'), icon: <Home /> },
    { id: 'activity' as const, label: t.one('tabActivity'), icon: <Clock /> },
    { id: 'ask' as const, label: t.one('tabAsk'), icon: <Chat /> },
    { id: 'receipt' as const, label: t.one('tabReceipt'), icon: <Receipt size={24} /> },
  ]
  return (
    <nav className="sn-tabs" aria-label="Sino">
      {tabs.map((tab) => (
        <button key={tab.id} type="button" className={`sn-tab${screen === tab.id ? ' is-on' : ''}`}
          aria-current={screen === tab.id ? 'page' : undefined} onClick={() => go(tab.id)}>
          <span className="sn-tab__icon">
            {tab.icon}
            {/* amber marker: cards waiting for you (ink outline, never colour alone: the count is the word) */}
            {tab.id === 'activity' && badge > 0 ? <span className="sn-tab__badge">{badge}</span> : null}
          </span>
          {tab.label}
        </button>
      ))}
    </nav>
  )
}
