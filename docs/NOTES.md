# Working notes

Briefing notes, decisions, and handoff notes go here. Newest at the bottom.

## Links

- Figma file: (add link)
- Cerebral Valley submission page: (from briefing)

## Briefing, Fri Oct 9 12:45 PM to 1 PM (summary; full text in [00-event.md](00-event.md))

### Theme and challenge

- **Theme: Local AI.** "Useful AI experiences where meaningful AI computation happens on the user's device, rather than depending entirely on cloud inference." Not the same as an AI product for a local audience.
- **Challenge:** "Build an AI product that remains genuinely useful when the cloud disappears." Show why local AI makes it difficult, expensive, slow, private, or impossible to do cloud-only. Any product category.

### Judging criteria and weights

Problem & Usefulness 25% · Local AI Implementation 25% · Technical Execution 20% · Innovation 15% · Product & Demo Quality 15%.

### Rules

- Required: substantially built during the hackathon; meaningful AI inference executes locally; working product, demonstrated; models, APIs, frameworks, and major tools disclosed; core Local AI works without depending entirely on a cloud AI API.
- Allowed: existing open-source models and libraries; AI-assisted development; Devin; cloud APIs as secondary components.

### Submission guidelines

- Project: name, short description, team members, public GitHub repo.
- Proof: demo video, X/LinkedIn video URL, what runs locally, what requires internet.
- Disclosures: models, technologies and frameworks, APIs and cloud services, existing code and assets, AI development tools.
- Must answer: "Why does this product benefit from running AI locally?"
- Deadline: 10:00 AM Sat Oct 10, no extensions.

### Side award criteria (Tutorials Dojo, WhiteCloak, Cognition/Devin, AMD, People's Choice)

TBD.

### Anything else announced

- Demo Day: 5-min pitch + live demo, 3-min judge Q&A (8 min per team). Finalists announced Sat Oct 10, 1:00 PM. Working product over many slides.
- Example tools (none required): Ollama, LM Studio, llama.cpp, MLX, ONNX, PyTorch, TensorFlow, WebGPU, Core ML, AMD ROCm, DirectML, Hugging Face.

### Model smoke test (hub: M1 8 GB)

Hub: M1 MacBook Air, 8 GB (MacBookAir10,1), macOS 26.5.1. whisper.cpp built with Metal, `-l tl`. Ollama 0.40.2 (Homebrew formula). Only the Fri offline row ran with Wi-Fi off; the Device column says what was on.

| Model + runtime | Device (airplane mode) | Inputs | Correct | Speed | Pass? |
|---|---|---|---|---|---|
| Whisper small, whisper.cpp | Hub, Wi-Fi on (Sat ~1:35 AM) | `test.wav`: Donita saying "Nasaan si Nanay?", 3.55 s (1 clip, 1 voice) | No: "nasaanzi na nai." (both runs) | run 1: 0.98 s (wall 1.25 s); run 2: 0.76 s (wall 0.87 s) | Speed yes, transcript no. More clips needed |
| Whisper medium, whisper.cpp (fallback only) | Hub, Wi-Fi on (Fri Oct 9 evening) | same `test.wav` | Yes: "Nasaan si nanay." | 2.27 s, including 0.72 s model load | Correct on 1 clip. Fallback only (pairs with `qwen2.5:1.5b`) |
| `qwen2.5:3b`, Ollama, Troy's `build_prompt` (`brain/model.py`), plain | Hub, Wi-Fi on (Sat ~1:30 AM) | 62 lines of `brain/tests/cases.json` (as of PR #6) | 60/62 valid JSON by `parse_model_json`. 2 malformed (`confidence` outside the object) | median 1.51 s, p90 1.79 s, max 2.68 s | No |
| `qwen2.5:3b`, Ollama, same prompt + `format: "json"` | Hub, Wi-Fi on (Sat ~1:30 AM) | same 62 lines | 62/62 valid JSON | median 1.68 s, p90 2.12 s, max 2.88 s | Yes for JSON. Accuracy is T5, not this check |
| `qwen2.5:3b` cold / warm / after idle | Hub, Wi-Fi state not logged (Sat, from 12:43 AM) | single requests | n/a | First after start: 5.56 s (3.89 s of it model load). Second: 1.17 s. After ~35 min idle: 9.00 s (Mac swapping: 8.3 GB swap used, 41% memory free), then 0.24–0.27 s on a tiny prompt | Close other heavy apps. A keep-warm ping may be needed |
| `qwen2.5:3b` on "Masakit ang dibdib ko" | Hub, Wi-Fi state not logged | 5 runs (3 Fri evening, 2 Sat 12:43 AM) | 0/5: `caregiver`, not `urgent` | not logged | No. Urgent words stay hard-coded before the model (`brain/decide.py`) |
| Whisper small + `qwen2.5:3b` offline | Hub, **Wi-Fi off** (Fri Oct 9 evening) | not logged | both ran | not logged | Yes (ran offline) |
| Ollama under the LAN-only firewall | Hub, firewall on, internet blocked (Sat 2:00 AM) | `curl http://127.0.0.1:11434/api/version` | `{"version":"0.40.2"}` | n/a | Yes. Whisper not run under the firewall yet |
| Whisper small, `whisper-server` (D2), `-l tl`, `127.0.0.1:8080`. Model 487.01 MB, server memory 560 MB | Hub, Wi-Fi on (Sat ~2:20 AM). System memory 15% free with Ollama `qwen2.5:3b` also loaded | `test.wav`: Donita saying "Nasaan si Nanay?", 3.55 s (1 clip, 1 voice). Plain request, temperature 0, 3 runs | No: "nasa ang zina na iy." | 0.596 s, 0.505 s, 0.559 s (curl total) | No: wrong transcript |
| same, with hint prompt "Nasaan si Nanay? Nasaan si Joy? Sino ka?" | same | same `test.wav`, 2 runs | Yes: "Nasaan si Nanay?" | run 1: 1.053 s; run 2: 0.540 s (curl total) | Correct on 1 clip, 1 voice. The hint may make TV lines sound like known questions, so T5's TV rows must check it |

Raw outputs of the JSON check are on the hub at `~/sino/d3-json-check.txt` (not in the repo). Troy's `brain/model.py` on main already sends `format: "json"`.

## Decision log

| Time | Decision | Who |
|---|---|---|
| Thu Oct 8 | Planning docs added; no application code until 1 PM Fri | Troy |
| Thu Oct 8 | Designer task split added (Ayen: flow, key frames, tokens, final QA; Viviene: state screens, assets, video, post graphic, pitch visuals). Adjust after 1 PM | Team |
| Thu Oct 8 | Mascot is an optional stretch for Ayen, only if the core works and it serves the UI | Ayen |
| Thu Oct 8 | "Yen" on the participant list is Ayen (confirmed) | Team |
| Thu Oct 8 | Ayen free all day Fri | Ayen |
| Thu Oct 8 | On-site Sat: Troy, Viviene, Ayen (Donita TBD), going even before finalists are named | Team |
| Thu Oct 8 | Prize targets: Grand Champion first, Tutorials Dojo as fallback; side-award criteria copied at briefing | Team |
| Thu Oct 8 | Talk to AI tools in any language; code, commits, and README stay in English | Team |
| Fri Oct 9 1 PM | Official rules folded into docs: Local AI theme, weighted criteria, official submission checklist, airplane-mode tests, model smoke-test gate. Idea not locked yet | Troy |
| Fri Oct 9 | **Idea locked: Sino.** Offline home hub that answers Lola's repeated questions in her family's recorded voice and alerts the caregiver. Hub: Donita's M2 (whisper.cpp + Ollama qwen2.5:3b). Spec in `docs/sino/` | Team |
| Fri Oct 9 10:30 PM | Build plan reset: MVP freeze 2:00 AM, add-ons cut-off 5:00 AM, submit 8:30 AM. See `docs/sino/mvp-plan.md` | Troy |
| Fri Oct 9 10:40 PM | Spec hardened: quick setup is the MVP onboarding (9-step wizard dropped); junk-line filter + throttle + hidden "listen now"; speech model picked by timing at 11:30 PM with a RAM rule; urgent = hub chime + red card (no push offline); quiet grouped yellow cards; recap is counts only; "Nasaan si Nanay?" gets a validation reply; Internet Sharing no-upstream test at 11:15 PM; add-ons a → b → c behind a cut line; why-local leads with the always-on mic | Troy |
| Fri Oct 9 11:20 PM | Interfaces locked for the build: WebSocket payloads, `POST /listen`, `GET`/`POST /questions`, and junk lines riding on `heard`. Shapes are in `docs/sino/architecture.md`. M2 RAM and measured latencies stay to verify | Troy |
| Sat Oct 10 1:20 AM | Hub is an M1 (8 GB), macOS 26.5.1, not an M2. Models: Whisper small + qwen2.5:3b (medium + qwen2.5:1.5b only if small's Tagalog is unusable; medium + 3B and large-v3-turbo out). Internet Sharing failed (needs an active upstream; `bridge100` never appeared); no Android on the team. Network ladder changed (Troy, 1:23 AM): primary iPhone 15 hotspot + hub LAN-only `pf` firewall → spare router/pocket Wi-Fi with no WAN → iPhone USB + Internet Sharing + firewall → venue Wi-Fi + firewall. See `docs/sino/architecture.md#network` | Donita, Troy |
| Sat Oct 10 12:43 AM | D3 done: Ollama 0.40.2 (Homebrew formula, not the app) running on the hub. `qwen2.5:3b` kept loaded (`OLLAMA_KEEP_ALIVE=-1`; `ollama ps`: 2.2 GB, 100% GPU, until Forever), local-only on `127.0.0.1:11434`. Timings in Model smoke test above | Donita |
| Sat Oct 10 | Viviene's hotspot tried first for D1: the Mac got no IPv4 address by DHCP, only `192.0.0.2` (IPv6-only network with 464XLAT). Not usable with the IPv4 firewall | Donita |
| Sat Oct 10 2:00 AM | **Hub and models (locked).** Hub = Donita's MacBook Air M1 (8 GB). Whisper small + qwen2.5:3b; Whisper medium + qwen2.5:1.5b only if small's Tagalog is unusable. Network: Troy's iPhone 15 hotspot + LAN-only `pf` firewall on the hub. Internet Sharing failed; no Android. Hub not up yet; firewall untested | Troy |
| Sat Oct 10 2:00 AM | **Pairs changed (at 1:51 AM).** Troy + Donita on the backend (hub + brain), Ayen + Viviene on the frontend (`/lola`, `/setup`, `/caregiver`, `/backstage`). The cross-pair sleep shifts in `docs/01-team.md` are TODO: re-decide | Troy |
| Sat Oct 10 2:00 AM | **Recorded family voices are the core reply** for every known question. No text-to-speech, no cloning. Still to record (TODO): Joy's four replies and Troy's "Sino ka?" line | Troy |
| Sat Oct 10 2:00 AM | **Live call cut** from tonight's build. Next step: calling a registered person on the house Wi-Fi (WebRTC). "Sino ka?" = the iPad shows the registered person's photo and plays their recorded line; on stage Troy then talks to "Lola" in person. Replaces the 12:57 AM "live call instead of the recording" change | Troy |
| Sat Oct 10 2:00 AM | **MVP freeze moved from 2:00 AM to 3:30 AM.** Core to protect: hub hears, transcribes, `decide()`; known question gets the recorded voice + photo on the iPad; urgent gets the hub chime + red card; TV silent and `/backstage` shows decisions; quick setup with "Nasaan yung aso?" live. After the freeze: T7 Ask Sino about Lola (code already in `brain/ask.py`), meals, recap counts. Cut now: T6 face match and add-on (b) CCTV (next steps; "Nasaan si Lola?" answers "no camera answer"). Voice ID already cut. 5 AM add-ons cut-off: n/a. 7 AM rehearse and 8:30 AM submit unchanged. See `docs/sino/mvp-plan.md` | Troy |
| Sat Oct 10 2:00 AM | **Status.** PRs #10 (triage hardening), #11 (T7 `ask.py`), #12 (T5 runner) merged. Stub-mode text run on Troy's Mac: urgent 34/34, comfort 37/37, TV false triggers 0, new 11/11, ask 9/9. Latency TODO (hub). Hub not up yet; firewall untested. Details under Pass/fail gate (T5) | Troy |
| Sat Oct 10 2:00 AM | D1 passed on Donita's iPhone hotspot (hub `172.20.10.2`, iPad `172.20.10.3`): firewall on → internet blocked (`curl` timed out), Ollama on the hub works, iPad pings, iPad loads `https://172.20.10.2:8443` (a throwaway test page) with no certificate warning. The firewall rules in `docs/sino/DONITA-SETUP.md` were fixed: the original rules (tested 1:55 AM) dropped the hub's replies to the iPad, so its page reload never reached the hub's server. iPhone (caregiver phone) not tested yet | Donita |
| Sat Oct 10 ~3:15 AM | **T6 face match and add-on (b) CCTV un-cut**, as after-freeze add-ons on Troy's path: built only after the 3:30 AM freeze and after T5 passes on the hub. T6: OpenCV YuNet (detect) + SFace (recognise), a few MB, CPU; 3 family members enrolled on the hub (troy, joy, donita); photos gitignored, frames in memory only; "Sino ka?" plays the recognised person's line (seed `sino-ka` gains additive `by_person`), Troy's line if nobody is matched. CCTV is now T8 "CCTV where + door alert" (was D7 + V5): old phones/iPads open `/camera?room=` and send JPEGs to `POST /cctv/frame`; OpenCV HOG person detector; `last_seen` feeds `_where_answer` in `brain/ask.py` ("Nasa sala, N minuto na.") with a caregiver-only in-memory snapshot that expires after 120 s; the `pinto` camera sends a caregiver `alert` with `kind: "door"`, at most 1 per 2 min. Single person assumed for the demo. New additive contract items: `POST /face/frame`, `face_seen`, `decided.who`, `POST /cctv/frame`, `GET /cctv/snapshot`, `cctv_seen`, `alert.kind`. Not built yet; branches in progress: `troy/face-engine`, `troy/face-wire`, `troy/cctv`. Voice ID (D8), the iPad face-match frame (A4), and the live call stay cut. **Superseded at 3:23 AM (next row).** | Troy |
| Sat Oct 10 3:23 AM | **Revised after review: only T6 face match is un-cut.** CCTV ("CCTV where + door alert", D7/V5), the door/wandering alert, voice ID (D8), and the live call stay **cut** (next steps). "Nasaan si Lola?" keeps the no-camera answer from `brain/ask.py`. No "Siri" framing: the pitch stays "family voice, offline". T6 rules: starts only after the core runs end to end on the hub (W1) and T5 passes there, after the 3:30 AM freeze, with a hard stop at 5 AM. One frame on demand: when "Sino ka?" fires, Sino grabs **one** frame (no continuous stream, no polling loop; `POST /face/frame` is called once per trigger). OpenCV YuNet detects and SFace recognises (a few MB, hub CPU) against 3 family members enrolled on the hub (troy, joy, donita). A family member's line plays **only on a high-confidence match**; otherwise Troy's seeded line plays, never the wrong relative. Enrollment photos are gitignored; frames stay in memory only. If the hub starts swapping, fall back to `qwen2.5:1.5b`. Contract (additive, not built): `POST /face/frame`, `face_seen` (backstage), `decided.who`, seed `sino-ka` gains `by_person`. Review credited: **Bototoy** (feasibility and RAM on the 8 GB hub), **Bon** (CCTV dilutes the story and raises consent problems; the Siri framing is a trap), **Satan** (core first; a face misfire on stage is the risk). Replaces the 3:15 AM row | Troy |
| Sat Oct 10 ~3:45 AM | **Urgent is rules-only** (Troy, from Bototoy's review). A model urgent becomes caregiver. The model may stay silent only at confidence ≥ 0.9 and only when the line has no breathing, pain, or fall word. Fixes [sino/hub-problems.md](sino/hub-problems.md) §2. | Troy |
| Sat Oct 10 ~4:15 AM | **Meals check (T4m).** "Kumain na ba ako?" is a seed question (`meal-check`) with a dynamic reply chosen in `server.py`. `decide()` stays stateless. The window is 3 hours (`MEAL_WINDOW_H`). Sino never answers "hindi pa": a missing log means we don't know, not that she didn't eat. The caregiver's tap is the only source. From Bon (dementia care) and Bototoy (architecture). Recordings still TODO: Joy's three meal clips (`ate`, `ate_repeat`, `unknown`). | Troy |
| Sat Oct 10 ~4:30 AM | **Recorded-clip "Nasaan si Lola?" only** (Troy, from Bototoy and Satan). Not live CCTV and not the door alert: those stay cut. Clips on the hub are scanned in advance, not when the question is asked. The answer is past tense ("Huling nakita sa recording: sala (clip 0:42)."), never "she is there now" and never "N minuto na". The caregiver snapshot is labeled "RECORDED CLIP · DEMO". Footage stays on the hub, frames stay in memory, and the snapshot goes to the caregiver only. Hard stop 5:00 AM: if it is not reliable on the demo clips, it returns to the next-steps slide, and it ships only if the core gate is green. | Troy |

## Pass/fail gate (T5)

The gate is met only by a hub run in `ollama` mode, before the 3:30 AM freeze (was 1:45 AM). Do not mark a pass, and do not show a `Test: passed` badge on `/backstage`, until the hub column is filled from a real run. Spec: [sino/mvp-plan.md](sino/mvp-plan.md#passfail-gate-t5-before-the-330-am-freeze).

| Result | Stub mode, text only (Troy's Mac, Sat ~2:00 AM, after PRs #10–#12) | Hub, `ollama` mode |
|---|---|---|
| urgent | 34/34 | TODO |
| comfort | 37/37 | TODO |
| TV false triggers | 0 (8/8 TV rows silent) | TODO |
| new questions | 11/11 | TODO |
| Ask Sino about Lola (`brain/ask.py`) | 9/9 | TODO |
| speech-to-reply latency | TODO: unknown (no audio) | TODO |
| verdict | `PENDING (latency TODO: unknown)`, **not a pass** | TODO |
| mode | `stub` | `ollama` |

Stub mode checks the rules and the matcher only: the model is never called, so lines the rules and matcher miss go to the caregiver. A long TV dialogue that hits no TV word (for example one with "nasaan si nanay" mid-sentence) comes out caregiver in stub mode; only the hub run can show the model keeping it silent. `cases.json` has 96 text rows, not the 30 audio clips the gate names (clip mix TODO, Troy).

## Handoffs

(Use the template in [01-team.md](01-team.md#handoff-note-write-it-in-docsnotesmd-at-100-am-and-430-am).)

- Sat Oct 10, T5 stub run on the `troy/t5-harness` branch before PR #10 was merged (`SINO_MODEL=stub python3 brain/tests/run_t5.py`, text only): mode stub; urgent 11/11; comfort 33/33; TV false triggers 8; model-path rows 15; verdict FAIL on the TV gate. **Superseded:** after PRs #10–#12 merged, the same run on `main` gives urgent 34/34, comfort 37/37, TV false triggers 0, new 11/11 (Pass/fail gate above). Still not a pass; the badge stays off until a real hub run is logged.

### Handoff 4:30 AM Sat, from Donita to the awake shift (TODO: names, sleep shifts not re-decided)

- main status: green. All of Donita's hub PRs are merged: #14 (setup results + firewall fix), #23 (D5 save questions/recordings/photos), #26 (D4 listen now), #31 (D6 `hub/start.sh` + urgent chime). No open PRs as of 4:32 AM.
- Done since last sync:
  - Hub running on Donita's MacBook Air M1 (8 GB), started with `hub/start.sh` (Sat ~4:20 AM). Health light: Whisper, AI model (Ollama `qwen2.5:3b`), hub server, microphone, keep-warm all OK. Offline DOWN, because the firewall was off.
  - Hub URL for the iPad and phone: `https://172.20.10.2:8000`. Logs in `~/sino/logs/`, PID files in `~/sino/run/`.
  - Restart (anyone, from the repo root on the hub): `hub/start.sh` starts only what isn't running and prints the light; `hub/start.sh status` prints the light only; `hub/start.sh stop` stops only what `start.sh` started. Cold start 13 s, stop + start 5 s. No Ctrl+C while it is still starting: that stops the parts it just started.
  - Network: Donita's iPhone Personal Hotspot, not Troy's (the doc's primary, `docs/sino/architecture.md#network`; team call). Mac `172.20.10.2`, iPad `172.20.10.3`. Keep the iPhone on the Personal Hotspot screen.
  - If the Mac's IP changes: `mkcert -cert-file ~/sino/certs/hub.pem -key-file ~/sino/certs/hub-key.pem <new-ip> localhost`, then `hub/start.sh stop && hub/start.sh`. `start.sh` warns when the cert doesn't match.
  - Firewall (LAN-only, blocks internet): on `sudo pfctl -f /etc/pf.sino.conf -e`, off `sudo pfctl -d` (needs the Mac password; turn it off before downloading anything). Rules fixed and tested Sat 2:00 AM (`docs/sino/DONITA-SETUP.md` §5). Must be ON for rehearsals and the demo; the Offline light turns OK only then.
  - Passed on the hub: iPad Safari loads the hub URL with no certificate warning, plays saved `.m4a` and `.wav` replies, shows photos; a re-recorded reply plays the new file.
  - Real mic, listen now: silence dropped (`likely no speech`). "Nasaan si Nanay?" heard as "nasa ang sinanay." but matched → comfort (confidence 0.903). "Thank you for watching" dropped (`junk line`).
  - Typed "Masakit dibdib ko" → urgent: `/caregiver` got `alert`, `/lola` got no `alert`, hub played the chime (Glass 5× back to back, ~8.25 s; Donita approved).
- In progress (branch, what's left): none from Donita; no open PRs as of 4:32 AM.
- Known bugs (priority order):
  1. Always-listening (Silero VAD, `docs/sino/features.md` M1) is NOT built. Only "listen now" (fixed 4.5 s clip) and typed questions exist. Past the 3:30 AM freeze: Troy decides build or cut.
  2. Whisper small mishears Tagalog (Donita's clip: "nasaanzi na nai.", "nasa ang zina na iy."); the matcher's fuzzy match saved the live test. A hint prompt of the known questions fixed the clip (`WHISPER_HINT=1`, off by default) but may make TV lines sound like known questions. Needs Troy's T5 TV clips before turning it on.
  3. `/lola` receives `decided` for urgent lines (the server sends comfort/caregiver/urgent `decided` to every screen). The Lola screen must ignore `decided` so it never shows red (`docs/sino/hub-chime.md`). Owner: Ayen.
  4. Caregiver iPhone not yet tested opening the hub page on the hotspot (its cert is trusted).
  5. 8 GB memory is tight: 15% free with Whisper + Qwen loaded (~2:20 AM); Qwen took 9.00 s after ~35 min idle, before keep-warm existed. Close other apps on the hub during rehearsals.
  6. Upload filenames: the setup screen must send files with a name (e.g. `reply.m4a`), or the hub rejects them (400).
  7. T5 not yet run on the hub in `ollama` mode with audio. Only stub/text so far: urgent 40/40, comfort 39/39, TV false triggers 0, new 19/19.
- Do NOT touch:
  - The running hub processes: use `hub/start.sh stop`, never kill or Ctrl+C.
  - `/etc/pf.sino.conf`, `/etc/pf.anchors/sino`, and `~/sino/certs/`.
  - `hub/data/` on the hub: the live questions list and family recordings (not in git).
- Next 3 tasks for the awake shift:
  1. Troy: run T5 on the hub in `ollama` mode (and with the synthetic Lola audio), fill the hub column in the Pass/fail gate above; decide always-listening and `WHISPER_HINT`.
  2. Ayen + Viviene: point the real screens at `https://172.20.10.2:8000` (`/ws?screen=lola|caregiver|backstage`, `POST /listen`, `GET/POST /questions`, `/media/...`); test the caregiver iPhone on the hotspot.
  3. Rehearse with the firewall ON (`sudo pfctl -f /etc/pf.sino.conf -e`) and the hub volume up for the chime.
- Wake us if (Donita): `hub/start.sh` shows a part DOWN that a stop + start doesn't fix; the hotspot, network, or certificate breaks; the firewall blocks the iPad.
