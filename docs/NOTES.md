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

### Model smoke test (fill after idea lock)

| Model + runtime | Device (airplane mode) | Inputs | Correct | Speed | Pass? |
|---|---|---|---|---|---|
| | | /5 | | | |

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
| Sat Oct 10 2:00 AM | **Hub and models (locked).** Hub = Donita's MacBook Air M1 (8 GB). Whisper small + qwen2.5:3b; Whisper medium + qwen2.5:1.5b only if small's Tagalog is unusable. Network: Troy's iPhone 15 hotspot + LAN-only `pf` firewall on the hub. Internet Sharing failed; no Android. Hub not up yet; firewall untested | Troy |
| Sat Oct 10 2:00 AM | **Pairs changed (at 1:51 AM).** Troy + Donita on the backend (hub + brain), Ayen + Viviene on the frontend (`/lola`, `/setup`, `/caregiver`, `/backstage`). The cross-pair sleep shifts in `docs/01-team.md` are TODO: re-decide | Troy |
| Sat Oct 10 2:00 AM | **Recorded family voices are the core reply** for every known question. No text-to-speech, no cloning. Still to record (TODO): Joy's four replies and Troy's "Sino ka?" line | Troy |
| Sat Oct 10 2:00 AM | **Live call cut** from tonight's build. Next step: calling a registered person on the house Wi-Fi (WebRTC). "Sino ka?" = the iPad shows the registered person's photo and plays their recorded line; on stage Troy then talks to "Lola" in person. Replaces the 12:57 AM "live call instead of the recording" change | Troy |
| Sat Oct 10 2:00 AM | **MVP freeze moved from 2:00 AM to 3:30 AM.** Core to protect: hub hears, transcribes, `decide()`; known question gets the recorded voice + photo on the iPad; urgent gets the hub chime + red card; TV silent and `/backstage` shows decisions; quick setup with "Nasaan yung aso?" live. After the freeze: T7 Ask Sino about Lola (code already in `brain/ask.py`), meals, recap counts. Cut now: T6 face match and add-on (b) CCTV (next steps; "Nasaan si Lola?" answers "no camera answer"). Voice ID already cut. 5 AM add-ons cut-off: n/a. 7 AM rehearse and 8:30 AM submit unchanged. See `docs/sino/mvp-plan.md` | Troy |
| Sat Oct 10 2:00 AM | **Status.** PRs #10 (triage hardening), #11 (T7 `ask.py`), #12 (T5 runner) merged. Stub-mode text run on Troy's Mac: urgent 34/34, comfort 37/37, TV false triggers 0, new 11/11, ask 9/9. Latency TODO (hub). Hub not up yet; firewall untested. Details under Pass/fail gate (T5) | Troy |

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
