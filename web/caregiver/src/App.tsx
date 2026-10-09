import { useEffect, useMemo, useReducer, useRef, useState } from 'react'
import type { AskIntent, ChatMsg, Entry, Lang, MemberColor, Person, Question, Scale, Screen } from './types'
import { makeT } from './i18n/i18n'
import { initialLog, logReducer } from './data/log'
import { loadQuestions, loadSafetyWords, useFeed, USING_HUB } from './data/hub'
import { SAFETY_WORDS } from './data/safetyWords'
import { readAbout } from './feed/events'
import { startMonitoring } from './feed/monitor'
import type { LinkStatus } from './feed/connect'
import { useUrgentSound } from './data/urgentSound'
import { TopBar } from './components/TopBar'
import { TAB_SCREENS, TabBar } from './components/TabBar'
import { answerLocally, ASK_QUESTIONS, intentOf } from './data/askLocal'
import { daysAgo, demoHistory, loadSaved, save } from './data/history'
import { ReceiptScreen } from './screens/ReceiptScreen'
import { AskScreen } from './screens/AskScreen'
import { ActivityScreen } from './screens/ActivityScreen'
import { HomeScreen } from './screens/HomeScreen'
import { FamilyScreen } from './screens/FamilyScreen'
import { PersonScreen } from './screens/PersonScreen'
import { KnowsScreen } from './screens/KnowsScreen'
import { RecordScreen } from './screens/RecordScreen'
import { AddPersonScreen } from './screens/AddPersonScreen'
import { AccountScreen } from './screens/AccountScreen'

// TODO: the caregiver's name should come from setup. Placeholder until then.
const ME = 'Joy'
// Member colours on the family wall, in turn (only shown on hover / tap).
const WALL_COLORS: MemberColor[] = ['green', 'amber', 'red']
const TABS: Screen[] = TAB_SCREENS
const ASK_TIMEOUT_MS = 15_000 // no about_lola by then: say so and let them ask again

export default function App() {
  const [lang, setLang] = useState<Lang>('both')
  const [scale, setScale] = useState<Scale>(0)
  const [screen, setScreen] = useState<Screen>('home')
  const [tab, setTab] = useState<Screen>('home') // where Back returns to
  const [langOpen, setLangOpen] = useState(false)
  const [recordId, setRecordId] = useState('')
  const [personName, setPersonName] = useState('')
  const [added, setAdded] = useState<Person[]>([])
  const [justAdded, setJustAdded] = useState<Person | null>(null)
  const [questions, setQuestions] = useState<Question[] | null>(null)
  const [builtinWords, setBuiltinWords] = useState<string[]>(SAFETY_WORDS)
  const [customWords, setCustomWords] = useState<string[]>([])
  const [loadError, setLoadError] = useState('')
  const [now, setNow] = useState(Date.now())
  const [log, dispatch] = useReducer(logReducer, initialLog)
  const [link, setLink] = useState<LinkStatus>('open')
  const [monitoring, setMonitoring] = useState(false)
  const t = useMemo(() => makeT(lang), [lang])

  // Sino AI thread. One question at a time; pendingId is the Sino bubble waiting for about_lola.
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const pendingId = useRef('')
  const askTimer = useRef(0)
  const answer = (patch: Partial<ChatMsg>) => {
    const id = pendingId.current
    if (!id) return
    pendingId.current = ''
    window.clearTimeout(askTimer.current)
    setMessages((ms) => ms.map((m) => (m.id === id ? { ...m, pending: false, ...patch } : m)))
  }

  const refreshQuestions = () => {
    loadQuestions().then(setQuestions).catch((e: unknown) => setLoadError(e instanceof Error ? e.message : String(e)))
  }
  const rememberWord = (word: string) => {
    if (!word || builtinWords.includes(word)) return
    setCustomWords((words) => (words.includes(word) ? words : [...words, word]))
  }
  // live events from /ws (fake feed unless ?feed=hub)
  const send = useFeed((event) => {
    if (event.event === 'safety_word' && typeof event.word === 'string') {
      rememberWord(event.word)
      return
    }
    const about = readAbout(event)
    if (about) {
      answer(about)
      return
    }
    dispatch({ type: 'event', event, at: Date.now() })
  }, {
    onStatus: setLink,
    onVisible: refreshQuestions,
  })
  useEffect(() => {
    refreshQuestions()
    loadSafetyWords().then((list) => {
      setBuiltinWords(list.builtin)
      setCustomWords(list.custom)
    }).catch(() => undefined)
  }, [])
  useEffect(() => { const id = window.setInterval(() => setNow(Date.now()), 60_000); return () => window.clearInterval(id) }, [])
  useUrgentSound(log.entries.some((e) => e.kind === 'urgent'))

  // Last 7 days: restore what this phone saved (real hub), or sample days (fake feed).
  useEffect(() => { dispatch({ type: 'load', entries: USING_HUB ? loadSaved() : demoHistory() }) }, [])
  useEffect(() => { if (USING_HUB) save(log.entries) }, [log.entries])
  const [lastNote, setLastNote] = useState<Entry | null>(null)
  const addNote = (label: [string, string], preset: string) => {
    const sentToHub = preset === 'ate' && USING_HUB
    if (sentToHub) send({ event: 'meal_logged' })
    const entry: Entry = { id: `note-${Date.now()}`, kind: 'note', transcript: label[0], label, preset, at: Date.now(), count: 1, sentToHub }
    dispatch({ type: 'addNote', entry })
    setLastNote(entry)
  }

  // whose voice played: look up the reply_id in the questions file
  const entries = useMemo(
    () => log.entries.map((e) => (e.replyId && !e.speaker ? { ...e, speaker: questions?.find((q) => q.id === e.replyId)?.speaker } : e)),
    [log.entries, questions],
  )

  // the family = every speaker in the questions file, the voice Lola heard last first
  const people: Person[] = useMemo(() => {
    const names: string[] = []
    for (const e of entries) if (e.kind === 'answered' && e.speaker && !names.includes(e.speaker)) names.push(e.speaker)
    for (const q of questions ?? []) if (q.speaker && !names.includes(q.speaker)) names.push(q.speaker)
    const fromHub = names.map((name, i) => ({ name, color: WALL_COLORS[i % WALL_COLORS.length] }))
    return [...fromHub, ...added]
  }, [entries, questions, added])
  // Home, Sino AI and the receipt are about today; the activity log can look back 7 days.
  const today = useMemo(() => entries.filter((e) => daysAgo(e.at, now) === 0), [entries, now])
  const replyCount = (name: string) => (questions ?? []).filter((q) => q.speaker === name).length

  // question: what the caregiver typed or tapped. intent: known when a quick question was tapped.
  const ask = (question: string, intent?: AskIntent) => {
    if (pendingId.current || !question.trim()) return
    const at = Date.now()
    const sinoId = `s${at}`
    pendingId.current = sinoId
    setMessages((ms) => [
      ...ms,
      { id: `y${at}`, from: 'you', text: question, at },
      { id: sinoId, from: 'sino', text: '', at, pending: true },
    ])
    if (!USING_HUB) {
      // fake feed: answer from today's cards, the same way brain/ask.py does
      window.setTimeout(() => answer({ text: answerLocally(intent ?? intentOf(question), today, t), source: 'fake' }), 700)
      return
    }
    // quick questions go in Tagalog so ask.py's rules answer them without the model
    const wording = intent ? ASK_QUESTIONS.find((q) => q.intent === intent)?.tl ?? question : question
    send({ event: 'ask_about_lola', question: wording })
    askTimer.current = window.setTimeout(() => answer({ text: t.two('askTimeout'), error: true }), ASK_TIMEOUT_MS)
  }

  const go = (s: Screen) => {
    setLangOpen(false)
    setScreen(s)
    if (TABS.includes(s)) setTab(s)
  }
  const back = () => go(tab)
  const recordEntry = entries.find((e) => e.id === recordId)
  const person = people.find((p) => p.name === personName)
  const onTab = TABS.includes(screen) || screen === 'receipt'

  return (
    <div className={`sn-app${scale === 1 ? ' s2' : scale === 2 ? ' s3' : ''}`} lang={lang === 'en' ? 'en' : 'tl'}>
      {onTab ? (
        <TopBar t={t} lang={lang} langOpen={langOpen} fake={!USING_HUB} me={ME}
          onToggleLang={() => setLangOpen(!langOpen)} onPickLang={(l) => { setLang(l); setLangOpen(false) }}
          onAccount={() => go('account')} />
      ) : null}

      {link === 'reconnecting' ? <p className="sn-reconnect" role="status">{t.one('reconnecting')}</p> : null}
      {!monitoring ? (
        <div className="sn-monitor">
          <button type="button" className="sn-btn sn-btn--wide" onClick={() => { void startMonitoring(); setMonitoring(true) }}>
            {t.btn('startMonitor')}
          </button>
        </div>
      ) : null}

      {screen === 'home' ? (
        <HomeScreen t={t} me={ME} now={now} health={log.health} entries={today} people={people} replyCount={replyCount}
          onRecord={(id) => { setRecordId(id); go('record') }}
          onRead={(id) => dispatch({ type: 'markRead', id })}
          onUnread={(id) => dispatch({ type: 'unmarkRead', id })}
          onPerson={(name) => { setPersonName(name); go('person') }}
          onFamily={() => go('family')}
          lastNote={lastNote}
          onAte={() => addNote(['Kumain', 'Ate a meal'], 'ate')}
          onUndoNote={() => { if (lastNote) dispatch({ type: 'removeNote', id: lastNote.id }); setLastNote(null) }} />
      ) : null}

      {screen === 'family' ? (
        <FamilyScreen t={t} people={people} replyCount={replyCount} justAdded={justAdded}
          onUndoAdd={() => { setAdded(added.filter((p) => p !== justAdded)); setJustAdded(null) }}
          onPerson={(name) => { setPersonName(name); go('person') }}
          onAdd={() => { setJustAdded(null); go('add') }} />
      ) : null}

      {screen === 'ask' ? <AskScreen t={t} me={ME} messages={messages} busy={messages.some((m) => m.pending)} onAsk={ask} /> : null}

      {screen === 'activity' ? (
        <ActivityScreen t={t} entries={entries} demoDays={!USING_HUB} lastNote={lastNote}
          onRecord={(id) => { setRecordId(id); go('record') }}
          onAddNote={addNote}
          onUndoNote={() => { if (lastNote) dispatch({ type: 'removeNote', id: lastNote.id }); setLastNote(null) }}
          onReceipt={() => go('receipt')} />
      ) : null}

      {screen === 'receipt' ? <ReceiptScreen t={t} today={today} /> : null}

      {screen === 'knows' ? (
        <KnowsScreen t={t} questions={questions} loadError={loadError} people={people} todayCount={today.length}
          builtinWords={builtinWords} customWords={customWords} onAdded={rememberWord}
          onOpenLog={() => go('activity')} />
      ) : null}

      {screen === 'record' && recordEntry ? (
        <RecordScreen t={t} entry={recordEntry} me={ME} onBack={back}
          onSaved={() => {
            dispatch({ type: 'replySaved', id: recordEntry.id, speaker: ME })
            // refresh the list so the new question shows in "What Sino knows"
            loadQuestions().then(setQuestions).catch(() => undefined)
            go('home')
          }} />
      ) : null}

      {screen === 'person' && person ? <PersonScreen t={t} person={person} questions={questions ?? []} onBack={back} /> : null}

      {screen === 'add' ? (
        <AddPersonScreen t={t} onCancel={() => go('family')}
          onDone={(p) => { setAdded([...added, p]); setJustAdded(p); go('family') }} />
      ) : null}

      {screen === 'account' ? (
        <AccountScreen t={t} me={ME} health={log.health} lang={lang} scale={scale}
          onLang={setLang} onScale={setScale} onBack={back} />
      ) : null}

      {onTab ? <TabBar t={t} screen={screen} go={go} badge={today.filter((e) => e.kind === 'needs').length} /> : null}
    </div>
  )
}
