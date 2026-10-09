# AGENTS.md: rules for AI coding assistants

These rules apply to every AI tool used in this repo (Claude Code, Cursor, Copilot, Devin, and others). `CLAUDE.md` and `.cursor/rules/project.mdc` are copies of this file; keep all three identical.

## Read first, every session

1. `docs/INDEX.md`: where everything lives
2. `docs/sino/README.md`: **the locked spec** for our project, Sino, then `features.md` (scope), `architecture.md` (devices, models, interfaces), and `mvp-plan.md` (who owns what, when)
3. `docs/02-philosophy.md`: the vision and principles

## Source of truth / do not invent

- Facts about the project come only from `docs/sino/`; official event rules come only from `docs/00-event.md`. **Cite the doc** a fact comes from when you state it.
- **Unknown means TODO, never a guess.** If hardware, a model, an owner, a number, or a feature isn't written down, write `TODO:` and ask the human.
- Latency, accuracy, and other unmeasured numbers are "to verify at smoke test" until a real measurement is logged in `docs/NOTES.md`. Never state them as results.
- Don't build anything outside `docs/sino/features.md`. New ideas go to its "Next steps" list. Since Sat 2:00 AM every add-on is cut (face match, CCTV, voice ID, live call); Should items are built only after the 3:30 AM MVP freeze.

## Stay inside the spec

- Build only what serves the sentence and the demo script. Anything on the cut list stays cut.
- Follow the interfaces in `docs/sino/architecture.md` exactly. If it must change, stop and tell the human; both the UI and the backend depend on it.
- Core UI pattern: input → one tap → AI result card → one next step. Every screen has empty, loading, result, and error states.
- Stack defaults: React + Vite + Tailwind + shadcn/ui (phone-first, PWA), Python FastAPI backend, Inter, Lucide icons, one accent color.
- Don't add dependencies, services, auth, or new screens unless the human asks.

## Local AI rules (event theme)

- **Core inference runs locally** on the user's device. The core path must work with the network off.
- **Never swap in a cloud AI API for the core path**, even to "make it work for now". If local is too slow or broken, stop and tell the human.
- Any cloud use must be **optional and secondary**, and listed in the README disclosures.
- Keep a **running disclosure list in the README**: every model, library, framework, API, cloud service, existing code or asset, and AI development tool used. Add to it in the same change that introduces the item.

## Small, explainable changes

- One focused change at a time, under ~200 lines where possible.
- Prefer the simplest code that works. No clever abstractions.
- Explain what you changed and why in plain language, so the human can explain it to a judge.
- Never write code the human can't walk through. If something is complex, add a short comment saying what it does.
- Report real numbers only. Never invent, round up, or fake eval results or benchmarks.
- Don't break `main`. If a change breaks the build, fix it before anything else.

## Secrets and safety

- Never commit API keys, tokens, or `.env` files. Use `.env` (gitignored) and keep `.env.example` updated with names only.
- Don't log user inputs that could be personal data.
- Treat model output and user input as untrusted. Validate before rendering or acting on it.

## Git and attribution

- **Commit as the human** who owns the work, with their own git name and email.
- **No `Co-authored-by` lines, no Cursor or other tool trailers, no "Generated with" footers**, and no tool watermarks in commit messages or PR bodies.
- Branch names use the owner's name: `troy/...`, `donita/...`, `ayen/...`, `viviene/...`. Never `cursor/...` or other tool-named branches.
- Don't push to `main` directly unless the human says so. Don't force-push.
- After 7:00 AM Sat (feature freeze): bug fixes only.

## Hackathon rules to respect

- No project code before 1:00 PM Fri Oct 9. Planning docs only.
- Only the four registered members build. The AI tools used must be disclosed at submission, so tell the human which tool did what.
