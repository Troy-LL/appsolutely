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

## Contract gaps for the team

These are things the screen is built for but cannot fully exercise under the
current `/ws` contract in `docs/sino/architecture.md`. None of them are bugs in
this screen; they need a team decision, not a change here.

- **The Listening ring is unreachable today.** The spec says a `heard` event
  (with `dropped` false) switches Lola to Listening, and the handler is built.
  But both the hub (`brain/server.py`) and the fake feed route `heard` to
  `/backstage` only, so Lola's screen never receives it. The ring will light up
  the moment `heard` is also sent to the `lola` socket.
- **No reply text.** `play_reply` carries `reply_id`, `reply_audio` and `photo`,
  but no words. The reply line stays blank until the hub (or the questions file)
  provides an optional `reply_text`. The screen does not invent a line.
- **`MAX_VOLUME` is a placeholder.** Playback is capped at `0.8` in `lola.js`
  pending decision D5 (the real volume is set together on the iPad at test time).

## Files

- `index.html` — the three state layers, the Start sheet (language choice + Start), the FAKE label.
- `lola.css` — the look (ink-on-paper tokens, the picture frame, motion, Start-sheet buttons).
- `lola.js` — language choice, clock, state switching, feed wiring, speaker-name lookup, audio queue.
- `strings.js` — every UI word, one key per word with a value per language. Nothing is hardcoded in the HTML.
- `fonts/` — local woff2 files (see `fonts/README.md`); falls back to system-ui.
