# 01 Team

## Pairs and roles

| Pair | Person | GitHub | Role |
|---|---|---|---|
| **Backend / AI** | Troy | `@Troy-LL` | AI core, API, eval script, architecture diagram, pitch lead, Q&A captain, **merge owner** |
| | Donita | `@DonitaSalonga` | Backend and AI with Troy, guardrails and failure states, QA, **backup merge owner** |
| **UI / UX** | Ayen | `@AyenMejorada` | **UX/UI lead**: flow, design system, hero screen, front-end screens, README |
| | Viviene | `@jwiwooyang` | UI/UX with Ayen, plus state screens, icons and assets, brand kit, ~1 min video, post graphic, pitch visuals, submission checklist, timekeeper |

**Sino pairs since 1:51 AM Sat (Troy):** Troy + Donita on the backend (hub + brain), Ayen + Viviene on the frontend (`/lola`, `/setup`, `/caregiver`, `/backstage`). Per-person tasks: [sino/mvp-plan.md](sino/mvp-plan.md#owners).

Ayen is listed as "Yen" on the official participant list (confirmed). Use "Ayen" on the submission form and in `CONTRIBUTIONS.md`.

## Availability

- **Ayen:** free all day Friday, locked in from the 12:30 PM room open.

## What each person is strong at (lean on them for this)

- **Troy:** AI and data work. Lean on him for model choice, prompts and tools, structured output, eval numbers, and the technical story in Q&A.
- **Donita:** Python web backends (Flask on Vercel) and AI security (OWASP LLM Top 10, prompt injection). Lean on her for input validation, abuse cases, safe refusals, QA passes, and "what are the limits?" answers.
- **Ayen:** turning Figma designs into React + Tailwind, data viz (Chart.js), and clear plain-language writing. Her design approach, "simple, intentional, built for clarity", is our product style. Lean on her for every screen decision and the README.
- **Viviene:** graphic design, branding, video editing, and social/marketing. Calm under pressure as an event host. Lean on her for the brand kit, the video, the post, the People's Choice push, and running user tests.

## Owners per area

| Area | Owner | Backup |
|---|---|---|
| Idea filter facilitation (1:10 PM) | Troy | Ayen |
| User flow, key screen frames, design tokens | Ayen | Viviene |
| State screens (empty, loading, error, success) | Viviene | Ayen |
| Icons, illustration, assets | Viviene | Ayen |
| Front-end screens | Ayen | Viviene, Donita |
| Final visual QA, demo screen look | Ayen | Viviene |
| Brand kit (name, logo, accent color) | Viviene | Ayen |
| AI contract (JSON) | Troy + Donita | |
| AI core, prompts, model calls | Troy | Donita |
| API and backend glue | Donita | Troy |
| Guardrails and failure logic | Donita | Troy |
| Eval set and script | Troy | Donita |
| Architecture diagram | Troy | Ayen (visuals) |
| README and setup steps | Ayen | Viviene (clean-clone test) |
| Deploy | Donita | Troy |
| Real-user tests | Viviene | Ayen |
| Briefing scribe, sync timekeeping, cut list | Viviene | |
| Video, post graphic, submission form | Viviene | Troy |
| Pitch visuals / slides (if any) | Viviene | Ayen |
| `CONTRIBUTIONS.md`, AI tools disclosure | Viviene (collects) | Troy (checks) |
| Merges to `main`, repo goes public | Troy | Donita |
| Pitch and Q&A | Troy | Viviene (problem/user section), Donita (limits/security) |

**Everyone** can explain their own files and the core flow in 60 seconds, without notes.

## Designer task split (Ayen + Viviene)

A starting point. We adjust it after the 1 PM reveal, once we know the screens.

| Phase (PH time) | Ayen (UI/UX lead) | Viviene (UI/UX + creatives) |
|---|---|---|
| Fri 1:35 to 2:10 PM: one screen + frames | User flow, 3 to 5 key screen frames | Brand kit draft (name, logo, accent), first state frames |
| 2:10 to 3:00 PM: handoff to Troy + Donita | Design tokens (type, color, spacing) in Figma; walk devs through the frames | Empty, loading, error, success frames; icon and asset list |
| 3:00 to 7:00 PM: devs build the ugly slice | Build front-end screens from frames; answer dev questions | Finish state screens and assets; video shot list; post graphic draft |
| 7:00 PM checkpoint | Polish starts **only** if real AI works end to end | Same |
| 7:30 PM to 1:00 AM: polish | Visual pass on working screens, wow-moment screen | Polish state screens and illustrations; pitch visuals; user test #2 |
| 1:00 to 7:00 AM | TODO: re-decide. The rows here assumed the old cross-pair sleep shifts; since 1:51 AM Ayen and Viviene work together on the frontend | TODO: re-decide |
| Sat 7:00 to 8:30 AM | Demo screen final check | Record and edit the 1-min video, publish post graphic |

**Optional stretch: mascot (Ayen).** Only if the core works after the 7 PM checkpoint, and only if it does a job in the UI (for example an empty or loading state). Not decoration. First thing cut if time is tight.

### Design handoff rules

- All designs live in one Figma file. The link goes in [NOTES.md](NOTES.md#links).
- Devs build from the frames, not from chat descriptions.
- Designers review every merged screen on a real phone and send fixes as short notes.
- Each designer hands off before their sleep window, so nothing is stuck waiting on someone asleep.

## Sleep shifts (cross-pair)

**TODO: re-decide (Sat 2:00 AM).** These shifts were built on the cross-pairing (Troy + Ayen, Donita + Viviene). Pairs changed at 1:51 AM to Troy + Donita (backend) and Ayen + Viviene (frontend), and Donita and Viviene were still working at 1:51 AM, so the 1:00 AM switch did not happen. Kept below for history until the team picks new times.

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
