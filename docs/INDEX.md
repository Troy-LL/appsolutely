# Index and glossary

Read this first. It tells you which file owns what and when to open it.

**Our project is Sino** (idea locked Fri Oct 9). Its spec lives in [docs/sino/](sino/README.md). Start there for anything about what we're building.

**Language:** you can talk to AI tools in Tagalog or Taglish (Bisaya works too, a bit less reliably). Keep code, commits, and the README in English.

## Files

| File | What it's for | Owner | Read it when |
|---|---|---|---|
| [README.md](../README.md) | What this repo is, key dates, setup steps (after 1 PM) | Ayen (setup steps), Troy | First visit; Sat 5 AM clean-clone test |
| [AGENTS.md](../AGENTS.md) | Rules for AI coding assistants | Troy | Before you let any AI tool touch the repo |
| `CLAUDE.md`, `.cursor/rules/project.mdc` | Copies of AGENTS.md so every tool loads it | Troy | Never edit alone; keep in sync with AGENTS.md |
| [docs/INDEX.md](INDEX.md) | This file: table of contents and glossary | Troy | Anytime you're lost |
| [docs/00-event.md](00-event.md) | Event facts, official Local AI theme, challenge, rules, judging weights, knock-out list, prizes, Demo Day logistics | Viviene | Before scoring ideas; whenever a rule is unclear |
| [docs/01-team.md](01-team.md) | Roles, pairs, owners per area, designer task split, sleep shifts, handles | Troy (designer split: Ayen + Viviene) | Tonight, and at every handoff |
| [docs/02-philosophy.md](02-philosophy.md) | Vision and principles (incl. "local is the point"); UI-first trade-offs; 5+3 pitch structure and judge Q&A prep | Troy + Ayen | Tonight, and whenever a decision feels unclear |
| [docs/03-playbook.md](03-playbook.md) | 1:00 to 2:30 PM sequence, model smoke-test gate, hardware notes, full timeline, airplane-mode tests, syncs, merge rules | Troy | 12:30 PM Fri, then at every sync |
| [docs/04-idea-filter.md](04-idea-filter.md) | Gates and weighted scoring (official 25/25/20/15/15). Its spec sections are superseded by docs/sino/ | Troy (filter), Ayen (screen), Troy + Donita (AI contract) | 1:00 PM Fri; it becomes the spec at 2:30 PM |
| [docs/05-submission.md](05-submission.md) | Official submission checklist (local vs. internet, disclosures, why-local answer) and video/post templates | Viviene | Tonight (prep), Sat 7:00 AM (execute) |
| [docs/sino/README.md](sino/README.md) | **Sino spec, start here:** one-page overview, problem, flow, why local, source-of-truth rules | Troy | First, before any Sino work |
| [docs/sino/features.md](sino/features.md) | MVP (incl. quick setup), should, add-ons behind the cut line, next steps; seeded replies; UX rules | Troy (scope), Ayen (quick setup) | Before building anything; at every sync |
| [docs/sino/architecture.md](sino/architecture.md) | Devices, network + fallbacks, viewports and routes, models + speech model selection, 3 interfaces, data flow, offline guarantees, privacy, to-verify list | Donita (hub), Troy (decision engine) | Before writing hub, decision, or screen code |
| [docs/sino/mvp-plan.md](sino/mvp-plan.md) | Timeline, pass/fail gate, sprints per person, sync points, task graph | Troy | 10:30 PM Fri, then at every sync |
| [docs/sino/demo.md](sino/demo.md) | Pitch run of show, why-local close, "Sino ka?" roleplay, "Nasaan si Lola?", fallbacks, video | Troy (script), Viviene (visuals) | 7:00 AM Sat rehearsals |
| [docs/sino/judge-qa.md](sino/judge-qa.md) | Judge Q&A answers, risks and mitigations | Troy | Before rehearsals and Demo Day |
| [docs/sino/DONITA-SETUP.md](sino/DONITA-SETUP.md) | M1 (8 GB) hub installs and offline smoke test | Donita | Before the build; results go to NOTES |
| `docs/sino/task-graph.mmd`, `task-graph.png` | Task dependencies (source and image) | Troy | With mvp-plan |
| [docs/NOTES.md](NOTES.md) | Links, briefing summary, model smoke-test results, decision log, handoffs | Viviene (briefing), anyone (decisions) | 12:45 PM briefing; whenever a decision is made |
| `CONTRIBUTIONS.md` (created after 1 PM) | Who built what, tools used | Viviene | Sat 7:00 AM |

## Reading order

1. Everyone, before building Sino: INDEX → sino/README → sino/features → sino/architecture → sino/mvp-plan (your own sprint table).
2. Donita: also sino/DONITA-SETUP before the build.
3. Background rules, anytime: 00-event, 01-team, 02-philosophy, 03-playbook.
4. Sat 7:00 AM: sino/demo, sino/judge-qa, 05-submission.

## Source of truth / do not invent

- Facts about Sino come only from `docs/sino/`. Official rules come only from `00-event.md`. Cite the file when you state a fact.
- If a fact isn't written down, write `TODO:` and ask. Never guess hardware, models, owners, numbers, or features.
- Latency, accuracy, and other numbers stay "to verify at smoke test" until a real measurement is logged in NOTES.

## Glossary

| Term | Meaning |
|---|---|
| **The sentence** | "When [user] is [moment], they [pain]. With our app they [one action] and get [result] in [seconds]." Every feature must serve it. |
| **One user, one moment** | We design for a single named person in a single painful moment, not a market. |
| **Slice** | A thin, user-visible piece that goes from real input to real result end to end. We build in slices, never "all backend, then all frontend". |
| **Happy path** | The exact flow shown in the demo. It must work every time. |
| **Wow moment** | The single thing in the demo that makes judges react. Named by 1:50 PM Fri. |
| **AI contract** | The exact JSON the backend returns to the UI, plus model, prompt sketch, and known failure cases. Locked at 2:20 PM so UI and backend build in parallel. |
| **Demo script** | Click-by-click list of what judges will see. If it's not in the script, it waits. |
| **Kill rule** | If the only AI is "chat with it", or we can't reach a real tester for the user, go back to the filter. |
| **Pivot lock** | 4:00 PM Fri. No idea changes after this. |
| **7 PM checkpoint** | Real AI working end to end on a phone. If not, cut scope immediately. Visual polish starts only after this passes. |
| **Cut list** | Everything we decided not to build. Updated at every sync. |
| **Freeze** | 7:00 AM Sat feature freeze. Only bug fixes after, merged by Troy (or Donita). |
| **Knock-out** | A miss that eliminates us no matter how good the app is (see 00-event and 05-submission). |
| **Sync** | 10-minute check-in: done, next, blocked. Viviene keeps time. |
| **Handoff note** | Short written note in `docs/NOTES.md` at each sleep switch (template in 01-team). |
| **Merge owner** | Troy. Donita is backup when Troy is asleep, pitching, or away. |
| **Eval set** | 10 to 20 labeled inputs plus a script that reports accuracy and latency. The only source of numbers we quote. |
| **On-site anchor** | A teammate registered at Cyberzone by 12:00 PM Sat. At least one is required for finals; we plan for Troy, Viviene, Ayen. |
| **Stretch** | Generic term from the playbook: nice-to-have built only after the core works. For Sino, see **Add-ons** |
| **Local AI** | The event theme: meaningful AI computation runs on the user's own device, not only in the cloud. Not "AI for a local audience". |
| **Airplane-mode test** | Running the app with the network off on the demo device. Every timed demo run, every user test from 7 PM, and the first 10 s of the video. |
| **Smoke test** | Right after idea lock: the exact model on the actual demo device, airplane mode, ~5 real inputs, speed and accuracy logged in NOTES. Fail by ~4 PM means pivot. |
| **Why-local answer** | One sentence on why the product needs local AI, using one of the five official reasons: difficult, expensive, slow, private, impossible. Required at submission. |
| **Sino** | Our project: a home hub that answers Lola's repeated questions in her family's recorded voice, and alerts the caregiver when needed. Fully offline. See sino/README |
| **Hub** | Donita's M1 (8 GB) MacBook Air running the mic, whisper.cpp, Ollama, and the server for all screens |
| **Lola's screen** | The A16 iPad, route `/lola`. Big clock, idle photo, full-screen photo with the family voice. Nothing else. Never red |
| **Caregiver phone** | Troy's iPhone 15, route `/caregiver`. Log, red cards (sound), quiet grouped yellow cards, record-a-reply |
| **Backstage** | The behind-the-scenes screen on the hub, route `/backstage`, where judges watch the AI decide |
| **Decision** | `decide()` output: one of comfort, caregiver, urgent, silent, plus reason, trigger words, confidence, latency |
| **Comfort / caregiver / urgent / silent** | Play a family reply / send Lola's question to the caregiver / red alert now / stay quiet and log it |
| **Escalate-only** | The AI can raise a decision (e.g. to urgent) but never lower one set by the urgent-word rules |
| **Silent-if-unsure** | Below the match threshold, Sino says nothing to Lola and logs the line |
| **Seed data** | `seed.json`: demo household (Lola Cora), questions, recorded replies, photos, safety words, earlier log. Disclosed as demo data |
| **Family voice reply** | A real recording by a family member (teammates in the demo), played with their photo. No synthetic voice |
| **Pass/fail gate** | The 30-clip test by 1:45 AM: urgent 10/10, comfort ≥ 8/10, 0 TV false triggers, known questions ≤ 3 s |
| **Quick setup** | Sino's onboarding and an MVP feature: add question, two phrasings, hold to record, photo, test. Route `/setup` |
| **Junk-line filter** | Drops quiet clips, likely-no-speech clips, and known Whisper junk lines ("Thank you for watching", "Salamat sa panonood") before `decide()` |
| **Throttle** | One model call at a time; stale clips are dropped |
| **Listen now** | Hidden button on `/backstage` that forces a capture; with the typed-question box, the demo safety |
| **Urgent chime** | Loud sound from the hub speaker on an urgent decision; first alert channel (no push offline) |
| **Cut line** | Everything below it in features.md is an add-on, built after the 2:00 AM freeze only |
| **Add-ons** | Sino's post-freeze extras, in order: (a) face greeting, (b) "Nasaan si Lola?" on a recorded clip, (c) voice ID. Each has an off switch; cut at 5:00 AM |
| **Health light** | Status of Whisper, Ollama, server, and mic on `/backstage`; tells anyone whether to run `start.sh` |
| **MVP freeze** | 2:00 AM Sat for Sino's core. Different from the 7:00 AM team feature freeze |
| **To verify at smoke test** | Label for any number or capability not yet measured on the real devices |
| **Explainable** | You can walk a judge through any file you merged, without notes. |
