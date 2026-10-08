# 01 Team

## Pairs and roles

| Pair | Person | GitHub | Role |
|---|---|---|---|
| **Backend / AI** | Troy | `@Troy-LL` | AI core, API, eval script, architecture diagram, pitch lead, Q&A captain, **merge owner** |
| | Donita | `@DonitaSalonga` | Backend and AI with Troy, guardrails and failure states, QA, **backup merge owner** |
| **UI / UX** | Ayen | `@AyenMejorada` | **UX/UI lead**: flow, design system, hero screen, front-end screens, README |
| | Viviene | `@jwiwooyang` | UI/UX with Ayen, plus brand kit, ~1 min video, social post, submission checklist, timekeeper |

## What each person is strong at (lean on them for this)

- **Troy:** AI and data work. Lean on him for model choice, prompts and tools, structured output, eval numbers, and the technical story in Q&A.
- **Donita:** Python web backends (Flask on Vercel) and AI security (OWASP LLM Top 10, prompt injection). Lean on her for input validation, abuse cases, safe refusals, QA passes, and "what are the limits?" answers.
- **Ayen:** turning Figma designs into React + Tailwind, data viz (Chart.js), and clear plain-language writing. Her design approach, "simple, intentional, built for clarity", is our product style. Lean on her for every screen decision and the README.
- **Viviene:** graphic design, branding, video editing, and social/marketing. Calm under pressure as an event host. Lean on her for the brand kit, the video, the post, the People's Choice push, and running user tests.

## Owners per area

| Area | Owner | Backup |
|---|---|---|
| Idea filter facilitation (1:10 PM) | Troy | Ayen |
| User flow, frames, design tokens | Ayen | Viviene |
| Front-end screens | Ayen | Viviene, Donita |
| Brand kit (name, logo, accent color) | Viviene | Ayen |
| AI contract (JSON) | Troy + Donita | |
| AI core, prompts, model calls | Troy | Donita |
| API and backend glue | Donita | Troy |
| Guardrails, error/empty/loading states | Donita | Ayen (UI side) |
| Eval set and script | Troy | Donita |
| Architecture diagram | Troy | Ayen (visuals) |
| README and setup steps | Ayen | Viviene (clean-clone test) |
| Deploy | Donita | Troy |
| Real-user tests | Viviene | Ayen |
| Briefing scribe, sync timekeeping, cut list | Viviene | |
| Video, post, submission form | Viviene | Troy |
| `CONTRIBUTIONS.md`, AI tools disclosure | Viviene (collects) | Troy (checks) |
| Merges to `main`, repo goes public | Troy | Donita |
| Pitch and Q&A | Troy | Viviene (problem/user section), Donita (limits/security) |

**Everyone** can explain their own files and the core flow in 60 seconds, without notes.

## Sleep shifts (cross-pair)

Each shift has one backend person and one UI person, so both sides of the app are covered at all hours.

| Shift | Who | Sleeps | On duty alone |
|---|---|---|---|
| **A** | Donita + Viviene | **1:00 to 4:30 AM** | 4:30 to 7:00 AM |
| **B** | Troy + Ayen | **4:30 to 7:00 AM** | 1:00 to 4:30 AM |

- **1:00 to 4:30 AM (Troy + Ayen awake):** bug fixes, AI reliability, eval run, architecture diagram, README draft, visual polish on working screens. No new features.
- **4:30 to 7:00 AM (Donita + Viviene awake):** bug fixes, guardrail pass, 6 AM real-user test, README clean-clone test, video shot prep. Donita merges.
- **7:00 AM:** everyone up, sync, feature freeze.
- If someone can't sleep at their window, they still go offline and rest. Swapping is fine if both pairs agree and coverage holds.

### Handoff note (write it in `docs/NOTES.md` at 1:00 AM and 4:30 AM)

```
## Handoff HH:MM, from [names] to [names]
- main status: green / broken (link to last deploy)
- Done since last sync:
- In progress (branch, what's left):
- Known bugs (priority order):
- Do NOT touch:
- Next 3 tasks for the awake shift:
- Wake us if:
```

## Contact

Use the Appsolutely Messenger GC for the team and the official Telegram group for event announcements. GitHub handles are listed above.
