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

## Pass/fail gate (T5)

Filled from a real 1:45 AM run. Until then every figure is TODO. Do not mark a pass, and do not show `Test: passed 1:45 AM` on `/backstage`, before this table is filled from a run. Spec: [sino/mvp-plan.md](sino/mvp-plan.md).

| Result | Value |
|---|---|
| urgent | TODO/10 |
| comfort | TODO/10 |
| TV false triggers | TODO |
| mode | TODO (`ollama` or `stub`) |

## Handoffs

(Use the template in [01-team.md](01-team.md#handoff-note-write-it-in-docsnotesmd-at-100-am-and-430-am).)
