# Sino: MVP plan, sprints, and task graph

This is the **2:00 AM Sat plan (rev 3)**. It keeps the 10:30 PM Fri sprint plan (rev 2) and applies Troy's 2:00 AM decisions: pairs changed at 1:51 AM, the MVP freeze moves to **3:30 AM**, and face match (T6, A4), the CCTV add-on (D7, V5), voice ID (D8), and the live call are cut. Decision log: [../NOTES.md](../NOTES.md#decision-log). Scope: [features.md](features.md). Team-wide deadlines: [../00-event.md](../00-event.md) and [../01-team.md](../01-team.md).

Time estimates are rough and not benchmarked: **MVP ≈ 3.5 h of parallel work** (about 13 person-hours). There are no add-ons left after the freeze, only Should items.

## Owners

Pairs since 1:51 AM Sat: **Troy + Donita on the backend** (hub + brain), **Ayen + Viviene on the frontend** (`/lola`, `/setup`, `/caregiver`, `/backstage`).

| Who | Part | Owns |
|---|---|---|
| **Troy** (backend pair) | Backend: decision engine | `decide()`: matcher, urgent rules, Qwen prompt and JSON, silent rule, medication logic, seed replies, 30-clip test; his "Sino ka?" recording; after the 3:30 AM freeze, T7 wiring (`answer_about_lola` is already in `brain/ask.py`) and meals logic (T4m). T6 face match is cut |
| **Donita** (backend pair) | Backend: M1 (8 GB) hub | Network + firewall test, HTTPS, Whisper + model timing, Ollama, VAD, junk-line filter, throttle, `/listen` + WebSocket events, storage, `start.sh` + health light, urgent chime. D7 CCTV detector and D8 voice ID are cut |
| **Ayen** (frontend pair) | Frontend: setup + Lola | Design system, Lola's iPad screen, quick setup (the onboarding), recording and photo upload. A4 (the face-match frame) is cut |
| **Viviene** (frontend pair) | Frontend: caregiver + judges | Fake event feed, caregiver iPhone app, behind-the-scenes screen (incl. "listen now" and typed question), Should items after the freeze (Kumain na, recap counts, Ask Sino about Lola on `/caregiver`). V5 is cut |

**Working rules:** each person keeps their own folder and branch (`brain/`, `hub/`, `web/setup`, `web/caregiver`), with small merges to main. Frontends build against the fake feed, so nobody waits. Only interface changes ([architecture.md](architecture.md#the-3-interfaces-locked-in-the-first-15-minutes)) get posted in the team chat.

## Timeline (Fri Oct 9 to Sat Oct 10, PH time)

| By | Done |
|---|---|
| 10:45 PM | Interfaces locked (I0). Done |
| **11:15 PM** | **Network checkpoint: path chosen late, 1:20 AM.** Internet Sharing failed (needs an upstream). Primary: iPhone 15 hotspot + LAN-only `pf` firewall on the hub; backups: spare router/pocket Wi-Fi with no WAN → iPhone USB + Internet Sharing + firewall → venue Wi-Fi + firewall ([architecture.md](architecture.md#network)). mkcert cert for the hub IP. **Passed Sat 2:00 AM for the iPad** on Donita's iPhone hotspot after a firewall rule fix (PR #14); caregiver iPhone not tested yet |
| **11:30 PM** | **Speech model picked:** 8 GB hub → Whisper small + qwen2.5:3b; medium + qwen2.5:1.5b only if small's Tagalog is unusable (timed on a 4 s clip); RAM rule applied ([architecture.md](architecture.md#speech-model-selection-by-1130-pm)). Timings logged in NOTES (PR #14): Whisper small 0.76 s warm but misheard 1 clip, medium right on that clip in 2.27 s; `qwen2.5:3b` 62/62 valid JSON with `format: "json"`. Small vs medium not decided yet: the 32 clips (PR #18) are being run on the hub |
| 12:30 AM | End to end: hub mic → iPad plays a reply. **Missed: the hub is not up yet (2:00 AM).** Now due before the 3:30 AM freeze |
| **1:00 AM** | `start.sh` + health light work, so anyone can restart the hub. **Missed (hub not up).** The 1:00 AM sleep handoff did not happen: sleep shifts are TODO: re-decide ([../01-team.md](../01-team.md#sleep-shifts-cross-pair)) |
| 1:15 AM | Decision model wired, caregiver alerts and urgent chime working. Decision code done in stub mode (PRs #10–#12); hub side missed, now due before 3:30 AM |
| 1:45 AM | 30-clip test passes (or fall back to rules + matcher); quick setup works on the real hub. Stub-mode text run done (see the gate below); hub run waiting on the hub |
| **2:00 AM** | Decisions (Troy): freeze moved to 3:30 AM, pairs changed, live call cut, T6 face match and add-on (b) CCTV cut ([../NOTES.md](../NOTES.md#decision-log)) |
| **3:30 AM** | **MVP freeze (F1).** Core protected until then: the hub hears, transcribes, and runs `decide()`; a known question gets the recorded voice + photo on the iPad; urgent gets the hub chime + red card; TV stays silent and `/backstage` shows decisions; quick setup works live with "Nasaan yung aso?". Then Should: T7 Ask Sino about Lola wiring (code already merged), meals (T4m), recap counts (V4) |
| 5:00 AM | Add-ons cut-off (C1): **n/a**, no add-ons are left |
| 7:00 AM | Team feature freeze. 3 timed rehearsals with no internet + backup video. 7 to 8 AM: rehearse only |
| 8:00 AM | Repo public |
| **8:30 AM** | **Submit** (official hard deadline 10:00 AM, no extensions) |
| 12:00 PM | On-site at Cyberzone, SM Makati |

## Pass/fail gate (T5, before the 3:30 AM freeze)

30 labeled clips. Pass = **urgent 10/10**, **comfort ≥ 8/10**, **0 false triggers on TV clips**, **known questions ≤ 3 s** speech to reply (model-path latency logged; expected 4 to 5 s, to verify). If it fails, ship rules + matcher and use the model only for the caregiver path. The gate is met only by a run on the hub in `ollama` mode with audio; the exact time of that run is TODO (it must land before the 3:30 AM freeze).

Write the run to `docs/NOTES.md` and show it on `/backstage`. Until a real hub run is logged, the hub figures stay TODO. Do not fill these in early.

| Field | Stub mode, text only (Troy's Mac, Sat ~2:00 AM, `brain/tests/run_t5.py`) | Hub, `ollama` mode |
|---|---|---|
| urgent | 34/34 | TODO |
| comfort | 37/37 | TODO |
| TV false triggers | 0 | TODO |
| new questions | 11/11 | TODO |
| speech-to-reply latency | TODO: unknown (no audio) | TODO |
| mode | `stub` | `ollama` |

The stub run checks the rules and the matcher only: `SINO_MODEL=stub` never calls the model, so lines the rules and matcher miss go to the caregiver. It is **not a pass**; the runner prints `PENDING (latency TODO: unknown)`. `cases.json` has 96 text rows (34 urgent, 37 comfort, 8 TV, 11 new, 6 "sakit ng loob"), not 30 audio clips.

`/backstage` shows a small badge. The badge text is `Test: passed <time of the logged run>` only after `docs/NOTES.md` records a hub pass. Until then the badge shows the TODO figures and does not say passed. A stub run never turns it on.

TODO (Troy): fix the 30-clip audio mix (how many urgent / comfort / TV / new-question clips).

## Sprints per person

Each sprint ends with something demoable. If you finish early, pull the next sprint or help the person behind. Times before 2:00 AM are the rev 2 plan; anything marked missed is now due before the 3:30 AM freeze.

### Troy: decision engine

**T7 `answer_about_lola(question, log)`** is Should, after the 3:30 AM freeze. The code is already merged (`brain/ask.py`, PR #11, 9/9 cases in stub mode); the hub side is wired too (PR #16 added the `ask_about_lola` / `about_lola` socket events, named as contract gaps in [architecture.md](architecture.md#the-3-interfaces-locked-in-the-first-15-minutes)); what is left is the `/caregiver` UI. The intent is one of `how`, `saying`, or `where`. The rules run first. Qwen only picks the intent, and it returns JSON only. Code builds the answer from the log: counts, her exact words, and the last urgent. `where` returns the no-camera answer, because add-on (b) is cut. Never a diagnosis or a mood.

| Sprint | Time | Deliver | Done when |
|---|---|---|---|
| S1 | 10:30–11:15 | I0 interfaces + T1 matcher + urgent rules | `decide("Si Mama asan?")` = comfort, `"masakit dibdib"` = urgent. **Done** (PR #2) |
| S2 | 11:15–12:15 | T2 seed questions + replies (incl. "Nasaan si Nanay?" and "Nasaan si Joy?") + 30 test clips (with the team) | Text done (PR #6, 5 questions). **Audio test clips done:** 32 synthetic Lola clips + manifest in `brain/tests/audio/lola/` (PR #18). Recordings TODO: Joy's four replies + Troy's "Sino ka?" line. Real-voice clips: TODO |
| S3 | 12:15–1:15 | T3 Qwen JSON decision + silent rule, T4 medication | **Done in stub mode** (PR #10): unclear lines go to caregiver; silent only at model confidence ≥ 0.8; medication never answered. `ollama` mode waits on the hub |
| S4 | 1:15–2:00 | T5 pass/fail test, tune thresholds | **Runner done** (PR #12), stub results in the gate above. Audio mode for the runner: not on GitHub yet (3:00 AM). Hub `ollama` run with audio not logged yet; due before 3:30 AM |
| S5 | 2:00–3:30 | With Donita: get the hub up, run T5 on the hub, wire `decide()` to the WebSocket; record "Sino ka?" | `decide()` → WebSocket **done** (PR #16: `POST /listen`, `/ws` per screen (lola, caregiver, backstage), `GET /health`, 13/13 tests in stub). Still to do: T5 on the hub, "Sino ka?" recording. Core above works on the hub by the freeze |
| S6 | after 3:30 | Should: T7 wiring and meals logic (T4m) | Socket side done in PR #16 (`ask_about_lola` → `about_lola`); the `/caregiver` UI is left. `answer_about_lola("Kamusta si Lola?")` returns log counts on `/caregiver`; `answer_about_lola("Nasaan si Lola?")` returns the no-camera answer; "Kumain na ba ako?" answers from the log |
| Cut | | T6 face match | Next step |
| Sleep | TODO: re-decide | | |

### Donita: M1 (8 GB) hub

| Sprint | Time | Deliver | Done when |
|---|---|---|---|
| S1 | 10:30–11:15 (D1 path chosen late, 1:20 AM) | D1 iPhone hotspot + LAN-only firewall + mkcert HTTPS ([DONITA-SETUP.md](DONITA-SETUP.md#5-network-d1)), D3 Ollama warm | iPad + iPhone open the https page; `curl -m 3 https://google.com` fails on the hub; ping to the iPad works. **D1 passed Sat 2:00 AM for the iPad** (hub `172.20.10.2`, firewall rule fixed, PR #14); caregiver iPhone not tested yet. **D3 done** 12:43 AM: `qwen2.5:3b` kept loaded, 62/62 valid JSON with `format: "json"` |
| S2 | 11:15–12:15 | D2 Whisper + model timing (by 11:30), D4 VAD → junk filter → throttle → /listen → WebSocket, D5 seed loader + storage | Speaking near the hub shows the transcript on backstage; TV sign-off lines are dropped; seed loader done (A3 needs it). In progress (3:00 AM): D2 timed (small 0.76 s but misheard 1 clip; medium right on it, 2.27 s), the 32 clips are being run; `/listen` + WebSocket + seed served by `GET /questions` + JSONL log came in PR #16; VAD, junk filter, throttle, and `POST /questions` are not in the repo yet |
| S3 | 12:15–1:00 | D6 `start.sh` + health light + urgent chime | Anyone can restart the hub; the chime test in [hub-chime.md](hub-chime.md) passes. In progress: the server sends the `alert` event (PR #16); `start.sh`, health light, and chime code are not in the repo yet (3:00 AM) |
| S4 | 2:00–3:30 | With Troy: finish D1–D6 so the core runs on the hub by the freeze | Core above works on the hub |
| Cut | | D7 CCTV detector, D8 voice ID | Next steps |
| Sleep | TODO: re-decide | | Hub left running; handoff note in `docs/NOTES.md` |
| S5 | 6:30–8:30 | Rehearse, README disclosures, submit | Submitted |

### Ayen: setup + Lola's screen

| Sprint | Time | Deliver | Done when |
|---|---|---|---|
| S1 | 10:30–11:15 | A1 design system (tokens, components) | Shared Tailwind theme pushed. In progress: the look spec is merged ([design-system.md](design-system.md), PR #15, owner Viviene); theme code not in the repo yet (3:00 AM) |
| S2 | 11:15–12:15 | A2 Lola iPad screen: big clock, idle photo, full-screen reply | Plays a reply from the fake feed. Not in the repo yet (3:00 AM) |
| S3 | 12:15–1:45 | A3 quick setup: add question, two phrasings, hold to record, photo, test | A new question added on the iPhone is answered on the iPad. Not in the repo yet (3:00 AM) |
| S4 | before 3:30 | With Viviene: check A2 + A3 on the real devices against the hub | Freeze-ready |
| Cut | | A4 face-match frame | Next step. "Sino ka?" is a normal reply on A2: photo + recorded line |
| Sleep | TODO: re-decide | | |
| S6 | 7:00–8:30 | Rehearse, demo video visuals | Video exported |

### Viviene: caregiver + backstage

| Sprint | Time | Deliver | Done when |
|---|---|---|---|
| S1 | 10:30–11:00 | V1 fake event feed | All screens can build against it. Not in the repo yet (3:00 AM; PR #4 added only an empty `packages/ui`). Stand-in: `brain/server.py` in stub mode + `brain/tests/fake_hub.py` (PR #16) |
| S2 | 11:00–12:15 | V2 caregiver phone: red card with sound, quiet yellow with grouped repeats + record-a-reply, green log | Works on the iPhone with the fake feed. Not in the repo yet (3:00 AM) |
| S3 | 12:15–1:00 | V3 backstage: transcript → rule or model → action, confidence, reason, ms; dropped row; `TV lines ignored: N`; T5 badge; OFFLINE; health light; "listen now"; typed question | Updates live from the real hub ([architecture.md](architecture.md#backstage-proof)). Not in the repo yet (3:00 AM) |
| S4 | after 3:30 | V4 Should: Kumain na + recap counts; Ask Sino about Lola on `/caregiver` (with Troy's T7 wiring) | Recap shows real counts |
| Cut | | V5 "Nasaan si Lola?" CCTV view | Next step |
| Sleep | TODO: re-decide | | Handoff note in `docs/NOTES.md` |
| S5 | 6:30–8:30 | Pitch visuals, submission post graphic, rehearse | Post ready |

**Sync points (5 min each):** 11:15 PM (interfaces + network), 11:30 PM (speech model), 1:00 AM (MVP wired + restart works; missed), 2:00 AM (rev 3 decisions), 3:30 AM (freeze, F1), 7:00 AM (rehearse). Other sync times: TODO: re-decide with the sleep shifts.

Sleep shifts: the cross-pair shifts in [../01-team.md](../01-team.md) (Donita + Viviene 1:00–4:30 AM, Troy + Ayen 4:30–7:00 AM) were built on the old pairing and the 1:00 AM handoff did not happen. **TODO: re-decide.**

## Task graph

Arrows show what needs what. Cut tasks (T6, A4, D7, V5, D8) are drawn, marked cut, and do not start. Tasks with no incoming arrow can start right away.

**Start immediately (no prerequisites):** T1, T2, D1, D3, A1, V1.

**Status as of ~3:00 AM Sat. Hub: MacBook Air M1 8 GB.** Colours: Done / In progress / Waiting on hub / Not started / Cut (legend in the image). Done: I0, T1, T2 (text + 32 synthetic Lola audio clips, PR #18; recordings TODO), T4, T3 and T5 in stub mode (PRs #10 and #12; `ollama` mode not run on the hub yet), T7 (`brain/ask.py`, PR #11, and its socket events, PR #16; `/caregiver` UI after the freeze), D1 (passed for the iPad at 2:00 AM after the firewall fix, PR #14; caregiver iPhone untested), D3 (Ollama `qwen2.5:3b` kept loaded, 62/62 valid JSON), the `decide()` → WebSocket wiring (PR #16), the spec docs. In progress: D2 (Whisper small timed but misheard 1 clip; medium right on it; 32 clips being run), D4 and D5 (`/listen`, `/ws`, `GET /questions`, and the JSONL log are in PR #16; VAD, junk filter, throttle, and `POST /questions` are not), D6 (`alert` event exists; no `start.sh`, health light, or chime code in the repo yet), A1 (design-system.md merged, PR #15; no theme code). Waiting on hub: W1 (needs the mic path and the screens), T5 in `ollama` mode with audio. Not started in the repo: A2, A3, V1 to V4 (PR #4 added only an empty `packages/ui`). Cut: T6, A4, D7, V5, D8.

![Sino task graph](task-graph.png)

Source: [task-graph.mmd](task-graph.mmd) (Mermaid, renders on GitHub):

```mermaid
flowchart TD
  I0[I0 Lock 3 interfaces · 15 min · all<br/>✓ done: wire contracts in architecture.md]

  subgraph Backend["Backend pair · Troy + Donita"]
    subgraph Troy["Troy · decision engine"]
      T1[T1 Matcher + urgent rules<br/>✓ decide.py · PR #2, hardened PR #10]
      T2[T2 Seed replies + 30 test clips<br/>✓ text PR #6 · 32 synthetic Lola clips PR #18<br/>recordings TODO: Joy ×4 + Sino ka?]
      T3[T3 Qwen JSON decision + silent rule<br/>✓ done in stub · PR #10 · ollama run on hub not logged]
      T4[T4 Medication<br/>✓ routes to caregiver, tests in cases.json]
      T5[T5 30-clip pass/fail test<br/>✓ stub runner · PR #12 · hub audio run not logged]
      T7[T7 Ask Sino about Lola · after 3:30 AM<br/>✓ ask.py PR #11 · socket events PR #16 · /caregiver UI left]
      T4m[Meals logic · after 3:30 AM]
      T6[T6 a: Face match<br/>cut · next step]
    end
    subgraph Donita["Donita · M1 (8 GB) hub"]
      D1[D1 iPhone hotspot + LAN firewall + HTTPS<br/>✓ passed for iPad 2:00 AM · PR #14 · caregiver iPhone untested]
      D2[D2 Whisper small server + timing<br/>small 0.76 s but misheard 1 clip · medium right · 32 clips running]
      D3[D3 Ollama qwen2.5:3b loaded + warm<br/>✓ kept loaded · 62/62 valid JSON · PR #14]
      D4[D4 VAD → junk filter → throttle → WebSocket<br/>/listen + /ws in PR #16 · VAD, filter, throttle not in repo]
      D5[D5 Seed loader + storage<br/>GET /questions + JSONL log in PR #16 · POST /questions not in repo]
      D6[D6 start.sh + health light + urgent chime<br/>alert event in PR #16 · start.sh + chime not in repo]
      D7[D7 b: CCTV detector<br/>cut · next step]
      D8[D8 c: Voice ID<br/>cut]
    end
  end
  subgraph Frontend["Frontend pair · Ayen + Viviene"]
    subgraph Ayen["Ayen · setup + Lola screen"]
      A1[A1 Design system<br/>spec merged PR #15 · theme code not in repo]
      A2[A2 Lola iPad: clock, photo, recorded reply<br/>not started in repo]
      A3[A3 Quick setup: question, phrasings, record, photo, test<br/>not started in repo]
      A4[A4 a: Face-match frame<br/>cut · next step]
    end
    subgraph Viv["Viviene · caregiver + backstage"]
      V1[V1 Fake event feed<br/>not in repo · stub server + fake_hub.py can stand in]
      V2[V2 Caregiver iPhone: red, quiet yellow, log<br/>not started in repo]
      V3[V3 Backstage + listen now + typed question<br/>not started in repo]
      V4[V4 Should: Kumain na + recap counts · after 3:30 AM<br/>not started in repo]
      V5[V5 b: 'Nasaan si Lola?' CCTV view<br/>cut · next step]
    end
  end
  subgraph Legend["Status as of ~3:00 AM Sat"]
    L1[Done]
    L2[In progress]
    L3[Waiting on hub]
    L4[Not started]
    L5[Cut]
  end

  I0 --> T1 & D4 & D5 & V1
  T1 --> T3 --> T5
  T1 --> T4
  T2 --> T5
  D3 --> T3
  D1 --> D2 --> D4 --> D6
  A1 --> A2 & A3 & V2 & V3
  V1 --> A2 & V2 & V3
  D5 --> A3
  D4 & D5 & D6 & T3 & A2 & V2 & V3 --> W[W1 MVP wired on the hub · before 3:30 AM<br/>server glue PR #16 · mic path + screens missing]
  W --> T5 --> F[F1 MVP freeze · 3:30 AM<br/>moved from 2 AM]
  T4 & A3 --> F
  F --> T7 & T4m
  T4m --> V4
  T7 & V4 --> R[R1 Rehearse ×3 + backup video · 7 AM]
  C[C1 Add-ons cut-off · 5 AM<br/>n/a: no add-ons left]
  F -.-> C
  R --> S[S1 Submit · 8:30 AM]

  classDef done fill:#dcfce7,stroke:#15803d,stroke-width:2px,color:#111
  classDef doing fill:#fef3c7,stroke:#b45309,stroke-width:2px,color:#111
  classDef hub fill:#fce7f3,stroke:#be185d,stroke-width:2px,color:#111
  classDef todo fill:#ffffff,stroke:#6b7280,color:#111
  classDef cut fill:#f3f4f6,stroke:#9ca3af,stroke-dasharray:5 5,color:#6b7280
  class I0,T1,T2,T3,T4,T5,T7,D1,D3,L1 done
  class D2,D4,D5,D6,A1,L2 doing
  class W,L3 hub
  class T4m,A2,A3,V1,V2,V3,V4,F,R,S,L4 todo
  class T6,A4,D7,V5,D8,C,L5 cut
```
