import { useEffect, useLayoutEffect, useMemo, useReducer, useRef, useState } from 'react'
import type { Alarm, AskIntent, ChatMsg, Entry, Lang, MemberColor, Person, Question, Scale, Screen } from './types'
import { makeT } from './i18n/i18n'
import { initialLog, logReducer } from './data/log'
import { deleteQuestion, loadQuestions, loadSafetyWords, postUrgentReply, useFeed, USING_HUB } from './data/hub'
import { SAFETY_WORDS } from './data/safetyWords'
import { readAbout } from './feed/events'
import { armAlerts, type AlertStatus } from './feed/monitor'
import type { LinkStatus } from './feed/connect'
import { audioRunning, startAlarm, stopAlarm } from './data/urgentSound'
import { AlarmScreen, AlertsBar } from './components/Alarm'
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
import { MonitorScreen } from './screens/MonitorScreen'
import { CalibrateScreen } from './screens/CalibrateScreen'
import { emptyLive, reduceLive, type LiveState } from './feed/live'
import { faceId } from './data/faceEnroll'
import { bindHoldRed } from './hold'

// TODO: the caregiver's name should come from setup. Placeholder until then.
const ME = 'Joy'
// Member colours on the family wall, in turn (only shown on hover / tap).
const WALL_COLORS: MemberColor[] = ['green', 'amber', 'red']
const TABS: Screen[] = TAB_SCREENS
const ASK_TIMEOUT_MS = 15_000 // no about_lola by then: say so and let them ask again
const SCREEN_SET = new Set<Screen>(['home', 'family', 'ask', 'activity', 'receipt', 'knows', 'record', 'person', 'add', 'account', 'monitor', 'calibrate'])

function shotName(): string {
  return new URLSearchParams(window.location.search).get('shot') ?? ''
}

function screenFromShot(shot: string): Screen {
  if (shot === 'monitor' || shot === 'knows' || shot === 'receipt') return shot
  if (shot === 'cal' || shot === 'cal-done' || shot === 'cal-missing') return 'calibrate'
  return 'home'
}

function calPreview(shot: string): { step: number; done?: boolean; engine?: 'ok' | 'missing' } | undefined {
  const step = Number(new URLSearchParams(window.location.search).get('step') ?? '0')
  if (shot === 'cal-done') return { step: 4, done: true }
  if (shot === 'cal-missing') return { step: 0, engine: 'missing' }
  if (shot === 'cal') return { step }
  return undefined
}

interface Hist {
  screen: Screen
  tab: Screen
  personName?: string
  recordId?: string
}

function isScreen(v: unknown): v is Screen {
  return typeof v === 'string' && SCREEN_SET.has(v as Screen)
}

function readHist(v: unknown): Hist | null {
  if (!v || typeof v !== 'object') return null
  const raw = v as Partial<Hist>
  if (!isScreen(raw.screen) || !isScreen(raw.tab)) return null
  return {
    screen: raw.screen,
    tab: raw.tab,
    personName: typeof raw.personName === 'string' ? raw.personName : undefined,
    recordId: typeof raw.recordId === 'string' ? raw.recordId : undefined,
  }
}

export default function App() {
  const [lang, setLang] = useState<Lang>('both')
  const [scale, setScale] = useState<Scale>(0)
  const shot = useMemo(() => shotName(), [])
  const [screen, setScreen] = useState<Screen>(() => screenFromShot(shotName()))
  const [tab, setTab] = useState<Screen>('home') // where Back returns to
  const [langOpen, setLangOpen] = useState(false)
  const [recordId, setRecordId] = useState('')
  const [personName, setPersonName] = useState(() => (screenFromShot(shotName()).startsWith('cal') ? 'Troy' : ''))
  const [added, setAdded] = useState<Person[]>([])
  const [justAdded, setJustAdded] = useState<Person | null>(null)
  const [questions, setQuestions] = useState<Question[] | null>(null)
  const [builtinWords, setBuiltinWords] = useState<string[]>(SAFETY_WORDS)
  const [customWords, setCustomWords] = useState<string[]>([])
  const [loadError, setLoadError] = useState('')
  const [now, setNow] = useState(Date.now())
  const [log, dispatch] = useReducer(logReducer, initialLog)
  const [link, setLink] = useState<LinkStatus>('open')
  // "Turn on alerts" (real hub only) and the full-screen red alarm (components/Alarm.tsx)
  const [alerts, setAlerts] = useState<AlertStatus | 'arming'>('off')
  const [alarm, setAlarm] = useState<Alarm | null>(null)
  // what the live monitor screen shows (feed/live.ts)
  const [live, setLive] = useState<LiveState>(emptyLive)
  const t = useMemo(() => makeT(lang), [lang])

  // Sino AI thread. One question at a time; pendingId is the Sino bubble waiting for about_lola.
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const pendingId = useRef('')
  const askTimer = useRef(0)
  const rootRef = useRef<HTMLDivElement>(null)
  const applyingPop = useRef(false)
  const nav = useRef({ personName: '', recordId: '' })
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
    if (event.event === 'question_removed' && typeof event.id === 'string') {
      const id = event.id
      setQuestions((list) => (list ? list.filter((item) => item.id !== id) : list))
      return
    }
    const about = readAbout(event)
    if (about) {
      answer(about)
      return
    }
    // Full-screen red alarm. A second alert while it rings only shows the new words
    // (the newest red card): ringing stays true, so the effect below starts no second alarm.
    if (event.event === 'alert') setAlarm({ ringing: true, silent: !audioRunning() })
    // Someone answered (this phone, another phone, or a voice reply): stop ringing here too.
    if (event.event === 'urgent_reply') endAlarm()
    const at = Date.now()
    setLive((state) => reduceLive(state, event, at))
    dispatch({ type: 'event', event, at })
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
  // The alarm rings while alarm.ringing is true: once a second, until someone answers.
  // After 2 minutes startAlarm stops the sound by itself; the red screen stays up.
  useEffect(() => {
    if (!alarm?.ringing) return
    startAlarm(() => setAlarm((a) => (a ? { ...a, ringing: false } : a)))
    return stopAlarm
  }, [alarm?.ringing])
  // The one stop for the alarm: the sound and the full-screen red. Called by the red
  // card's "Papunta na ako / On my way" (replyUrgent) and by an urgent_reply from the hub.
  function endAlarm() {
    stopAlarm()
    setAlarm(null)
  }
  const turnOnAlerts = async () => {
    setAlerts('arming')
    setAlerts(await armAlerts(setAlerts))
  }

  // Last 7 days: restore what this phone saved (real hub), or sample days (fake feed).
  useEffect(() => {
    const entries = USING_HUB ? loadSaved() : demoHistory()
    if (shot === 'hold' && !USING_HUB) {
      entries.unshift({ id: 'shot-needs', kind: 'needs', transcript: 'Nasaan yung aso?', at: Date.now(), count: 1 })
    }
    dispatch({ type: 'load', entries })
  }, [shot])
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

  const replyUrgent = (audio?: Blob) => {
    endAlarm()
    const text = lang === 'en' ? 'On my way' : 'Papunta na ako'
    for (const entry of log.entries) {
      if (entry.kind === 'urgent') dispatch({ type: 'markRead', id: entry.id })
    }
    const message = { event: 'urgent_reply', text, speaker: ME, reply_audio: '' }
    if (audio && USING_HUB) {
      void postUrgentReply({ text, speaker: ME, audio }).catch(() => send(message))
      return
    }
    send(message)
  }

  const go = (s: Screen) => {
    setLangOpen(false)
    const nextTab = TABS.includes(s) ? s : tab
    setScreen(s)
    if (TABS.includes(s)) setTab(s)
    if (applyingPop.current) return
    history.pushState({ screen: s, tab: nextTab, personName: nav.current.personName, recordId: nav.current.recordId }, '')
  }
  const finish = (s: Screen) => {
    setLangOpen(false)
    const nextTab = TABS.includes(s) ? s : tab
    setScreen(s)
    if (TABS.includes(s)) setTab(s)
    history.replaceState({ screen: s, tab: nextTab, personName: nav.current.personName, recordId: nav.current.recordId }, '')
  }
  const back = () => history.back()

  useLayoutEffect(() => {
    history.replaceState({ screen, tab }, '')
    const onPop = (e: PopStateEvent) => {
      applyingPop.current = true
      setLangOpen(false)
      const st = readHist(e.state)
      if (!st) {
        nav.current = { personName: '', recordId: '' }
        setPersonName('')
        setRecordId('')
        setTab('home')
        setScreen('home')
      } else {
        setScreen(st.screen)
        setTab(st.tab)
        if (st.personName !== undefined) {
          nav.current.personName = st.personName
          setPersonName(st.personName)
        }
        if (st.recordId !== undefined) {
          nav.current.recordId = st.recordId
          setRecordId(st.recordId)
        }
      }
      applyingPop.current = false
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  useEffect(() => {
    const el = rootRef.current
    if (!el) return
    return bindHoldRed(el)
  }, [])
  const recordEntry = entries.find((e) => e.id === recordId)
  const alarmEntry = entries.find((e) => e.kind === 'urgent') // newest first
  const person = people.find((p) => p.name === personName)
  const onTab = TABS.includes(screen) || screen === 'receipt'

  const calibrateId = faceId(person?.name ?? personName)
  return (
    <div ref={rootRef} className={`sn-app${scale === 1 ? ' s2' : scale === 2 ? ' s3' : ''}`} lang={lang === 'en' ? 'en' : 'tl'}>
      {onTab ? (
        <TopBar t={t} lang={lang} langOpen={langOpen} fake={!USING_HUB} me={ME}
          onToggleLang={() => setLangOpen(!langOpen)} onPickLang={(l) => { setLang(l); setLangOpen(false) }}
          onAccount={() => go('account')}
          onBack={screen === 'receipt' ? back : undefined} backLabel={t.one('back')} />
      ) : null}

      {link === 'reconnecting' ? <p className="sn-reconnect" role="status">{t.one('reconnecting')}</p> : null}
      {/* hidden in screenshot mode (?shot=), like the old "Start monitoring" bar */}
      {USING_HUB && !shot ? <AlertsBar t={t} status={alerts} onArm={() => void turnOnAlerts()} /> : null}

      {screen === 'home' ? (
        <HomeScreen t={t} me={ME} now={now} health={log.health} entries={today} people={people} replyCount={replyCount}
          onRecord={(id) => { nav.current.recordId = id; setRecordId(id); go('record') }}
          onReply={replyUrgent}
          onUnread={(id) => dispatch({ type: 'unmarkRead', id })}
          onPerson={(name) => { nav.current.personName = name; setPersonName(name); go('person') }}
          onFamily={() => go('family')}
          lastNote={lastNote}
          onMonitor={() => go('monitor')}
          onAte={() => addNote(['Kumain', 'Ate a meal'], 'ate')}
          onUndoNote={() => { if (lastNote) dispatch({ type: 'removeNote', id: lastNote.id }); setLastNote(null) }} />
      ) : null}

      {screen === 'family' ? (
        <FamilyScreen t={t} people={people} replyCount={replyCount} justAdded={justAdded}
          onUndoAdd={() => { setAdded(added.filter((p) => p !== justAdded)); setJustAdded(null) }}
          onPerson={(name) => { nav.current.personName = name; setPersonName(name); go('person') }}
          onAdd={() => { setJustAdded(null); go('add') }} />
      ) : null}

      {screen === 'ask' ? <AskScreen t={t} me={ME} messages={messages} busy={messages.some((m) => m.pending)} onAsk={ask} /> : null}

      {screen === 'activity' ? (
        <ActivityScreen t={t} entries={entries} demoDays={!USING_HUB} lastNote={lastNote}
          onRecord={(id) => { nav.current.recordId = id; setRecordId(id); go('record') }}
          onReply={() => replyUrgent()}
          onAddNote={addNote}
          onUndoNote={() => { if (lastNote) dispatch({ type: 'removeNote', id: lastNote.id }); setLastNote(null) }}
          onReceipt={() => go('receipt')} />
      ) : null}

      {screen === 'receipt' ? <ReceiptScreen t={t} today={today} /> : null}

      {screen === 'knows' ? (
        <KnowsScreen t={t} questions={questions} loadError={loadError} people={people} todayCount={today.length}
          builtinWords={builtinWords} customWords={customWords} onAdded={rememberWord}
          onOpenLog={() => go('activity')}
          onRemove={async (id) => {
            const prev = questions
            setQuestions((list) => (list ? list.filter((item) => item.id !== id) : list))
            try {
              await deleteQuestion(id)
            } catch (err) {
              setQuestions(prev)
              throw err
            }
          }} />
      ) : null}

      {screen === 'record' && recordEntry ? (
        <RecordScreen t={t} entry={recordEntry} me={ME} onBack={back}
          onSaved={() => {
            dispatch({ type: 'replySaved', id: recordEntry.id, speaker: ME })
            // refresh the list so the new question shows in "What Sino knows"
            loadQuestions().then(setQuestions).catch(() => undefined)
            finish('home')
          }} />
      ) : null}

      {screen === 'person' && person ? (
        <PersonScreen t={t} person={person} questions={questions ?? []} onBack={back}
          onCalibrate={faceId(person.name) ? () => go('calibrate') : undefined} />
      ) : null}

      {screen === 'monitor' ? (
        <MonitorScreen t={t} health={log.health} link={link} hub={USING_HUB} rows={live.rows} face={live.face}
          onBack={back} preview={shot === 'monitor'} />
      ) : null}

      {screen === 'calibrate' && calibrateId ? (
        <CalibrateScreen t={t} name={person?.name ?? personName} personId={calibrateId} onBack={back}
          preview={calPreview(shot)} />
      ) : null}

      {screen === 'add' ? (
        <AddPersonScreen t={t} onCancel={back}
          onDone={(p) => { setAdded([...added, p]); setJustAdded(p); finish('family') }} />
      ) : null}

      {screen === 'account' ? (
        <AccountScreen t={t} me={ME} health={log.health} lang={lang} scale={scale}
          onLang={setLang} onScale={setScale} onBack={back} />
      ) : null}

      {onTab ? <TabBar t={t} screen={screen} go={go} badge={today.filter((e) => e.kind === 'needs').length} /> : null}

      {alarm && alarmEntry ? <AlarmScreen t={t} alarm={alarm} entry={alarmEntry} onReply={replyUrgent} /> : null}
    </div>
  )
}
