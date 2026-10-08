# Index and glossary

Read this first. It tells you which file owns what and when to open it.

## Files

| File | What it's for | Owner | Read it when |
|---|---|---|---|
| [README.md](../README.md) | What this repo is, key dates, setup steps (after 1 PM) | Ayen (setup steps), Troy | First visit; Sat 5 AM clean-clone test |
| [AGENTS.md](../AGENTS.md) | Rules for AI coding assistants | Troy | Before you let any AI tool touch the repo |
| `CLAUDE.md`, `.cursor/rules/project.mdc` | Copies of AGENTS.md so every tool loads it | Troy | Never edit alone; keep in sync with AGENTS.md |
| [docs/INDEX.md](INDEX.md) | This file: table of contents and glossary | Troy | Anytime you're lost |
| [docs/00-event.md](00-event.md) | Event facts, rules, knock-out list, prizes, Demo Day logistics | Viviene | Tonight, and at the 12:45 PM briefing |
| [docs/01-team.md](01-team.md) | Roles, pairs, owners per area, sleep shifts, handles | Troy | Tonight, and at every handoff |
| [docs/02-philosophy.md](02-philosophy.md) | Vision and principles; how UI-first wins and where it can lose | Troy + Ayen | Tonight, and whenever a decision feels unclear |
| [docs/03-playbook.md](03-playbook.md) | 1:00 to 2:30 PM sequence, full timeline, dev loop, feedback loop, syncs, merge rules | Troy | 12:30 PM Fri, then at every sync |
| [docs/04-idea-filter.md](04-idea-filter.md) | Scoring template plus the locked spec: user, moment, screen, AI contract, failure cases, cut list | Troy (filter), Ayen (screen), Troy + Donita (AI contract) | 1:00 PM Fri; it becomes the spec at 2:30 PM |
| [docs/05-submission.md](05-submission.md) | Submission checklist and video/post templates | Viviene | Tonight (prep), Sat 7:00 AM (execute) |
| [docs/NOTES.md](NOTES.md) | Briefing notes (verbatim criteria) and a decision log | Viviene (briefing), anyone (decisions) | 12:45 PM briefing; whenever a decision is made |
| `CONTRIBUTIONS.md` (created after 1 PM) | Who built what, tools used | Viviene | Sat 7:00 AM |

## Reading order

1. Everyone tonight: INDEX, 00-event, 01-team, 02-philosophy.
2. Fri 12:30 PM: 03-playbook, then 04-idea-filter open on screen.
3. Sat 7:00 AM: 05-submission.

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
| **On-site anchor** | A teammate registered at Cyberzone by 12:00 PM Sat. We need at least two. |
| **Explainable** | You can walk a judge through any file you merged, without notes. |
