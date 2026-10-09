# Caregiver phone (`/caregiver`)

The caregiver's iPhone screen for Sino. Owner: Viviene. Frontend only: it reads the hub's
existing `/ws`, `GET /questions` and `POST /questions` ([architecture.md](../../docs/sino/architecture.md#the-3-interfaces-locked-in-the-first-15-minutes))
and adds nothing to the backend. Look and words follow [design-system.md](../../docs/sino/design-system.md).

## Run it

```bash
cd web/caregiver
npm install
npm run dev            # fake feed: http://localhost:5173/
```

- **Fake feed (default).** Plays `web/fake-feed`'s script, so the screen works with no hub. A "Fake feed" tag shows in the top bar. "What Sino knows" reads `brain/seed.json`. Saving a reply does not send anything.
- **Real hub.** Start the hub (`brain/server.py`, port 8000), then open `http://localhost:5173/?feed=hub`. Vite proxies `/ws`, `/questions`, `/media` and `/health` to the hub. Point it elsewhere with `HUB=https://<hub-ip>:8000 npm run dev`.
- **On the iPhone.** The mic needs HTTPS. Use the hub's mkcert setup (`docs/sino/DONITA-SETUP.md`). TODO: serve `dist/` from the hub at `/caregiver` (backend change, not in this folder).
- `npm run build` type-checks and writes `dist/`.

## What it does (MVP)

| Event / call | On screen |
|---|---|
| `alert` | Red card, pinned on top, a two-note tone every 4 s until **Nabasa na / Mark as read** (Undo available). Calling is cut, see design-system gap 1. |
| `ask_caregiver` | Quiet yellow card. Repeats of the same words share one card ("2 times since …"). **Record a reply** opens the recorder. |
| `decided` (comfort) | Green "Answered" card, with whose voice played (looked up by `reply_id` in the questions file). |
| `ask_about_lola` → `about_lola` | **Sino AI** tab: three fixed questions (design-system gap 4, no free-text box) worded to match `brain/ask.py`'s rules. Answers show as a chat thread with where they came from and the seconds taken. On the fake feed a local copy of ask.py's logic answers (`src/data/askLocal.ts`). No answer in 15 s says so. |
| `ask_about_lola` (typed) | Sino AI also has a text box. The words go to the hub as the `question`; `brain/ask.py` picks the intent (rules, then Qwen). On the fake feed a few keywords pick it. Note: `design-system.md` gap 4 asked for chips only; the text box was added on request (Viviene). |
| all of the above | **Activity log** tab: a timeline, newest first. One **Filter** button opens a panel: what (everything, urgent, needs you, answered, activities) and when (today, last 7 days, one date). Active filters show as chips with ×. |
| (this phone only) | **Add activity**: quick picks (Kumain, Naligo, …) or free text, logged at the current time with Undo. Not sent to the hub: `meal_logged` is a Should item and its direction is not written down (TODO). |
| (this phone only) | **Day receipt**: today as a torn paper receipt with totals; complete from 9 in the evening. "Print or save" opens the phone's print sheet. |
| `health` | Sala status bar: green when every part is up, amber naming the part that is down. Account shows each part. |
| `POST /questions` | Saving a recording: Lola's words become `question` and `phrasings`, your recording `reply_audio`, your name `speaker`. |
| `GET /questions` | The family wall (one frame per `speaker`) and "What Sino knows". |

Also: Tagalog / English / Both (`src/i18n/tl.ts`, `en.ts`), text size A / A+ / A++, times in words.

## Where the 7 days come from

The hub has no route for past days, so on `?feed=hub` this phone keeps its own copy of the log in `localStorage` (`sino.caregiver.log.v1`, last 7 days, pruned on save). On the fake feed the earlier days are sample data (`demoHistory()` in `src/data/history.ts`) and the screen says so.

## Not connected yet (UI only, said on screen)

- **Add a family member** keeps the new frame on this phone only. The hub has people only as a question's `speaker`; their replies are added in `/setup`.
- **What Sino knows** is read-only: there is no delete route, so each question's trash button says so on screen and deletes nothing. Safety words are copied from `brain/decide.py` (`URGENT_STEMS`), keep in sync.
- The caregiver's name is a placeholder (`ME` in `src/App.tsx`). TODO.
- Not built (Should items, after the freeze): "Kumain na", recap counts.
- The tab bar order is Home, Family, Sino AI, Activity log, Sino knows. The amber number on Activity is how many cards need you. The day receipt opens from Activity; your account from the initial tile in the top bar.

## Files

```
src/
  App.tsx              screens, state, wiring
  types.ts             interface shapes (Question, Health, events) + card types
  data/hub.ts          /ws via web/fake-feed, GET and POST /questions
  data/log.ts          events -> cards
  data/recorder.ts     MediaRecorder + live waveform levels
  data/urgentSound.ts  the urgent tone (Web Audio, no file)
  data/safetyWords.ts  copy of URGENT_STEMS
  data/askLocal.ts     fake-feed answers for Sino AI (mirrors brain/ask.py) + keyword intent for typed questions
  data/history.ts      7-day log on this phone (localStorage), sample days for the fake feed
  i18n/                tl.ts, en.ts, helpers (one / two / btn / head), times in words
  components/          Frame (MemoryFrame), SalaScene, Cards (urgent, needs, done), SummaryChips, TopBar, TabBar, bits
  screens/             Home, Family, Ask (Sino AI), Activity, Receipt, Knows, Person, Record, AddPerson, Account
  styles/              tokens.css (design-system Appendix A), app.css
  assets/fonts/        Fredoka 500/600, DM Sans 400/700 (SIL OFL, Fontsource 5.3.0)
```
