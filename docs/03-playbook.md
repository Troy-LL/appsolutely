# 03 Playbook

All times PH. Owners per area are in [01-team.md](01-team.md).

## Thu Oct 8 (tonight): prep only, no project code

- [ ] Everyone confirms Fri 12:30 PM to Sat, and who is on-site by 12 PM Sat (Troy + Viviene suggested)
- [ ] Everyone in the official Telegram group
- [ ] Accounts: GitHub with 2FA, Vercel, Figma team file, X or LinkedIn that can post video, Cerebral Valley (once link is out)
- [ ] Tooling: Node LTS, Python 3.11+, git, editor, screen recorder. Test `npm create vite` and `pip install fastapi` work
- [ ] Ayen: moodboard of "one-tap obvious" apps (GCash send, Google Lens, Grab, Apple Weather). References only, no screens for our app
- [ ] Troy: API keys for 2 model providers, time a structured-JSON call on each, note rate limits
- [ ] Viviene: video shot list, post draft with verified Devin/Cognition handles, `CONTRIBUTIONS.md` skeleton kept local until 1 PM
- [ ] Ask in Telegram: judging criteria, sponsor award criteria
- [ ] Sleep

## Fri Oct 9: 1:00 to 2:30 PM (all four on one call)

| Time | Step | Who |
|---|---|---|
| 12:30 to 1:00 | Join the room and briefing. Copy judging criteria and submission rules **verbatim** into `docs/NOTES.md` | Viviene scribes |
| 1:00 to 1:10 | Read the challenge **twice, silently**. Each person writes 3 people it hurts and their worst moment. No talking | All |
| 1:10 to 1:25 | **Filter** ideas with the gates and scores in [04-idea-filter.md](04-idea-filter.md) | Troy facilitates |
| 1:25 to 1:35 | **Pick one user + one moment.** Write the sentence | All, Troy breaks ties |
| 1:35 to 1:50 | **One screen, one action:** input → one tap → AI result card → next step. Name the wow moment. Start the cut list. Kill rule check | Ayen leads, Troy checks AI feasibility |
| 1:50 to 2:10 | **3 to 5 frames** (empty, input, loading, result, error). Show one non-team person: "what would you tap?" Viviene drafts brand kit | Ayen + Viviene; Donita notes components |
| 2:10 to 2:20 | **AI contract:** JSON shape, model, prompt sketch, 3 known failure cases | Troy + Donita |
| 2:20 to 2:30 | **Lock:** spec paragraph and click-by-click demo script in 04-idea-filter. Split files by owner | Troy |

## Full timeline to submit

| Time | What | Notes |
|---|---|---|
| Fri 2:30 to 3:00 PM | Scaffold from public starters (Vite + shadcn, FastAPI). Deploy "hello" | `main` live from here on |
| 3:00 to 7:00 PM | **Ugly end-to-end slice:** real input → real model → result card on a phone | Stub nothing that's in the demo |
| 4:00 PM | **Pivot lock** | |
| 7:00 PM | **Checkpoint:** happy path works on a phone every time? If not, cut scope now. User test #1. Dinner | Visual pass starts only after this |
| 7:30 PM to 12:00 AM | Slice 2 (wow moment), error/empty/loading states, visual pass on working screens, eval set (10 to 20 cases). User test #2 at ~10 PM | |
| 12:00 to 1:00 AM | Judge-question drill #1, demo run #1 (timed), README draft, architecture diagram | |
| 1:00 AM | **Handoff:** Donita + Viviene sleep | Handoff note in NOTES.md |
| 1:00 to 4:30 AM | Troy + Ayen: bug fixes, AI reliability, eval run, diagram, polish. **No new features** | |
| 4:30 AM | **Handoff:** Troy + Ayen sleep | Handoff note in NOTES.md |
| 4:30 to 7:00 AM | Donita + Viviene: bug fixes, guardrail pass, user test #3 (~6 AM), README clean-clone test, video prep. Donita merges | |
| Sat 7:00 AM | **Feature freeze.** All up, sync, demo run #2 | Bug fixes only after this |
| 7:00 to 8:00 AM | Record video (plus full backup demo), finalize `CONTRIBUTIONS.md` and AI tools disclosure. **Repo public at 8:00** | See 05-submission |
| 8:00 to 8:30 AM | Publish post. **Submit by 8:30**, two people check every field first | One submission only |
| 8:30 AM to 12:00 PM | Travel to Cyberzone, SM Makati. Rehearse the 5-min pitch twice. Judge drill #2 on the way | |
| 12:00 PM | **On-site and registered** | Demo run #3 on-site |

## Sync times (10 minutes each)

Fri 3 PM, 5 PM, 7 PM, 10 PM, 12 AM. Handoffs 1:00 AM and 4:30 AM. Sat 7:00 AM.

Format: each person says **done / next / blocked**. Viviene keeps time and updates the cut list.

## Dev loop

- **Vertical slices.** Each slice is user-visible, input to result.
- **`main` is always demoable and deployed.** If `main` breaks, fixing it beats everything else.
- **Small PRs** (under ~200 lines), one owner per file area, so "who built what" is true in git.
- **Branches:** `troy/agent`, `donita/api`, `ayen/result-card`, `viviene/brand`. No `cursor/` or tool-named branches.
- **AI-assisted coding is fine.** Log the tools as you go for the disclosure.

## Merge rules

- Troy merges to `main`. Donita merges when Troy is asleep, pitching, or away.
- Squash-merge with a clear title. Commits are authored by the human who owns the work.
- **Don't merge code you can't explain.** The merger asks "walk me through it" if unsure.
- After 7:00 AM: bug fixes only.
- No secrets in the repo. Use `.env` (gitignored) and an `.env.example`.

## Feedback loop

- **Real-user tests** at ~2 PM (paper frames), 7 PM, 10 PM, 6 AM. Hand over the phone, give one instruction, say nothing, time it, note where they hesitate. Fix the top issue before the next test. Testers only use the app; they don't build or design.
- **Judge-question drill** (12 AM, and on the way to Makati). Each person answers 2 out loud in under 30 seconds:
  - Why AI here and not rules?
  - What happens when the model is wrong?
  - Which model, where does it run, what does it cost per use?
  - Show me the file you wrote.
  - What are the limits?
  - How do you know it works? (eval numbers and test-set size, never rounded up)
- **Demo runs** at 12 AM, 7 AM, and on-site: full 5 minutes with a timer, on the demo laptop, inputs pre-loaded. Once with Wi-Fi off to test the fallback.

## Pitch shape (5 min + 3 min Q&A)

| Time | Beat |
|---|---|
| 0:00 to 0:30 | The user and the moment |
| 0:30 to 3:30 | Live demo of the happy path and the wow moment |
| 3:30 to 4:30 | Architecture and measured numbers (one slide) |
| 4:30 to 5:00 | Limits, what's next, "scan the QR for People's Choice" |
