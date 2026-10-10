# Lola's iPad screen (`/lola`)

One wall of the sala: a clock while Sino waits, one framed memory when family
answers. Ink on paper only. Plain HTML/CSS/JS, no build step, no dependencies.

## How to run

The screen imports the shared fake feed from `../fake-feed/`, so it must be
served from the `web/` folder (the same way the hub serves every screen), not
from `web/lola/`.

```
cd web
python -m http.server 8000
```

Then open <http://localhost:8000/lola/>.

Opening `index.html` directly from disk (a `file://` URL) will **not** work:
the page imports `../fake-feed/index.js`, which the browser can only resolve
when both `/lola/` and `/fake-feed/` are served over the same origin.

## Page options

Add these to the URL:

- `?feed=hub` — use the real hub socket instead of the practice feed. The FAKE
  label is hidden in this mode.
- `?hub=host:port` — point the real socket (and `GET /questions` / `/media`) at
  a specific hub, e.g. `?feed=hub&hub=172.20.10.3:8000`.
- `?big` — bigger text for Lola (text 44, second lines 28, names 28/44, time 72).
- `?time=17:15` — freeze the clock at a fixed time (for tests). Without it the
  clock follows the device time and redraws once a minute.
- `?lang=tl|en` — force the language. Without it the screen uses the family's
  saved choice (from the Start sheet), falling back to Tagalog (`tl`).
- `?mic=off` — the iPad does not listen (see [Microphone](#microphone)).

## Language

The screen shows **one** language at a time, never a "Tagalog / English" pair.
The language is chosen in this order: `?lang` in the URL, else the choice the
family saved on the Start sheet (stored in `localStorage`, with a try/catch so
it still works where storage is blocked), else Tagalog (`tl`). `<html lang>` is
set to match. Speaker names and reply lines are the family's own words and are
never translated.

Before Guided Access, the Start sheet shows two plain buttons ("Tagalog" and
"English", each written in its own language) and then Start. Picking a language
saves it and switches the Start and help text at once. After Start, no language
choice is on screen.

### Adding a language

Everything is in `strings.js`:

1. Add the two-letter code to `LANGS` (e.g. `['tl', 'en', 'ceb']`).
2. Add that key with its value to every entry in `STRINGS` (the day-parts, the
   reassurance line, the listening caption, `start`, `startHelp`, `fake`).
3. Add the language's own name to `LANG_NAMES` (e.g. `ceb: 'Bisaya'`).

No other file changes. A new language in `LANGS` automatically gets a button on
the Start sheet, and a missing value for the chosen language falls back to `tl`.

## Microphone

Lola speaks to the iPad. With `?feed=hub`, the "Simulan" tap also asks for the
microphone, and iPadOS shows its permission prompt then: tap Allow. After that
the screen listens all the time; Lola never presses anything. `mic.js` does it:

- **Clips.** A loudness gate with the same defaults as `hub/always.py`: a clip
  starts when a 30 ms frame is 12 dB above a slow-moving noise floor, keeps
  0.3 s from just before (so the start of "Tulong" is not cut), ends after
  0.8 s of quiet, is thrown away if under 0.5 s, and is cut at 8 s. The first
  second only learns how loud the room is.
- **Upload.** Each clip is sent as a 16 kHz mono 16-bit WAV (8 s is about
  256 KB) to `POST /listen/audio` (`audio` = `clip.wav`, `source` = `ipad`).
  One upload at a time; if more clips finish meanwhile, only the newest waits.
  The hub runs Whisper, the junk filter and `decide()`, and the results come
  back on `/ws` as usual. No audio is kept on the iPad.
- **Not hearing ourselves.** While a family reply plays, and for 1 s after it
  ends, the iPad throws away what it hears. The browser's echo cancellation is
  also on, and the hub separately ignores clips right after a reply or the chime.
- **Calm screen.** Nothing new is shown to Lola. If the mic is denied or
  missing, the screen works exactly as before and one line goes to the console
  (`mic: off (...)`). iPadOS shows its own mic indicator while it listens.

It needs:

- **HTTPS**: open the hub's mkcert URL (`https://<hub-ip>:8000/lola/?feed=hub`).
  Over plain `http://` on the LAN, Safari offers no microphone at all.
- **`?feed=hub`**: the practice feed never uses the mic. `?mic=off` turns it off.
- **Auto-Lock set to Never** on the iPad during the demo (Settings → Display &
  Brightness): a locked screen stops the mic. If iPadOS stops it anyway (a call,
  Siri), coming back to the page wakes the audio and asks for the mic again; if
  that fails, reload and tap Simulan.

The gate is not tuned on the iPad mic yet: to verify at smoke test. Test the
pure parts (gate, WAV, upload queue) with `node web/lola/mic.test.mjs`.

## Playing a reply

A comfort decision arrives on the lola socket as `play_reply`. `reply_audio` is
`/media/...` on the hub (the same origin as `/lola/`, http or https with the page).
The Simulan tap plays a one-sample silent clip on one audio element and resumes
an AudioContext. That is the only gesture iPad Safari needs. Later replies reuse
that element, for a typed question, the iPad mic, and "Sino ka?". While the mic
is on, the clip plays through that AudioContext, because Safari will not sound
an `<audio>` element that is sharing the speakers with the microphone. If Safari
refuses `play()` on the element, the same context plays the file. A tap anywhere
replays a reply the browser blocked. `web/lola/reply.test.py` checks both paths.

## Contract gaps for the team

These are things the screen is built for but cannot fully exercise under the
current `/ws` contract in `docs/sino/architecture.md`. None of them are bugs in
this screen; they need a team decision, not a change here.

- **The Listening ring is unreachable today.** The spec says a `heard` event
  (with `dropped` false) switches Lola to Listening, and the handler is built.
  But both the hub (`brain/server.py`) and the fake feed route `heard` to
  `/backstage` only, so Lola's screen never receives it. The ring will light up
  the moment `heard` is also sent to the `lola` socket.
- **No reply text on `play_reply`.** That event carries `reply_id`, `reply_audio` and `photo`,
  but no words. The reply line stays blank until the hub provides an optional `reply_text`.
  A caregiver's urgent reply is a different event, `urgent_reply`: `text`, `speaker`, and
  `reply_audio`. The screen shows the name and the text in the answer state (ink on paper),
  plays the recording on the unlocked player when there is one, then returns to the clock.
- **`MAX_VOLUME` is a placeholder.** Playback is capped at `0.8` in `lola.js`
  pending decision D5 (the real volume is set together on the iPad at test time).

## Files

- `index.html` — the three state layers, the Start sheet (language choice + Start), the FAKE label.
- `lola.css` — the look (ink-on-paper tokens, the picture frame, motion, Start-sheet buttons).
- `lola.js` — language choice, clock, state switching, feed wiring, speaker-name lookup, audio queue.
- `mic.js` — the iPad listens: mic on the Simulan tap, loudness gate, WAV, upload to the hub.
- `mic.test.mjs` — Node test for the gate, the WAV encoder and the upload queue.
- `strings.js` — every UI word, one key per word with a value per language. Nothing is hardcoded in the HTML.
- `fonts/` — local woff2 files (see `fonts/README.md`); falls back to system-ui.
