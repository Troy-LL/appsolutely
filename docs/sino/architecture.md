# Sino: architecture

How the devices, screens, models, and data fit together. Hardware facts come from the team; model setup comes from [DONITA-SETUP.md](DONITA-SETUP.md). Anything not yet measured is in [To verify at smoke test](#to-verify-at-smoke-test).

## Devices

| Device | Role | Owner |
|---|---|---|
| Donita's M2 MacBook | **Home hub / brain:** mic, speaker (urgent chime), whisper.cpp, Ollama + Qwen2.5, the web server, the behind-the-scenes screen | Donita |
| A16 iPad | Lola's screen and speaker | Ayen (screen) |
| Troy's iPhone 15 | Caregiver phone | Viviene (screen) |
| Viviene's Windows laptop (optional) | Extra behind-the-scenes view in a browser | Viviene |
| Troy's 2017 MacBook Pro (Intel i5, 8 GB RAM, per [../03-playbook.md](../03-playbook.md)) | Not part of the demo. Development only. Any "cheaper hub" claim needs a timed run on it first | Troy |

- **Mic:** on the hub, to avoid iPad Safari's mic limits. The iPad needs one "Simulan" tap at start because iOS blocks audio autoplay.
- **Restart:** `start.sh` brings up the whole hub; a health light on `/backstage` shows each part (Whisper, Ollama, server, mic). Anyone on the team can restart it while Donita sleeps (1:00 to 4:30 AM).
- TODO (Donita): RAM of the M2, from the setup report. It decides the model pair below.

## Network

| Option | Status |
|---|---|
| **Primary:** the M2's own Wi-Fi via macOS Internet Sharing, fixed IP, mkcert HTTPS | **To verify tonight:** does Internet Sharing work with no upstream connection? Checkpoint 11:15 PM ([mvp-plan.md](mvp-plan.md)) |
| Fallback 1: an Android phone hotspot with mobile data off | Use if Internet Sharing fails without upstream |
| Fallback 2: a travel router with no internet | Same |
| Last resort for the iPad: USB-C cable to the M2 | Demo only |

All screens are served by the hub over this local network. There is no internet on the core path.

## Viewports

Each route is designed for its own device only (no responsive juggling).

| Viewport | Device | Who sees it | Route | Shows in the MVP | Only if an add-on ships | Owner |
|---|---|---|---|---|---|---|
| **Lola's screen** | A16 iPad (landscape, ~1180×820) | Lola | `/lola` | Big clock, idle family photo, full-screen photo while the family voice plays. **Nothing else.** Never red. Calm colors only | Photo of a registered person, then a call only while that person is on the house Wi-Fi (no internet). If they are not on that network, their photo and the "Sino ka?" line they recorded in setup (add-on a) | Ayen |
| **Caregiver phone** | iPhone 15 (portrait, ~393×852) | Caregiver / family | `/caregiver` | Live log; red cards (sound); quiet yellow cards with grouped repeats and record-a-reply; green log entries. A registered person can ask about Lola. "How is she" and "what has she been saying" are this log (counts and her words, not a diagnosis). Should: "Kumain na" button, recap counts | "Where is she" is the recorded-clip answer if add-on (b) is on, and "no camera answer, no room guessed" if it is off | Viviene |
| **Behind the scenes** | M2 MacBook (~1440×900) | Judges / presenters | `/backstage` | Per-utterance proof ([below](#backstage-proof)): transcript → rule or model → action, confidence, reason → ms; a dropped row; `TV lines ignored: N`; T5 badge; OFFLINE badge; health light; hidden "listen now" and typed-question box | Face match panel (a). CCTV clip with detection box (b), only if stable by 5:00 AM. No voice match panel: voice ID is cut | Viviene |
| **Setup** | iPhone 15 or iPad | Family | `/setup` | Quick setup: add question, two phrasings, hold to record, photo, test | n/a | Ayen |
| (optional) Extra backstage | Viviene's Windows laptop | Audience | `/backstage` | Mirror of the M2 view | n/a | Viviene |

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

`source` is `rule` when urgent-word rules, the medication rule, or the known-question matcher decided. `source` is `model` when Qwen decided, including a model error or timeout (that path already goes to the caregiver). `ignored` is `tv` or `""`. The hub sets `tv` when it treats the line as television. The demo clip in [demo.md](demo.md) expects `ignored` `tv` so this counter ticks. The token `decide()` uses to separate television from in-room chatter is `TODO: unknown` until the decision engine names it. This screen only reads the field.

## Models and runtimes (all on the M2, all local)

| Job | Model | Runtime | Notes |
|---|---|---|---|
| Voice activity detection | Silero VAD | hub | Starts capture only when someone speaks |
| Speech to text | Whisper small, medium, or large-v3-turbo (picked by measurement) | whisper.cpp (`-l tl`) | See the selection rule below |
| Decision for unclear lines | Qwen2.5-3B (`qwen2.5:3b`) or Qwen2.5-1.5B (`qwen2.5:1.5b`) | Ollama | Must return JSON matching the decision interface. No AI phrasing for the recap |
| Add-on a: face match | face-api.js or MobileFaceNet ONNX | browser or hub | 3 enrolled family members only |
| Add-on b: person detection | MediaPipe or YOLO | hub | Runs on a pre-recorded clip |
| Add-on c: speaker match | sherpa-onnx speaker embeddings or SpeechBrain ECAPA | hub | **Cut. Not built** ([mvp-plan.md](mvp-plan.md)) |

No text-to-speech or voice-cloning model is used anywhere: Lola only hears the family's own recordings (safety rule in [README.md](README.md#safety-rules)). Add-ons (a) and (b) sit below the cut line; (b) only if stable by 5:00 AM; (c) voice ID is cut and is not built. The camera view (b) overlaps with common offline dementia-assistant ideas, so it is a demo extra, not the story. The who-are-you moment is a call only while the registered person is on the house Wi-Fi, or the "Sino ka?" line they recorded in setup ([features.md](features.md#add-ons-behind-the-cut-line-after-the-200-am-freeze-in-this-order)).

### Speech model selection (by 11:30 PM)

1. Time Whisper **small**, **medium**, and **large-v3-turbo** on the same 4 s Tagalog clip on the M2.
2. Use **medium if it transcribes the clip in under about 1.5 s**; otherwise the fastest model whose transcript is usable.
3. RAM rule: **16 GB → medium + Qwen2.5-3B. 8 GB → small + Qwen2.5-3B, or medium + Qwen2.5-1.5B.**
4. Log the real times and the choice in `docs/NOTES.md` (Model smoke test).

**Published accuracy reference** (Whisper paper, Radford et al. 2022, FLEURS Tagalog word error rate): base 45.8%, small 27.7%, medium 19.1%. This is read speech from a benchmark, not our measurement. Lola's real Taglish will likely be worse, which is why the matcher, the urgent rules, the junk-line filter, and silent-if-unsure exist.

Web stack is the repo default in [../../AGENTS.md](../../AGENTS.md): React + Vite + Tailwind on the screens, Python FastAPI on the hub.

## The 3 interfaces (locked in the first 15 minutes)

1. **Decision** (returned by `decide()`):
   ```json
   {"action": "comfort | caregiver | urgent | silent", "reply_id": "", "reason": "", "trigger_words": [], "confidence": 0.0, "latency_ms": 0, "source": "rule | model", "ignored": ""}
   ```
   `source` and `ignored` are additive. Do not rename the other keys. `ignored` is `""` or `tv`.
2. **Events.** WebSocket at `/ws`. One JSON object per message. `event` is the name. The fake feed emits this same shape, so the screens do not wait on the hub.
   - `heard`: `{"event":"heard","transcript":"","dropped":false,"drop_reason":""}`. `transcript` is the live transcript (Lola's exact words). `dropped` is true only when the junk-line filter drops the clip: too quiet, Whisper likely no speech, or a known junk line ("Thank you for watching", "Salamat sa panonood", and similar). `drop_reason` is then `too quiet`, `likely no speech`, or `junk line`. A dropped `heard` is shown on `/backstage` as a dropped row. It does not call `decide()` and does not emit `decided`, `play_reply`, `alert`, or `ask_caregiver`. Junk lines ride on `heard`. They do not have their own event. A `junk line` drop also adds 1 to `TV lines ignored: N`. `too quiet` and `likely no speech` do not.
   - `decided`: the decision object with `"event":"decided"` added, including `source` and `ignored`. Emitted for comfort, caregiver, urgent, and silent. Silent emits `decided` and nothing else (log only). `ignored` `tv` is the television case in the [backstage proof](#backstage-proof).
   - `play_reply`: `{"event":"play_reply","reply_id":"","reply_audio":"","photo":""}` to `/lola` on comfort. `reply_audio` and `photo` come from the questions file. Lola's screen shows the photo and plays the recording, and nothing else.
   - `alert`: `{"event":"alert","transcript":""}` to `/caregiver` on urgent. The red card shows `transcript` and is the only card that plays a sound. The hub chime is separate, from the hub speaker.
   - `ask_caregiver`: `{"event":"ask_caregiver","transcript":"","count":1}` to `/caregiver` when the action is caregiver. Quiet. Repeats of the same `transcript` share one yellow card, and `count` is how many times. One tap records a reply through `POST /questions`.
   - `meal_logged`: `{"event":"meal_logged"}`. No extra fields. This is the Should meals check, after the 2 AM freeze. Clients ignore it until then. The name means the caregiver tapped "Kumain na".
   - `health`: `{"event":"health","whisper":true,"ollama":true,"server":true,"mic":true,"offline":true}`. `whisper`, `ollama`, `server`, and `mic` are the health light. `true` means that part is up. `offline` true means the OFFLINE badge is showing. Sent when a client connects and again when a part changes.
3. **Questions file:** `{id, question, phrasings[], reply_audio, photo, speaker}`. Troy's seed file is `brain/seed.json`. Donita's loader (D5) reads it, and quick setup appends to the same list.
   - `GET /questions` returns the array.
   - `POST /questions` accepts one object. `reply_audio` and `photo` are file parts (hold to record, and the photo). The hub stores the files and returns the stored object. The hub sets `id` when the client omits it. If `id` already exists, the hub replaces `reply_audio` and `photo` and keeps the question. That is the caregiver's one-tap record-a-reply.
4. **`POST /listen`:** returns 202 and no body. What happened arrives on `/ws`.
   - Listen now: `{"mode":"listen_now"}`. The hub captures from its own mic and runs VAD, Whisper, the junk filter, and `decide()`.
   - Typed question: `{"mode":"typed","text":""}`. Skips VAD, Whisper, and the junk filter. Emits `heard` with that `text` as `transcript` and `dropped` false, then `decided`.
5. **Folders:** `brain/`, `hub/`, `web/setup`, `web/caregiver`.

Changing an interface needs a post in the team chat, because every screen depends on it.

## Data flow

1. The hub mic hears speech; Silero VAD cuts the clip. (Or: "listen now" on backstage forces a capture; the typed-question box skips steps 1 to 3.)
2. whisper.cpp transcribes it on the M2 → `heard` event.
3. Junk-line filter: quiet clips, likely-no-speech clips, and known junk lines are dropped. Backstage shows them as `heard` with `dropped` true. They never reach Lola or the caregiver.
4. Throttle: one model call at a time. Stale clips are discarded and emit no event.
5. `decide()`: urgent-word rules → known-question matcher → Qwen only if still unclear → `decided` event.
6. Comfort → `play_reply` to `/lola`. Caregiver → `ask_caregiver` to `/caregiver` (quiet, grouped). Urgent → hub chime + `alert` to `/caregiver`. Silent → log only.
7. `/backstage` shows each utterance as transcript → rule or model → action, confidence, reason → ms, plus the dropped row and `TV lines ignored: N` ([backstage proof](#backstage-proof)).

## Offline guarantees

- No cloud API, model download, or internet request on the core path at runtime. Models are downloaded once during setup.
- The hub serves all screens over its own local network, so the demo runs with internet off.
- With no internet there are no push notifications (iOS push needs Apple's servers). Alerts reach people through the **hub chime** and through `/caregiver` while it is open on the local network.
- What requires internet: nothing at runtime. Setup-time downloads only (models, packages).

## Consent, privacy, and safety

- The family sets it up and controls everything. Pitch the caregiver as the user.
- The mic is always on, so **nothing it hears leaves the house**. No audio is stored by default. Only transcripts and decisions go into the local log, and the family can delete it.
- Face and voice samples (add-ons) stay on the hub.
- No cloned or synthetic family voices, ever.
- Not a medical device, not a diagnosis. It always escalates to a human.

## To verify at smoke test

None of these are facts yet. Log real results in `docs/NOTES.md` (Model smoke test) and update this list.

| Item | Expectation | Status |
|---|---|---|
| Speech-to-reply latency, known question | about 2 s | to verify at smoke test |
| Speech-to-reply latency, model decides | about 4 to 5 s | to verify at smoke test |
| Whisper small / medium / large-v3-turbo on a 4 s Tagalog clip | medium under about 1.5 s? | to verify by 11:30 PM |
| Transcript quality on Taglish speech | usable for the matcher | to verify at smoke test |
| `qwen2.5:3b` / `1.5b` JSON validity and time | valid JSON every time | to verify at smoke test |
| M2 RAM | 8 or 16 GB | TODO (Donita) |
| Internet Sharing with no upstream | iPad and iPhone reach the hub | to verify by 11:15 PM |
| Junk-line filter | drops TV sign-offs and silence, keeps real questions | to verify at smoke test |
| Hub chime audible across a room | yes | to verify at smoke test |
| Hub cold start with `start.sh` | under 2 min with seed loaded | to verify at smoke test |
| Hub on battery through the demo | needed only if we show it unplugged | to verify at smoke test |
| Add-ons (a) face match and (b) person detector | reliable on the demo set | to verify after the freeze; (b) only if stable by 5:00 AM |
| Add-on (c) voice ID | cut, not built | not measured |
