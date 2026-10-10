# Caregiver phone (`/caregiver`)

The caregiver's iPhone screen for Sino. Owner: Viviene. It reads the hub's
`/ws`, questions, and family routes ([architecture.md](../../docs/sino/architecture.md#the-3-interfaces-locked-in-the-first-15-minutes)).
Look and words follow [design-system.md](../../docs/sino/design-system.md).

## Run it

```bash
cd web/caregiver
npm install
npm run dev            # fake feed: http://localhost:5173/
```

- **Fake feed (default).** Plays `web/fake-feed`'s script, so the screen works with no hub. A "Fake feed" tag shows in the top bar. "What Sino knows" reads `brain/seed.json`. Saving a reply does not send anything.
- **Real hub.** Start the hub (`brain/server.py`, port 8000), then open `http://localhost:5173/?feed=hub`. Vite proxies `/ws`, `/questions`, `/family`, `/media` and `/health` to the hub. Point it elsewhere with `HUB=https://<hub-ip>:8000 npm run dev`.
- **On the iPhone.** The mic needs HTTPS. Use the hub's mkcert setup (`docs/sino/DONITA-SETUP.md`). TODO: serve `dist/` from the hub at `/caregiver` (backend change, not in this folder).
- `npm run build` type-checks and writes `dist/`.

## What it does (MVP)

| Event / call | On screen |
|---|---|
| `alert` | **Full-screen red alert**: the newest red card, bigger, with Lola's exact words, and a loud alarm once a second until **Papunta na ako / On my way** (or a short recording) on that card. That sends `urgent_reply`; the card leaves the red state. An `urgent_reply` from the hub (another phone answered) also stops it. The sound stops by itself after 2 minutes; the red screen stays. See [Alerts](#alerts). The same button is on today's urgent rows in the activity log. Calling is cut, see design-system gap 1. |
| `urgent_reply` | Stops the alarm and closes the full-screen red; the red cards leave the red state. |
| `ask_caregiver` | Quiet yellow card. Repeats of the same words share one card ("2 times since …"). **Record a reply** opens the recorder. |
| `decided` (comfort) | Green "Answered" card, with whose voice played (looked up by `reply_id` in the questions file). |
| `ask_about_lola` → `about_lola` | **Sino AI** tab: three fixed questions (design-system gap 4, no free-text box) worded to match `brain/ask.py`'s rules. Answers show as a chat thread with where they came from and the seconds taken. On the fake feed a local copy of ask.py's logic answers (`src/data/askLocal.ts`). No answer in 15 s says so. |
| `ask_about_lola` (typed) | Sino AI also has a text box. The words go to the hub as the `question`; `brain/ask.py` picks the intent (rules, then Qwen). On the fake feed a few keywords pick it. Note: `design-system.md` gap 4 asked for chips only; the text box was added on request (Viviene). |
| all of the above | **Activity log** tab: a timeline, newest first. One **Filter** button opens a panel: what (everything, urgent, needs you, answered, activities) and when (today, last 7 days, one date). Active filters show as chips with ×. |
| (this phone only) | **Add activity**: quick picks (Kumain, Naligo, …) or free text, logged at the current time with Undo. Not sent to the hub: `meal_logged` is a Should item and its direction is not written down (TODO). |
| (this phone only) | **Day receipt**: today as a torn paper receipt with totals; complete from 9 in the evening. "Print or save" opens the phone's print sheet. |
| `health` | Sala status bar: green when every part is up, amber naming the part that is down. Account shows each part. |
| `POST /questions` | Saving a recording: Lola's words become `question` and `phrasings`, your recording `reply_audio`, your name `speaker`. |
| `GET /questions` | The family wall (one frame per `speaker`) and "What Sino knows". Joy, Troy, and Donita show `by_person.<id>.photo` in the frame when that photo is set. |
| `GET /family`, `POST /family` | Magdagdag saves the new member on the hub (`hub/data/family.json`). A photo from the gallery or camera is stored under `hub/data/media` and shown in that frame. A refresh or a hub restart keeps both. Other open screens get `family_added`. |

Also: Tagalog / English / Both (`src/i18n/tl.ts`, `en.ts`), text size A / A+ / A++, times in words.

## Alerts

Since Sat ~8:05 AM (Donita) the urgent alarm rings on this phone, not on the hub laptop (the laptop chime plays only with `CHIME=1`, [hub-chime.md](../../docs/sino/hub-chime.md)). With no internet there is no push, so this page must be open.

1. Open `/caregiver/?feed=hub` from the hub in Safari and tap **Buksan ang abiso / Turn on alerts** once. That tap allows sound, asks the iPhone to ring even when the ring/silent switch is on silent (`navigator.audioSession.type = 'playback'`, where Safari has it), and asks for a screen wake lock so the screen stays on. The bar then says **Bukas ang abiso / Alerts on**. If the phone can't keep the screen on, the bar says so: set Auto-Lock to **Never** (Settings › Display & Brightness › Auto-Lock), or use Guided Access.
2. Keep the page open and in front, with the volume up. A reload needs the tap again. When the page comes back after being hidden, it asks for the wake lock again and checks the sound; if sound is blocked, **Turn on alerts** shows again.
3. On `alert`: full-screen red with Lola's words and a high-low tone once a second (square waves, 1400 Hz then 1050 Hz, level 0.8; Web Audio, no file). A second alert while it rings only shows the new words; it never starts a second alarm.
4. It rings until **Papunta na ako / On my way** (or a voice reply) on the red card, or an `urgent_reply` from the hub. While a voice reply is recording the beeps pause, so the recording does not catch the alarm. Safety cap: the sound stops after **2 minutes**; the red screen stays until someone answers.

Limits: if the phone is locked or Safari is closed, it cannot ring (no push offline). Older iOS may still follow the ring/silent switch: keep the switch on ring for the demo. Next step: a native app with lock-screen alerts.

On the fake feed there is no **Turn on alerts** bar; the scripted "Masakit dibdib ko" opens the same full-screen alert, and the first tap anywhere allows sound.

Not tested on the iPhone yet. Measured on desktop Chrome only (Sat Oct 10, rendered offline, nothing played): one beep peaks at 0.79 of full scale (under clipping), and its average level (RMS) over one second is about 11 times the old two-note tone's (+21 dB). How loud that is on the iPhone speaker is to verify.

## Where the 7 days come from

The hub has no route for past days, so on `?feed=hub` this phone keeps its own copy of the log in `localStorage` (`sino.caregiver.log.v1`, last 7 days, pruned on save). On the fake feed the earlier days are sample data (`demoHistory()` in `src/data/history.ts`) and the screen says so.

## Not connected yet (UI only, said on screen)

- **Add a family member** keeps the new frame on this phone only. The hub has people only as a question's `speaker`; their replies are added in `/setup`.
- **What Sino knows** can remove a question the family added (`DELETE /questions/{id}`). The trash turns red while it is pressed and while it asks "Burahin? / Delete?"; the card leaves at once and comes back if the hub refuses. A built-in question (an id in `brain/seed.json`) stays, and the card says so. Safety words are copied from `brain/decide.py` (`URGENT_STEMS`), keep in sync.
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
  data/recorder.ts     MediaRecorder + live waveform levels (tells urgentSound.ts while it has the mic)
  data/urgentSound.ts  the urgent alarm: two tones once a second, 2-minute cap, rings on silent (Web Audio, no file)
  feed/monitor.ts      Turn on alerts: unlock sound + screen wake lock, checked again when the page is visible
  data/safetyWords.ts  copy of URGENT_STEMS
  data/askLocal.ts     fake-feed answers for Sino AI (mirrors brain/ask.py) + keyword intent for typed questions
  data/history.ts      7-day log on this phone (localStorage), sample days for the fake feed
  i18n/                tl.ts, en.ts, helpers (one / two / btn / head), times in words
  components/          Frame (MemoryFrame), SalaScene, Cards (urgent, needs, done), Alarm (Turn on alerts bar, full-screen red), SummaryChips, TopBar, TabBar, bits
  screens/             Home, Family, Ask (Sino AI), Activity, Receipt, Knows, Person, Record, AddPerson, Account
  styles/              tokens.css (design-system Appendix A), app.css
  assets/fonts/        Fredoka 500/600, DM Sans 400/700 (SIL OFL, Fontsource 5.3.0)
```
