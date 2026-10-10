# Sino: architecture

How the devices, screens, models, and data fit together. Hardware facts come from the team; model setup comes from [DONITA-SETUP.md](DONITA-SETUP.md). Anything not yet measured is in [To verify at smoke test](#to-verify-at-smoke-test).

## Devices

| Device | Role | Owner |
|---|---|---|
| Donita's MacBook Air M1 (8 GB), macOS 26.5.1 | **Home hub / brain:** mic, speaker (urgent chime), whisper.cpp, Ollama + Qwen2.5, the web server, the behind-the-scenes screen | Donita |
| A16 iPad | Lola's screen and speaker; the main mic from Sat ~7:15 AM | Ayen (screen) |
| Troy's iPhone 15 | Caregiver phone, and the rung-1 Personal Hotspot (the house network) | Viviene (screen) |
| Viviene's Windows laptop (optional) | Extra behind-the-scenes view in a browser | Viviene |
| Troy's 2017 MacBook Pro (Intel i5, 8 GB RAM, per [../03-playbook.md](../03-playbook.md)) | Not part of the demo. Development only. Any "cheaper hub" claim needs a timed run on it first | Troy |

- **Mic:** from Sat ~7:15 AM the main mic is the **iPad** at Lola's screen (Donita, after the 7:00 AM freeze), so a "Tulong!" is heard from where Lola is, not only by the Mac's mic. With the real hub (`/lola/?feed=hub`, not `?mic=off`), `/lola` listens all the time in the browser and uploads each clip to `POST /listen/audio` ([interfaces](#the-3-interfaces-locked-in-the-first-15-minutes)). iPad Safari's mic limits still apply: it needs HTTPS (the hub's mkcert URL, see [Network](#network)) and a tap to grant the mic. That tap is the "Simulan" tap at start, which iOS already needs because it blocks audio autoplay. The hub mic stays for "listen now" and always-listening; nothing was removed. Not tested yet: to verify on the iPad.
- **Restart:** `start.sh` brings up the whole hub; a health light on `/backstage` shows each part (Whisper, Ollama, server, mic). Anyone on the team can restart it while Donita sleeps (sleep times: TODO: re-decide after the 1:51 AM pair change, see [../01-team.md](../01-team.md#sleep-shifts-cross-pair)).
- Hub RAM is **8 GB** (Donita, Sat 1:20 AM). The model pair below follows the 8 GB rule.

## Network

macOS Internet Sharing failed on the hub (Sat 1:20 AM): it needs an active upstream connection, `bridge100` never appeared, and Wi-Fi can't be both the upstream and the shared network. No one on the team has an Android phone. Ladder (decided by Troy, Sat 1:23 AM):

| Rung | Network | Notes |
|---|---|---|
| **1 (primary, tonight and the demo)** | Troy's iPhone 15 Personal Hotspot (Maximize Compatibility on) + LAN-only `pf` firewall on the hub | The hotspot itself has cellular, so the hub blocks every non-local destination. Hub IP is usually 172.20.10.x |
| 2 | A spare Wi-Fi router or pocket Wi-Fi with no WAN / SIM data off | Swap in on stage if someone brings one: an offline LAN with no internet anywhere |
| 3 | iPhone USB-cabled into the M1, retry Internet Sharing from "iPhone USB" to Wi-Fi + the same firewall | Gives Internet Sharing the active upstream it needs |
| 4 | Venue Wi-Fi + the same firewall | Last resort |
| Last resort for the iPad | USB-C cable to the hub | Demo only |

**Firewall:** a `pf` anchor on the hub allows only loopback, private LAN ranges, link-local, multicast, and DHCP/mDNS out, and drops everything else. Exact files and commands: [DONITA-SETUP.md](DONITA-SETUP.md#5-network-d1). Test before relying on it. Pitch line: **"the hub is firewalled to the house network."** The OFFLINE badge on backstage must come from a real outbound check failing (for example a request to a public address timing out), not a hardcoded label.

**HTTPS:** `mkcert <hub-ip> localhost` for the hub's LAN IP on whichever rung is used (`ipconfig getifaddr en0`); regenerate if the IP changes. The mkcert root CA (`rootCA.pem`) is installed and trusted on the iPad and iPhone.

All screens are served by the hub over this local network. There is no internet on the core path.

## Viewports

Each route is designed for its own device only (no responsive juggling).

| Viewport | Device | Who sees it | Route | Shows in the MVP | Add-ons | Owner |
|---|---|---|---|---|---|---|
| **Lola's screen** | A16 iPad (landscape, ~1180×820) | Lola | `/lola` | Big clock, idle family photo, full-screen photo while the family voice plays. **Nothing else.** Never red. Calm colors only. From Sat ~7:15 AM it also listens, still calm and never red: the "Simulan" tap asks for the microphone, then it listens in the browser (off with `?mic=off`). "Sino ka?" is a known question like the others: the registered person's photo and their recorded line | Add-on (a), after the freeze: "Sino ka?" plays the matched family member's photo and line on a high-confidence match, Troy's otherwise; no extra UI | Ayen (frontend pair: Ayen + Viviene) |
| **Caregiver phone** | iPhone 15 (portrait, ~393×852) | Caregiver / family | `/caregiver` | Live log; red cards (sound); quiet yellow cards with grouped repeats and record-a-reply; green log entries. Should, after the 3:30 AM freeze: Ask Sino about Lola ("how is she" and "what has she been saying" are this log, counts and her words, not a diagnosis; "where is she" is the no-camera answer, no room guessed), "Kumain na" button, recap counts | n/a (add-ons cut) | Viviene (frontend pair: Ayen + Viviene) |
| **Behind the scenes** | M1 MacBook Air (8 GB) (~1440×900) | Judges / presenters | `/backstage` | Per-utterance proof ([below](#backstage-proof)): transcript → rule or model → action, confidence, reason → ms; a dropped row; `TV lines ignored: N`; T5 badge; OFFLINE badge; health light; hidden "listen now" and typed-question box | After the freeze: a `face_seen` row (add-on a). No CCTV view, no voice match panel (both cut) | Viviene |
| **Setup** | iPhone 15 or iPad | Family | `/setup` | Quick setup: add question, two phrasings, hold to record, photo, test | n/a | Ayen (frontend pair: Ayen + Viviene) |
| (optional) Extra backstage | Viviene's Windows laptop | Audience | `/backstage` | Mirror of the hub view | n/a | Viviene |

Viewport sizes are approximate CSS sizes; confirm on the real devices.

## Backstage proof

`/backstage` is where judges see the local AI decide. One row per utterance, in this order:

1. **Transcript**, from `heard.transcript`.
2. **Rule hit or model**, from `decided.source`: `rule` or `model`.
3. **Action, confidence, and reason**, from `decided.action`, `decided.confidence`, and `decided.reason`.
4. **Milliseconds**, from `decided.latency_ms`.

A **dropped** row replaces that chain in two cases. The junk-line filter (`heard.dropped` true) is one. A television line the decision ignores (`decided.ignored` is `tv`) is the other. The row shows the transcript and the word `dropped`. It does not play a reply and it does not raise an alert. A junk drop still does not call `decide()` and still emits no `decided` event. A TV line that is real speech is not `dropped: true`; it goes through `decide()` and comes back silent with `ignored` set to `tv`.

**Counter.** The label is exactly `TV lines ignored: N`. N starts at 0 when the screen loads. Add 1 when `heard.drop_reason` is `junk line`. Add 1 when `decided.ignored` is `tv`. Do not add for `too quiet`, `likely no speech`, or in-room chatter (`action` silent and `ignored` empty).

The small T5 badge is specified in [mvp-plan.md](mvp-plan.md). The fake feed emits this same shape, including `source` and `ignored`.

`source` is `rule` when the urgent-word rules, the "sakit ng loob" idiom, the medication rule, the TV-word rule, or the known-question matcher decided. `source` is `model` when Qwen decided, including a model error or timeout (that path already goes to the caregiver). `ignored` is `tv` or `""`. This screen only reads the field.

What `brain/decide.py` does today: the TV-word rule (`TV_PHRASES` and `TV_TOKENS`: "thank you for watching", "salamat sa panonood", abangan, kabanata, palabas, teleserye, dula, bes, balita, commercial; a TV word inside a longer word still counts) returns `silent` with `ignored` `tv` and `source` `rule`. The model path never sets `ignored`: a model `silent` comes back with `ignored` `""`. So the demo clip in [demo.md](demo.md), a long dialogue the TV-word rule may not catch, only ticks this counter if its words hit the rule. **TODO (Troy): decide whether a model `silent` should set `ignored` `tv`, or add the clip's words to the rule, before the TV beat is rehearsed.**

## Models and runtimes (all on the M1 (8 GB) hub, all local)

| Job | Model | Runtime | Notes |
|---|---|---|---|
| Voice activity detection | Silero VAD | hub | Starts capture only when someone speaks |
| Speech to text | Whisper small (default); medium only as the fallback below | whisper.cpp (`-l tl`) | See the selection rule below |
| Decision for unclear lines | Qwen2.5-3B (`qwen2.5:3b`) (default); Qwen2.5-1.5B (`qwen2.5:1.5b`) only with the medium fallback | Ollama | Must return JSON matching the decision interface. No AI phrasing for the recap |
| Add-on a: face match (T6) | OpenCV YuNet (detect) + SFace (recognise), a few MB | OpenCV, hub CPU | Enrollment and `POST /face/frame` are on the hub. Missing OpenCV returns a calm `engine: "missing"` and writes nothing. A real match is to verify when OpenCV is installed ([features.md](features.md#should-after-the-330-am-freeze)) |
| Add-on b: recorded clip | OpenCV HOG people detector | OpenCV, hub CPU | **Sat ~4:30 AM.** Files on the hub, scanned before the question. Not a live camera. Live CCTV stays a next step ([features.md](features.md)) |
| Add-on c: speaker match | n/a | n/a | **Cut. Not built** ([mvp-plan.md](mvp-plan.md)) |

No text-to-speech or voice-cloning model is used anywhere: Lola only hears the family's own recordings (safety rule in [README.md](README.md#safety-rules)). Live CCTV and voice ID are cut, and there is no live call. The recorded-clip demo reads files on the hub and does not open a camera. "Sino ka?" is a seeded known question: the iPad shows the registered person's photo and plays the line they recorded. With add-on (a) after the freeze, a high-confidence match plays that family member's line; anything else plays Troy's ([features.md](features.md#should-after-the-330-am-freeze)).

### Speech model selection (by 11:30 PM)

The hub is an M1 with 8 GB RAM, so:
1. **Default: Whisper small + `qwen2.5:3b`.** Time small on a 4 s Tagalog clip on the hub.
2. **Fallback: Whisper medium + `qwen2.5:1.5b`**, only if the timing test shows small's Tagalog transcript is unusable.
3. **Out on this hub:** medium + 3B, and large-v3-turbo (too heavy for 8 GB alongside the LLM).
4. Log the real times and the choice in `docs/NOTES.md` (Model smoke test).

**Published accuracy reference** (Whisper paper, Radford et al. 2022, FLEURS Tagalog word error rate): base 45.8%, small 27.7%, medium 19.1%. This is read speech from a benchmark, not our measurement. Lola's real Taglish will likely be worse, which is why the matcher, the urgent rules, the junk-line filter, and silent-if-unsure exist.

Web stack is the repo default in [../../AGENTS.md](../../AGENTS.md): React + Vite + Tailwind on the screens, Python FastAPI on the hub.

## The 3 interfaces (locked in the first 15 minutes)

1. **Decision** (returned by `decide()`):
   ```json
   {"action": "comfort | caregiver | urgent | silent", "reply_id": "", "reason": "", "trigger_words": [], "confidence": 0.0, "latency_ms": 0, "source": "rule | model", "ignored": ""}
   ```
   `source` and `ignored` are additive. Do not rename the other keys. `ignored` is `""` or `tv`. `brain/decide.py` returns exactly these keys (checked Sat 2:00 AM).
2. **Events.** WebSocket at `/ws`. One JSON object per message. `event` is the name. The fake feed emits this same shape, so the screens do not wait on the hub.
   - `heard`: `{"event":"heard","transcript":"","dropped":false,"drop_reason":""}`. `transcript` is the live transcript (Lola's exact words). `dropped` is true only when the junk-line filter drops the clip: too quiet, Whisper likely no speech, or a known junk line ("Thank you for watching", "Salamat sa panonood", and similar). `drop_reason` is then `too quiet`, `likely no speech`, or `junk line`. A dropped `heard` is shown on `/backstage` as a dropped row. It does not call `decide()` and does not emit `decided`, `play_reply`, `alert`, or `ask_caregiver`. Junk lines ride on `heard`. They do not have their own event. A `junk line` drop also adds 1 to `TV lines ignored: N`. `too quiet` and `likely no speech` do not.
   - `decided`: the decision object with `"event":"decided"` added, including `source` and `ignored`. Emitted for comfort, caregiver, urgent, and silent. Silent emits `decided` and nothing else (log only). `ignored` `tv` is the television case in the [backstage proof](#backstage-proof).
   - `play_reply`: `{"event":"play_reply","reply_id":"","reply_audio":"","photo":""}` to `/lola` on comfort. `reply_audio` and `photo` come from the questions file. Lola's screen shows the photo and plays the recording, and nothing else.
   - `alert`: `{"event":"alert","transcript":""}` to `/caregiver` on urgent. The red card shows `transcript` and is the only card that plays a sound. The hub chime is separate, from the hub speaker. `/lola` does not receive `alert` and does not turn red.
   - `urgent_reply`: `{"event":"urgent_reply","text":"","speaker":"","reply_audio":""}`. Additive. The caregiver socket sends it while an urgent alert is active, or `POST /urgent-reply` does (multipart `text`, `speaker`, optional file `reply_audio`). The hub stops the chime and sends this same object to every screen. `text` is the caregiver's words (for example "Papunta na ako"). `speaker` is their name. `reply_audio` is `""` or `"/media/<file>"` when they recorded a voice. `/lola` shows the name and the text in the calm answer state, plays the recording when there is one, and returns to the clock. No recording means text only. `/caregiver` and `/backstage` leave the alert's active state. A `/lola` socket that connects after the reply, and before the next urgent, receives this event after `health`, so a reconnect does not drop it.
   - `ask_caregiver`: `{"event":"ask_caregiver","transcript":"","count":1}` to `/caregiver` when the action is caregiver. Quiet. Repeats of the same `transcript` share one yellow card, and `count` is how many times. One tap records a reply through `POST /questions`.
   - `meal_logged`: `{"event":"meal_logged"}`. No extra fields on the wire. The caregiver socket sends this when they tap "Kumain na". The hub does not send it back out. It appends `{"event":"meal_logged","ts":""}` to the decisions log and stamps `ts` itself (ISO 8601).
   - `health`: `{"event":"health","whisper":true,"ollama":true,"server":true,"mic":true,"offline":true}`. `whisper`, `ollama`, `server`, and `mic` are the health light. `true` means that part is up. `offline` true means the OFFLINE badge is showing. Sent when a client connects and again when a part changes.
3. **Questions file:** `{id, question, phrasings[], reply_audio, photo, speaker}`. Troy's seed file is `brain/seed.json`. Donita's loader (D5) reads it, and quick setup appends to the same list.
   - `GET /questions` returns the array.
   - `POST /questions` accepts one object. `reply_audio` and `photo` are file parts (hold to record, and the photo). The hub stores the files and returns the stored object. The hub sets `id` when the client omits it. If `id` already exists, the hub replaces `reply_audio` and `photo` and keeps the question. That is the caregiver's one-tap record-a-reply.
   - `DELETE /questions/{id}` removes one question the family added from the hub working copy (`hub/data/questions.json`). `id` is 1–64 of `a-z 0-9 -`. An id that is in `brain/seed.json` is refused with 400 `{"error":"built-in questions stay"}` and nothing is written, so a built-in question is not lost (there is no hide/restore). An unknown id is 404 `{"error":"no question with that id"}`. On success the stored object is returned, that question's own `/media/<id>-reply…` and `/media/<id>-photo…` files are deleted, and every screen gets `{"event":"question_removed","id":""}`. The seed file is never written. Additive. TODO: contract gap — post in the team chat.
4. **`POST /listen`:** returns 202 and no body. What happened arrives on `/ws`.
   - Listen now: `{"mode":"listen_now"}`. The hub captures from its own mic and runs VAD, Whisper, the junk filter, and `decide()`.
   - Typed question: `{"mode":"typed","text":""}`. Skips VAD, Whisper, and the junk filter. Emits `heard` with that `text` as `transcript` and `dropped` false, then `decided`.
   - iPad clip: **`POST /listen/audio`**, `multipart/form-data`. Field `audio`: one file whose filename ends in `.wav`, `.m4a`, `.mp4`, `.webm`, `.ogg`, or `.aac`, not empty, up to 2 MB. Optional field `source` (`ipad`). Returns 202 and no body, or 400 `{"error":""}`. The hub converts the clip with ffmpeg to 16 kHz mono WAV and runs the same path as listen now: Whisper → junk filter → clip deleted → a dropped `heard` on backstage, or `decide()`. One clip at a time, newest wins. Clips inside the hub's deaf windows (after `play_reply`, after the chime; see always-listening below) are ignored, so a cry inside those windows is not heard from the iPad either. Results arrive on `/ws` as the events above; no new events. **Additive change after the 7:00 AM freeze** (Donita, Sat ~7:15 AM); nothing existing changes. Post in the team chat (TODO: Donita).
5. **Folders:** `brain/`, `hub/`, `web/setup`, `web/caregiver` (served at `/caregiver/`), `web/lola` (served at `/lola/`), `web/backstage` (served at `/backstage/`).

**Ask Sino about Lola:** the caregiver socket sends `{"event":"ask_about_lola","question":""}` and that socket alone gets `{"event":"about_lola","intent":"","answer":"","source":"","latency_ms":0}` (`answer_about_lola()`). TODO: contract gap — those event names were not in the locked list. Post them in the team chat.

**Running the brain without the hub:** `SINO_MODEL=stub` (the default) never opens a socket; lines the rules and matcher miss go to the caregiver. `SINO_MODEL=ollama` posts to `{HUB_URL}/api/generate` with `qwen2.5:3b` (`HUB_URL` defaults to `http://localhost:11434`), 4 s timeout. Text test: `SINO_MODEL=stub python3 brain/tests/run_t5.py`; Ask about Lola cases: `cd brain && python3 ask.py`.

Changing an interface needs a post in the team chat, because every screen depends on it.

## Data flow

1. The iPad mic (the main input from Sat ~7:15 AM): `/lola` cuts a clip in the browser with a loudness gate (12 dB over the noise floor, ~0.3 s kept before the start, ends after 0.8 s of quiet, clips 0.5–8 s), encodes it as WAV, and uploads it to `POST /listen/audio`; the hub converts it to 16 kHz mono WAV. The iPad pauses while a family reply plays and for 1 s after. Thresholds not tuned yet: to verify on the iPad. Or the hub mic hears speech; Silero VAD cuts the clip. (Or: "listen now" on backstage forces a capture; the typed-question box skips steps 1 to 3.)
2. whisper.cpp transcribes it on the hub → `heard` event.
3. Junk-line filter: quiet clips, likely-no-speech clips, and known junk lines are dropped. Backstage shows them as `heard` with `dropped` true. They never reach Lola or the caregiver.
4. Throttle: one model call at a time. Stale clips are discarded and emit no event, except a line with an urgent word: it is always decided (README safety rule 1).
5. `decide()`: urgent-word rules (built-in stems, then a custom safety word when the line is not a TV line) → "sakit ng loob" idiom (caregiver) → medication (caregiver) → TV words (silent, `ignored` `tv`) → known-question matcher → Qwen only if still unclear → `decided` event. A custom word is urgent by rule. It does not override a TV line.
6. Comfort → `play_reply` to `/lola`. Caregiver → `ask_caregiver` to `/caregiver` (quiet, grouped). Urgent → hub chime + `alert` to `/caregiver` (`/lola` stays on the clock, never red). A caregiver `urgent_reply` stops the chime and goes to every screen; `/lola` shows their name and words (and plays the recording when there is one), then returns to the clock. Silent → log only.
7. `/backstage` shows each utterance as transcript → rule or model → action, confidence, reason → ms, plus the dropped row and `TV lines ignored: N` ([backstage proof](#backstage-proof)).

## Running the hub server

`brain/server.py` is the hub process. It serves `/ws`, `POST /listen`, `POST /listen/audio`, `POST /urgent-reply`, `GET /questions`, `POST /questions`, `DELETE /questions/{id}`, `GET /safety-words`, `POST /safety-words`, `GET /log`, `POST /clips`, `GET /clips/rooms`, `GET /clips/snapshot`, `GET /clips/file/{room}`, `POST /face/frame`, `POST /face/enroll/{person}`, `GET /face/gallery`, and `/media`, and it calls `decide()` and `answer_about_lola()`. When `web/caregiver/dist` exists it also serves that build at `/caregiver` (`index.html` with `Cache-Control: no-cache`); the phone opens `https://<hub>:8000/caregiver/?feed=hub` so `/ws`, `/questions`, `/media`, `/clips`, and `/face` share one origin. Plain `ws://` unless `CERT` and `KEY` are both set (mkcert files), then `wss://`.

TODO: contract gap — custom safety words. Additive, nothing renamed. The built-in stems stay in `brain/decide.py` (`URGENT_STEMS`). The caregiver card can add a word; it cannot remove a built-in.

- `GET /safety-words` returns `{"builtin":[],"custom":[]}`. `builtin` is `URGENT_STEMS`. `custom` is the family's list.
- `POST /safety-words` accepts `{"word":""}`. The hub trims, lowercases, and strips punctuation the same way `normalize()` does. Empty is 400 `{"error":"empty"}`. Under 4 letters is `{"error":"short"}`. Over 40 characters is `{"error":"long"}`. A duplicate of a built-in stem (including the English urgent phrases and the fuzzy solos such as `dibdib`) or of a saved word is `{"error":"duplicate"}`. Otherwise the word is appended to `hub/data/safety-words.json` and the response is `{"word":""}` with the stored spelling. `SINO_SAFETY_WORDS` overrides that file. `HUB_DATA` overrides the folder, same as the questions working copy.
- `safety_word`: `{"event":"safety_word","word":""}` goes to the caregiver and backstage sockets when a word is saved, so other open screens show it. `decide()` reads the file on the next line. A custom hit is urgent, same fuzzy rules as the built-ins, unless the line is already a TV line: then the TV rule still wins and `ignored` stays `tv`.

TODO: contract gap — the interfaces do not name a listen port. `PORT` defaults to 8000. `HOST` defaults to `0.0.0.0`.

TODO: contract gap — `/ws` does not say which socket is `/lola`, `/caregiver`, or `/backstage`. Additive query `screen` is one of `lola`, `caregiver`, `backstage`. A caregiver socket may also send `monitor=1`. That socket also receives `heard`, `face_seen`, and silent `decided`. A plain caregiver socket stays quiet on those. `clip_scan` stays on backstage only.

TODO: contract gap — `decided` has no transcript. Additive field `transcript` (same string as `heard.transcript`). Silent `decided` goes to `/backstage` only. Comfort, caregiver, and urgent go to every screen.

TODO: contract gap — additive, nothing renamed. `heard` and `decided` gain `utterance_id`, the same string for one utterance, so `/backstage` pairs them into one row. The listen-drop `heard` (`dropped` true) carries its own `utterance_id` and does not emit `decided`.

TODO: contract gap — `health` has no model mode or last event time. Additive fields `model` (`stub` or `ollama`) and `last_event_at` (ISO 8601, or `""` before the first decision). `GET /health` returns that same object. `offline` is true only when an outbound request fails (`https://example.com` by default, `OFFLINE_PROBE` overrides). `mic` is described under listen now below.

TODO: contract gap — listen now has no VAD yet. `POST /listen` `{"mode":"listen_now"}` returns 202 at once, then `hub/listen.py` records one fixed clip of `LISTEN_SECONDS` (default 4.5 s) from `MIC_DEVICE` (default `:0`) with `ffmpeg -f avfoundation` (16 kHz mono WAV in the system temp folder). whisper-server (`127.0.0.1:8080/inference`, temperature 0, 10 s timeout) transcribes it, and the clip is deleted right after, so no audio is kept. One capture at a time: a press during a capture is ignored. A recording or Whisper failure emits nothing; the health light shows it.

TODO: contract gap — junk filter thresholds. `too quiet`: the loudest sample is under `QUIET_DBFS` (default -45 dBFS, not measured on the hub mic yet: to verify at smoke test), and Whisper is skipped. `likely no speech`: nothing but Whisper markers is left (`[BLANK_AUDIO]`, `(silence)`, `[MUSIC]`, `♪`). `junk line`: after lowercasing and removing punctuation, the line is only these phrases: "thank you (so much) for watching", "thanks for watching", "(maraming) salamat sa panonood", "(please) (like and) subscribe". Any extra word keeps the line, and `decide()` judges it. Drops go to `/backstage` only. `WHISPER_HINT=1` sends the known questions as Whisper's prompt; it is off by default because it may make TV lines sound like known questions.

TODO: contract gap — `mic` in `health`. It is true at start when ffmpeg's device list has `MIC_DEVICE`, then true after each good recording, and false after a failed recording or an all-zero clip (no real room is exactly zero). Only `python3 brain/server.py` opens the mic; a test that imports `app` keeps `mic` false and listen now does nothing. macOS asks once for microphone permission for the app that starts the server (Terminal, iTerm, or the editor). Allow it. TODO: check on the hub whether a denied permission shows as a failed recording or as an all-zero `too quiet` clip.

TODO: contract gap — always-listening (D4) is **off by default**. `ALWAYS_LISTEN=1` turns it on (`ALWAYS_LISTEN=1 hub/start.sh`, which passes it to the server); only `main()` reads it, so tests never open the mic. `hub/always.py` keeps one `ffmpeg -f avfoundation` reading `MIC_DEVICE` as raw 16 kHz mono PCM and cuts clips with a loudness gate, no VAD package: speech starts when a 30 ms frame is `GATE_MARGIN_DB` (default 12) dB above a slow-moving noise floor, or above `GATE_DBFS` when that is set; 0.3 s before the start is kept; the clip ends after `SILENCE_SECONDS` (default 0.8) of quiet or at `MAX_CLIP_SECONDS` (default 8); under 0.5 s of sound is thrown away; the first second after ffmpeg starts only learns the room. whisper-server's Silero VAD (`--vad`) then checks for real speech (none gives `likely no speech`). Each clip then follows listen now: Whisper, junk filter, deleted at once, backstage drop or `decide()`. One clip at a time: a newer clip replaces one still waiting, which is deleted with no event. Clips are dropped with no event while a listen now capture runs, for `REPLY_DEAF_SECONDS` (default 12) after `play_reply`, and for `CHIME_DEAF_SECONDS` (default 9) after the urgent chime starts, so the hub does not transcribe the iPad's reply or its own chime; a cry for help inside those windows is not heard by always-listening (listen now and the typed box still work). If ffmpeg stops, `mic` goes false and it is restarted every 3 s. Thresholds are not tuned on the hub mic yet: to verify at smoke test.

TODO: contract gap — no route or event for Ask Sino about Lola. Inbound on `/ws` from the caregiver socket: `{"event":"ask_about_lola","question":""}`. Reply to that socket only: `{"event":"about_lola","intent":"","answer":"","source":"","latency_ms":0}`.

TODO: contract gap — caregiver reply to an urgent alert. Additive, nothing renamed. Post in the team chat. The wire shape is `urgent_reply` in the events list above. The decisions log gains `{"event":"urgent_reply","ts":"","speaker":""}` only: the hub stamps `ts`, and the words stay on the wire so the log does not keep the reply text.

TODO: contract gap — meals check (T4m), for Viviene's V4. Post in the team chat. The wire `meal_logged` stays `{"event":"meal_logged"}`; the hub stamps `ts` on the log line only. On comfort for `meal-check`, `decided` gains additive `reply_variant` (`ate`, `ate_repeat`, or `unknown`) and `last_meal_ts` (that hub `ts`, or `""` when no meal is logged). `play_reply` uses the matching object in seed `replies` (`reply_audio`, `photo`, `speaker`); the question's top-level `reply_audio` and `photo` are the fallback. `unknown` also sends a quiet `ask_caregiver` whose `transcript` is "Lola asked if she's eaten. No meal logged." The same log counts food asks since that meal for the recap.

TODO: contract gap — `play_reply` has no speaker name. Additive field `speaker`: the speaker of the reply that actually played, `""` when unknown. A "Sino ka?" face match uses that person's `by_person` entry; `meal-check` uses the chosen variant's `speaker`; otherwise the seed `speaker` for that `reply_id`. Lola's screen shows it as the name on the frame and never invents one.

TODO: contract gap — recorded-clip demo, all additive, nothing renamed. Post them in the team chat. Footage stays on the hub (`brain/clips/media/`, gitignored). Frames stay in memory. The snapshot goes to the caregiver only, never to Lola's screen.

- `POST /clips`: optional multipart file `clip` (`.mp4`, `.mov`, `.webm`). Saving a file, or a POST with no file, scans the folder again. The scan also runs at startup, in the background when clips are present, and never when the question is asked.
- `GET /clips/snapshot`: the latest in-memory JPEG, or 404 when nothing was detected. Optional `?room=` (`hagdan`, `kainan`, or `balkonahe`) returns that room's JPEG instead of the winner.
- `GET /clips/rooms`: `{rooms:[{id,tl,en,file,detected,clip_offset_s,scanned_at}]}` for Hagdan, Kainan, and Balkonahe, in that order, even when a file is missing. `stairs.MOV` is Hagdan, `dining.MOV` is Kainan, `balcony.MOV` is Balkonahe.
- `GET /clips/file/{room}`: that room's video (`video/mp4`, `video/quicktime`, or `video/webm`). Unknown ids (including `kusina`) are 404.
- `about_lola` gains `snapshot` (`"/clips/snapshot"`) and `label` (`"RECORDED CLIP · DEMO"`) only when the answer comes from a recording. The spoken room is the Tagalog name (Hagdan, Kainan, Balkonahe). The files are `stairs.MOV`, `dining.MOV`, and `balcony.MOV`.
- `clip_card` (caregiver socket only, when nothing was detected): `{"event":"clip_card","text":"Hindi ko sigurado kung nasaan si Lola. Pakitingnan."}`.
- `clip_scan` (backstage, one per scan): `{"event":"clip_scan","rooms":[],"frames":0,"detections":0,"ms":0}`.

**Add-on a, face match.** TODO: contract gaps, all additive, nothing renamed. `POST /face/frame` is unchanged.

- `POST /face/frame`: one JPEG, sent **once per "Sino ka?" trigger** (no stream, no polling loop). Recognises against the enrolled family (troy, joy, donita). That frame stays in memory.
- `face_seen` (to `/backstage`, and to a caregiver socket with `monitor=1`): who was recognised and the score, or nobody.
- `decided.who`: additive field on a "Sino ka?" decision, the matched person on a high-confidence match, `""` otherwise.
- Seed `sino-ka` gains additive `by_person`: the reply per enrolled person. No high-confidence match → Troy's line.
- `POST /face/enroll/<person>`: multipart field `frames`, 1 to 5 JPEGs, person exactly `troy`, `joy`, or `donita`. Optional `replace=1`. Unknown person is 400 `{"error":"unknown person"}`. Zero or more than five files is 400 `{"error":"send 1 to 5 jpegs"}`. HTTP 200 is `{person, engine: "ok"|"missing", frames: [{ok:true}|{ok:false, reason:"no_face"|"engine_missing"}], count}`. A frame over 2 MB or a bad embed is `no_face`, not 500. Missing OpenCV writes nothing.
- `GET /face/gallery`: `{engine, people:{troy,joy,donita}}` counts. Enrollment crops stay in that person's gallery on the hub and do not leave the LAN. The first good frame, cropped to the face, fills an empty `by_person.<id>.photo` on the hub working copy only (`/media/sino-ka-<id>-photo.jpg`); `brain/seed.json` is never written. New crops are stored in `hub/data/faces/<person>/`. A hub that already has crops in `brain/face/gallery/` keeps using that folder. `face_photo`: `{"event":"face_photo","person":"","photo":""}` goes to the caregiver when that photo is saved, so an open Family screen reloads it. The caregiver frame uses `by_person.<id>.photo`, then a question `photo`. Lola's "Sino ka?" answer uses the matched person's photo, or Troy's `by_person` photo when the question's own photo is empty.

TODO: contract gap — `GET /log` returns the decisions log `{"entries":[]}`. A caregiver or backstage socket receives `{"event":"log","entries":[]}` after `health` when that log is not empty, so a refresh shows meals, decisions, and whether an urgent was answered. The log file stays `brain/decisions.jsonl` (`SINO_LOG` overrides it). `hub/data/urgent-ack.json` keeps the open alert and the last urgent reply (`text`, `speaker`, `reply_audio`) so a hub restart still replays it to Lola. The decisions log line for that reply stays `speaker` and `ts` only.

TODO: contract gap — the local log is not named as SQLite or JSONL. This server appends one JSON object per decision to `brain/decisions.jsonl` (`SINO_LOG` overrides the path). `answer_about_lola` reads those rows.

TODO: contract gap — `POST /questions` field encoding was not named. Multipart form: `id` (optional, 1–64 of `a-z 0-9 -`), `question` (1–300 chars, needed for a new id), `speaker` (up to 60 chars), and `phrasings` as repeated fields (`phrasings=a&phrasings=b`, up to 10, each 1–300 chars). File parts `reply_audio` (needed for a new id: `.webm .m4a .mp4 .wav .mp3 .ogg .aac`) and `photo` (`.jpg .jpeg .png .webp .heic`), not empty, up to 10 MB, with a filename that has one of those extensions. Returns the stored object; bad input is 400 `{"error":""}`. On an existing id a non-empty `speaker` is also replaced.

TODO: contract gap — where new questions and files live. The hub keeps its own copy of the list in `hub/data/questions.json` (gitignored, copied from `brain/seed.json` the first time; the seed is never changed) and the files in `hub/data/media/`, served at `/media/<file>`. `reply_audio` and `photo` hold `"/media/<file>"` or `""`; the hub names the files `<id>-reply.<ext>` and `<id>-photo.<ext>`. `HUB_DATA` overrides the data folder. `python3 brain/server.py` sets `SINO_SEED` to the working copy, and `load_seed()` reads `SINO_SEED` when that file exists, else `brain/seed.json`. Default recordings ship in git in `brain/media/` (Joy's four comfort replies and three meal clips) and the seed points at them as `/media/<id>-reply.m4a` (`meal-check-ate-reply.m4a`, `meal-check-ate-repeat-reply.m4a`, `meal-check-unknown-reply.m4a`; the unknown clip is also `meal-check`'s top-level fallback). On start the hub copies any of these files missing from `hub/data/media/`, and fills only empty `reply_audio`/`photo` fields (including `replies` and `by_person`) of an existing working copy from the seed, so a caregiver's own recording is never overwritten. `/media` serves `.m4a` as `audio/mp4`.

Mac (stub, plain `ws://`):

```bash
python3 -m venv .venv && .venv/bin/pip install fastapi 'uvicorn[standard]' python-multipart
SINO_MODEL=stub .venv/bin/python brain/server.py
SINO_MODEL=stub .venv/bin/python brain/tests/fake_hub.py
SINO_MODEL=stub .venv/bin/python brain/tests/test_server.py
SINO_MODEL=stub .venv/bin/python brain/tests/test_media.py
SINO_MODEL=stub .venv/bin/python brain/tests/test_urgent_reply.py
```

Hub (M1, Ollama, mkcert `wss://`):

```bash
HOST=0.0.0.0 PORT=8000 SINO_MODEL=ollama HUB_URL=http://127.0.0.1:11434 CERT=/absolute/path/cert.pem KEY=/absolute/path/key.pem python3 brain/server.py
```

**One command (D6): `hub/start.sh`.** Run it from the repo on the hub. Anyone on the team can.

```bash
hub/start.sh          # start what is not answering, warm qwen2.5:3b, print the health light
hub/start.sh status   # health light only: Whisper, AI model, server, mic, offline, plus the hub URL
hub/start.sh stop     # stop only what hub/start.sh started
```

- A part that already answers is left alone: Ollama (`127.0.0.1:11434`), whisper-server (`127.0.0.1:8080`), the hub server (`https://localhost:8000/health`). A part that does not is started in the background: `ollama serve` with `OLLAMA_KEEP_ALIVE=-1`, whisper-server with `-l tl` (plus `--vad --vad-speech-pad-ms 200` when the Silero model file is there), and `brain/server.py` with the hub line above and the certificates in `~/sino/certs/`. It waits up to 60 s in total. If a part did not come up, it names it and its log and exits non-zero. Don't press Ctrl+C while it starts things.
- Logs are `~/sino/logs/<part>.log` and PID files are `~/sino/run/<part>.pid`. `stop` only stops the PIDs in those files, and leaves processes started by hand alone. Every setting at the top of the script can be overridden with an environment variable.
- Keep-warm: start loads `qwen2.5:3b` (`keep_alive` -1), then a loop sends a one-token request every 60 s. Reason: after ~35 min idle the first request took 9.00 s because macOS swapped the model out (`docs/NOTES.md`, model smoke test).
- It does not touch the firewall. It prints the enable command (`sudo pfctl -f /etc/pf.sino.conf -e`), and warns when the certificate does not include the hub's current IP.
- Urgent chime: `hub/chime.py` runs `afplay -v 1 /System/Library/Sounds/Glass.aiff` 5 times, back to back (about 8.25 s, never two alarms at once), at the moment `alert` goes to `/caregiver` ([hub-chime.md](hub-chime.md)). Only `brain/server.py` `main()` turns it on, so tests make no sound. `CHIME=0` keeps it off. Audible across a room: to verify at smoke test.

## Offline guarantees

- No cloud API, model download, or internet request on the core path at runtime. Models are downloaded once during setup.
- The hub serves all screens over its own local network, so the demo runs with internet off.
- With no internet there are no push notifications (iOS push needs Apple's servers). Alerts reach people through the **hub chime** and through `/caregiver` while it is open on the local network.
- What requires internet: nothing at runtime. Setup-time downloads only (models, packages).

## Consent, privacy, and safety

- The family sets it up and controls everything. Pitch the caregiver as the user.
- The mic is always on, so **nothing it hears leaves the house**. No audio is stored by default. Only transcripts and decisions go into the local log, and the family can delete it.
- No voice samples are collected (voice ID is cut). No CCTV (cut). Family recordings and photos for replies stay on the hub.
- Face match: troy, joy, and donita enroll from the caregiver phone. Gallery crops stay on the hub, are gitignored, and never leave the LAN. The one "Sino ka?" frame stays in memory. Recorded room clips stay on the hub too. There is no live camera on the caregiver monitor.
- No cloned or synthetic family voices, ever.
- Not a medical device, not a diagnosis. It always escalates to a human.

## To verify at smoke test

None of these are facts yet. Log real results in `docs/NOTES.md` (Model smoke test) and update this list.

| Item | Expectation | Status |
|---|---|---|
| Speech-to-reply latency, known question | about 2 s | to verify at smoke test |
| Speech-to-reply latency, model decides | about 4 to 5 s | to verify at smoke test |
| Whisper small on a 4 s Tagalog clip (medium only if small is unusable) | small's transcript usable | measured Sat ~1:35 AM: 0.76 s warm on a 3.55 s clip, but the transcript was wrong ("nasaanzi na nai."). One clip, one voice; more clips needed. See `docs/NOTES.md` |
| Transcript quality on Taglish speech | usable for the matcher | to verify at smoke test |
| `qwen2.5:3b` / `1.5b` JSON validity and time | valid JSON every time | `3b` measured Sat ~1:30 AM on 62 lines: 62/62 valid with `format: "json"` (median 1.68 s), 60/62 without (median 1.51 s). `1.5b` not measured here. See `docs/NOTES.md` |
| Hub RAM | 8 GB (M1) | confirmed by Donita, Sat 1:20 AM |
| Offline network (rung 1: iPhone hotspot + firewall) | iPad and iPhone reach the hub over HTTPS | passed for the iPad, Sat 2:00 AM (Donita's iPhone hotspot). iPhone not tested yet. See `docs/NOTES.md` |
| LAN-only firewall | outbound check fails, LAN still works | passed Sat 2:00 AM after the rule fix in [DONITA-SETUP.md](DONITA-SETUP.md#5-network-d1). See `docs/NOTES.md` |
| T5 in `ollama` mode on the hub | gate in [mvp-plan.md](mvp-plan.md#passfail-gate-t5-before-the-330-am-freeze) | waiting on the hub. Stub-mode text results only so far ([../NOTES.md](../NOTES.md#passfail-gate-t5)) |
| Junk-line filter | drops TV sign-offs and silence, keeps real questions | to verify at smoke test |
| Hub chime audible across a room | yes | to verify at smoke test |
| iPad mic (`/lola` listening, Sat ~7:15 AM) | a "Tulong!" said at the iPad reaches the hub and alerts | not tested yet: to verify on the iPad |
| Hub cold start with `start.sh` | under 2 min with seed loaded | to verify at smoke test |
| Hub on battery through the demo | needed only if we show it unplugged | to verify at smoke test |
| Add-on (a) face match | runs on the hub CPU next to Whisper and Qwen without swapping; if the hub swaps, fall back to `qwen2.5:1.5b` | routes are in; a real YuNet/SFace run is to verify when OpenCV is installed |
| Add-on (b) person detector | n/a | cut, not built |
| Add-on (c) voice ID | cut, not built | not measured |
