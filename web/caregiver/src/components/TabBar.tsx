import type { Screen } from '../types'
import type { T } from '../i18n/i18n'
import { Chat, Clock, Frames, Home, List } from './Icons'

// Home, Family, Sino AI, Activity, Knows. The day receipt opens from Activity; Account from the top bar.
export const TAB_SCREENS: Screen[] = ['home', 'family', 'ask', 'activity', 'knows']

export function TabBar({ t, screen, go, badge }: { t: T; screen: Screen; go: (s: Screen) => void; badge: number }) {
  const current = screen === 'receipt' ? 'activity' : screen
  const tabs = [
    { id: 'home' as const, label: t.one('tabHome'), icon: <Home /> },
    { id: 'family' as const, label: t.one('tabFamily'), icon: <Frames /> },
    { id: 'ask' as const, label: t.one('tabAsk'), icon: <Chat /> },
    { id: 'activity' as const, label: t.one('tabActivity'), icon: <Clock /> },
    { id: 'knows' as const, label: t.one('tabKnows'), icon: <List /> },
  ]
  return (
    <nav className="sn-tabs" aria-label="Sino">
      {tabs.map((tab) => (
        <button key={tab.id} type="button" className={`sn-tab${current === tab.id ? ' is-on' : ''}`}
          aria-current={current === tab.id ? 'page' : undefined} onClick={() => go(tab.id)}>
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
