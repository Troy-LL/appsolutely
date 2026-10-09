# Sino: architecture

How the devices, screens, models, and data fit together. Hardware facts come from the team; model setup comes from [DONITA-SETUP.md](DONITA-SETUP.md). Anything not yet measured is in [To verify at smoke test](#to-verify-at-smoke-test).

## Devices

| Device | Role | Owner |
|---|---|---|
| Donita's MacBook Air M1 (8 GB), macOS 26.5.1 | **Home hub / brain:** mic, speaker (urgent chime), whisper.cpp, Ollama + Qwen2.5, the web server, the behind-the-scenes screen | Donita |
| A16 iPad | Lola's screen and speaker | Ayen (screen) |
| Troy's iPhone 15 | Caregiver phone, and the rung-1 Personal Hotspot (the house network) | Viviene (screen) |
| Viviene's Windows laptop (optional) | Extra behind-the-scenes view in a browser | Viviene |
| Troy's 2017 MacBook Pro (Intel i5, 8 GB RAM, per [../03-playbook.md](../03-playbook.md)) | Not part of the demo. Development only. Any "cheaper hub" claim needs a timed run on it first | Troy |

- **Mic:** on the hub, to avoid iPad Safari's mic limits. The iPad needs one "Simulan" tap at start because iOS blocks audio autoplay.
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
| **Lola's screen** | A16 iPad (landscape, ~1180×820) | Lola | `/lola` | Big clock, idle family photo, full-screen photo while the family voice plays. **Nothing else.** Never red. Calm colors only. "Sino ka?" is a known question like the others: the registered person's photo and their recorded line | n/a (add-ons cut) | Ayen (frontend pair: Ayen + Viviene) |
| **Caregiver phone** | iPhone 15 (portrait, ~393×852) | Caregiver / family | `/caregiver` | Live log; red cards (sound); quiet yellow cards with grouped repeats and record-a-reply; green log entries. Should, after the 3:30 AM freeze: Ask Sino about Lola ("how is she" and "what has she been saying" are this log, counts and her words, not a diagnosis; "where is she" is the no-camera answer, no room guessed), "Kumain na" button, recap counts | n/a (add-ons cut) | Viviene (frontend pair: Ayen + Viviene) |
| **Behind the scenes** | M1 MacBook Air (8 GB) (~1440×900) | Judges / presenters | `/backstage` | Per-utterance proof ([below](#backstage-proof)): transcript → rule or model → action, confidence, reason → ms; a dropped row; `TV lines ignored: N`; T5 badge; OFFLINE badge; health light; hidden "listen now" and typed-question box | n/a (add-ons cut: no face match panel, no CCTV view, no voice match panel) | Viviene |
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

What `brain/decide.py` does today: the TV-word rule (`TV_PHRASES` and `TV_TOKENS`: "thank you for watching", "salamat sa panonood", abangan, kabanata, palabas, teleserye, dula, bes) returns `silent` with `ignored` `tv` and `source` `rule`. The model path never sets `ignored`: a model `silent` comes back with `ignored` `""`. So the demo clip in [demo.md](demo.md), a long dialogue the TV-word rule may not catch, only ticks this counter if its words hit the rule. **TODO (Troy): decide whether a model `silent` should set `ignored` `tv`, or add the clip's words to the rule, before the TV beat is rehearsed.**

## Models and runtimes (all on the M1 (8 GB) hub, all local)

| Job | Model | Runtime | Notes |
|---|---|---|---|
| Voice activity detection | Silero VAD | hub | Starts capture only when someone speaks |
| Speech to text | Whisper small (default); medium only as the fallback below | whisper.cpp (`-l tl`) | See the selection rule below |
| Decision for unclear lines | Qwen2.5-3B (`qwen2.5:3b`) (default); Qwen2.5-1.5B (`qwen2.5:1.5b`) only with the medium fallback | Ollama | Must return JSON matching the decision interface. No AI phrasing for the recap |
| Add-on a: face match | n/a | n/a | **Cut, Sat 2:00 AM. Next step** ([features.md](features.md#cut-tonight-moved-to-next-steps)) |
| Add-on b: person detection | n/a | n/a | **Cut, Sat 2:00 AM. Next step** |
| Add-on c: speaker match | n/a | n/a | **Cut. Not built** ([mvp-plan.md](mvp-plan.md)) |

No text-to-speech or voice-cloning model is used anywhere: Lola only hears the family's own recordings (safety rule in [README.md](README.md#safety-rules)). All add-ons are cut for tonight, and there is no live call. "Sino ka?" is a seeded known question: the iPad shows the registered person's photo and plays the line they recorded ([features.md](features.md#cut-tonight-moved-to-next-steps)).

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
   - `alert`: `{"event":"alert","transcript":""}` to `/caregiver` on urgent. The red card shows `transcript` and is the only card that plays a sound. The hub chime is separate, from the hub speaker.
   - `ask_caregiver`: `{"event":"ask_caregiver","transcript":"","count":1}` to `/caregiver` when the action is caregiver. Quiet. Repeats of the same `transcript` share one yellow card, and `count` is how many times. One tap records a reply through `POST /questions`.
   - `meal_logged`: `{"event":"meal_logged"}`. No extra fields. This is the Should meals check, after the 3:30 AM freeze. Clients ignore it until then. The name means the caregiver tapped "Kumain na".
   - `health`: `{"event":"health","whisper":true,"ollama":true,"server":true,"mic":true,"offline":true}`. `whisper`, `ollama`, `server`, and `mic` are the health light. `true` means that part is up. `offline` true means the OFFLINE badge is showing. Sent when a client connects and again when a part changes.
3. **Questions file:** `{id, question, phrasings[], reply_audio, photo, speaker}`. Troy's seed file is `brain/seed.json`. Donita's loader (D5) reads it, and quick setup appends to the same list.
   - `GET /questions` returns the array.
   - `POST /questions` accepts one object. `reply_audio` and `photo` are file parts (hold to record, and the photo). The hub stores the files and returns the stored object. The hub sets `id` when the client omits it. If `id` already exists, the hub replaces `reply_audio` and `photo` and keeps the question. That is the caregiver's one-tap record-a-reply.
4. **`POST /listen`:** returns 202 and no body. What happened arrives on `/ws`.
   - Listen now: `{"mode":"listen_now"}`. The hub captures from its own mic and runs VAD, Whisper, the junk filter, and `decide()`.
   - Typed question: `{"mode":"typed","text":""}`. Skips VAD, Whisper, and the junk filter. Emits `heard` with that `text` as `transcript` and `dropped` false, then `decided`.
5. **Folders:** `brain/`, `hub/`, `web/setup`, `web/caregiver`. Only `brain/` has code on `main` so far. Which folders hold `/lola` and `/backstage` is TODO: unknown (frontend pair to decide).

**Contract gap (TODO: Troy + Donita):** Ask Sino about Lola (T7, Should) has code in `brain/ask.py`, which returns `{"intent","answer","source","latency_ms"}`, but no WebSocket event or HTTP route carries the caregiver's question or the answer yet. Add one additive event or route before wiring it after the freeze, and post it in the team chat.

**Running the brain without the hub:** `SINO_MODEL=stub` (the default) never opens a socket; lines the rules and matcher miss go to the caregiver. `SINO_MODEL=ollama` posts to `{HUB_URL}/api/generate` with `qwen2.5:3b` (`HUB_URL` defaults to `http://localhost:11434`), 4 s timeout. Text test: `SINO_MODEL=stub python3 brain/tests/run_t5.py`; Ask about Lola cases: `cd brain && python3 ask.py`.

Changing an interface needs a post in the team chat, because every screen depends on it.

## Data flow

1. The hub mic hears speech; Silero VAD cuts the clip. (Or: "listen now" on backstage forces a capture; the typed-question box skips steps 1 to 3.)
2. whisper.cpp transcribes it on the hub → `heard` event.
3. Junk-line filter: quiet clips, likely-no-speech clips, and known junk lines are dropped. Backstage shows them as `heard` with `dropped` true. They never reach Lola or the caregiver.
4. Throttle: one model call at a time. Stale clips are discarded and emit no event.
5. `decide()`: urgent-word rules → "sakit ng loob" idiom (caregiver) → medication (caregiver) → TV words (silent, `ignored` `tv`) → known-question matcher → Qwen only if still unclear → `decided` event.
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
- No face or voice samples are collected: the face and voice add-ons are cut. Family recordings and photos for replies stay on the hub.
- No cloned or synthetic family voices, ever.
- Not a medical device, not a diagnosis. It always escalates to a human.

## To verify at smoke test

None of these are facts yet. Log real results in `docs/NOTES.md` (Model smoke test) and update this list.

| Item | Expectation | Status |
|---|---|---|
| Speech-to-reply latency, known question | about 2 s | to verify at smoke test |
| Speech-to-reply latency, model decides | about 4 to 5 s | to verify at smoke test |
| Whisper small on a 4 s Tagalog clip (medium only if small is unusable) | small's transcript usable | to verify |
| Transcript quality on Taglish speech | usable for the matcher | to verify at smoke test |
| `qwen2.5:3b` / `1.5b` JSON validity and time | valid JSON every time | to verify at smoke test |
| Hub RAM | 8 GB (M1) | confirmed by Donita, Sat 1:20 AM |
| Offline network (rung 1: iPhone hotspot + firewall) | iPad and iPhone reach the hub over HTTPS | to verify |
| LAN-only firewall | outbound check fails, LAN still works | to verify (untested as of Sat 2:00 AM) |
| T5 in `ollama` mode on the hub | gate in [mvp-plan.md](mvp-plan.md#passfail-gate-t5-before-the-330-am-freeze) | waiting on the hub. Stub-mode text results only so far ([../NOTES.md](../NOTES.md#passfail-gate-t5)) |
| Junk-line filter | drops TV sign-offs and silence, keeps real questions | to verify at smoke test |
| Hub chime audible across a room | yes | to verify at smoke test |
| Hub cold start with `start.sh` | under 2 min with seed loaded | to verify at smoke test |
| Hub on battery through the demo | needed only if we show it unplugged | to verify at smoke test |
| Add-ons (a) face match and (b) person detector | n/a | cut Sat 2:00 AM, not built |
| Add-on (c) voice ID | cut, not built | not measured |
