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
| **Lola's screen** | A16 iPad (landscape, ~1180×820) | Lola | `/lola` | Big clock, idle family photo, full-screen photo while the family voice plays. **Nothing else.** Never red | Greeting photo + recorded line (add-on a) | Ayen |
| **Caregiver phone** | iPhone 15 (portrait, ~393×852) | Caregiver / family | `/caregiver` | Live log; red cards (sound); quiet yellow cards with grouped repeats and record-a-reply; green log entries. Should: "Kumain na" button, recap counts | "Nasaan si Lola?" answer (add-on b) | Viviene |
| **Behind the scenes** | M2 MacBook (~1440×900) | Judges / presenters | `/backstage` | Live transcript, dropped junk lines, decision + reason + trigger words, matched reply + confidence, latency ms, OFFLINE badge, health light, hidden "listen now" button and typed-question box | Face match panel (a), CCTV clip with detection box (b), voice match panel (c) | Viviene |
| **Setup** | iPhone 15 or iPad | Family | `/setup` | Quick setup: add question, two phrasings, hold to record, photo, test | n/a | Ayen |
| (optional) Extra backstage | Viviene's Windows laptop | Audience | `/backstage` | Mirror of the M2 view | n/a | Viviene |

Viewport sizes are approximate CSS sizes; confirm on the real devices.

## Models and runtimes (all on the M2, all local)

| Job | Model | Runtime | Notes |
|---|---|---|---|
| Voice activity detection | Silero VAD | hub | Starts capture only when someone speaks |
| Speech to text | Whisper small, medium, or large-v3-turbo (picked by measurement) | whisper.cpp (`-l tl`) | See the selection rule below |
| Decision for unclear lines | Qwen2.5-3B (`qwen2.5:3b`) or Qwen2.5-1.5B (`qwen2.5:1.5b`) | Ollama | Must return JSON matching the decision interface. No AI phrasing for the recap |
| Add-on a: face match | face-api.js or MobileFaceNet ONNX | browser or hub | 3 enrolled family members only |
| Add-on b: person detection | MediaPipe or YOLO | hub | Runs on a pre-recorded clip |
| Add-on c: speaker match | sherpa-onnx speaker embeddings or SpeechBrain ECAPA | hub | 3 enrolled family members only |

No text-to-speech or voice-cloning model is used anywhere: Lola only hears the family's own recordings (safety rule in [README.md](README.md#safety-rules)). The add-on models (a, b, c) sit below the cut line; the face greeting and camera view overlap with common offline dementia-assistant ideas, so they are demo extras, not the story ([features.md](features.md#add-ons-behind-the-cut-line-after-the-200-am-freeze-in-this-order)).

### Speech model selection (by 11:30 PM)

1. Time Whisper **small**, **medium**, and **large-v3-turbo** on the same 4 s Tagalog clip on the M2.
2. Use **medium if it transcribes the clip in under about 1.5 s**; otherwise the fastest model whose transcript is usable.
3. RAM rule: **16 GB → medium + Qwen2.5-3B. 8 GB → small + Qwen2.5-3B, or medium + Qwen2.5-1.5B.**
4. Log the real times and the choice in `docs/NOTES.md` (Model smoke test).

**Published accuracy reference** (Whisper paper, Radford et al. 2022, FLEURS Tagalog word error rate): base 45.8%, small 27.7%, medium 19.1%. This is read speech from a benchmark, not our measurement. Lola's real Taglish will likely be worse, which is why the matcher, the urgent rules, the junk-line filter, and silent-if-unsure exist.

Web stack follows the repo defaults in [../../AGENTS.md](../../AGENTS.md) (React + Vite + Tailwind, Python FastAPI backend) unless the team decides otherwise. TODO: confirm.

## The 3 interfaces (locked in the first 15 minutes)

1. **Decision** (returned by `decide()`):
   ```json
   {"action": "comfort | caregiver | urgent | silent", "reply_id": "", "reason": "", "trigger_words": [], "confidence": 0.0, "latency_ms": 0}
   ```
2. **Events (WebSocket):** `heard`, `decided`, `play_reply`, `alert`, `ask_caregiver`, `meal_logged`, `health`
3. **Questions file:** `{id, question, phrasings[], reply_audio, photo, speaker}`
4. **`/listen`:** named in the MVP plan (D4). Request and response body: TODO: unknown.
5. **Folders** (from the MVP plan): `brain/`, `hub/`, `web/setup`, `web/caregiver`.

Changing an interface needs a post in the team chat, because every screen depends on it. TODO: unknown (Troy + Donita) whether dropped junk lines get their own event or ride on `heard`. No event name is written.

## Data flow

1. The hub mic hears speech; Silero VAD cuts the clip. (Or: "listen now" on backstage forces a capture; the typed-question box skips steps 1 to 3.)
2. whisper.cpp transcribes it on the M2 → `heard` event.
3. Junk-line filter: quiet clips, likely-no-speech clips, and known junk lines are dropped and shown only on backstage.
4. Throttle: one model call at a time; stale clips are dropped.
5. `decide()`: urgent-word rules → known-question matcher → Qwen only if still unclear → `decided` event.
6. Comfort → `play_reply` to `/lola`. Caregiver → `ask_caregiver` to `/caregiver` (quiet, grouped). Urgent → hub chime + `alert` to `/caregiver`. Silent → log only.
7. Every step is shown on `/backstage` with latency.

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
| Add-ons: face match, person detector, voice ID | reliable on the demo set | to verify after the freeze |
