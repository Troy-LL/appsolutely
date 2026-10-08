# 02 Philosophy

## Vision

Build something **so simple and so visual that a stranger uses it correctly in 10 seconds, on their phone, and it makes a real moment in their life better.** UI/UX first, portable (phone-first web app), life-improving. The topic arrives at 1 PM Fri; this stance doesn't change with it.

## Principles

1. **One user, one moment.** One named person, one painful moment. If a feature doesn't serve [the sentence](04-idea-filter.md#2-the-user-and-the-moment), it's cut.
2. **The demo is the product.** Build exactly what judges will see, click by click. Anything outside the demo script waits.
3. **AI earns its place and is explainable.** It does something a form or a list can't. We can name the model, the prompt and tools, the failure cases, and our measured numbers.
4. **Working > pretty > more features.** Ugly slice first. Polish only screens that already work. Never add a feature to cover a weak one.
5. **Cut before polish.** At every checkpoint, ask what to remove before asking what to add.
6. **Everyone explains their part.** No orphan code. Git history matches `CONTRIBUTIONS.md`.
7. **The checklist is not optional.** Public repo, video, post, and submission in by 8:30 AM. A missed item ends the run regardless of quality.

## How UI-first wins

- Most teams will ship a chat box. A product that feels obvious in 10 seconds is something judges *feel*.
- It wins **People's Choice** (audience QR vote) and demos well live on a phone.
- Local judge pools have scored UX and real-world applicability explicitly.

## Where UI-first can lose

- Judges run a serious Q&A on architecture, the AI, its limits, and who built what, and they may read the code. **A pretty shell over one generic AI call collapses** under "why is this AI?" and "show me the code".
- Polishing before the core works burns the hours we need.

## How we cover the risk

- **Show the AI inside the UI:** what it understood ("I read: ..."), how sure it is, a one-tap correction, and an honest fallback state. Good AI UX is our architecture answer.
- **More than one prompt:** structured JSON output, at least one tool or retrieval step, input validation and guardrails.
- **Bring real numbers:** a 10 to 20 case eval in the repo, with test-set size and failures listed. Never round up.
- **Schedule it:** the 7 PM checkpoint needs real AI working end to end before the visual pass.
- **One architecture diagram** in the README and on one slide.

## Design defaults (decided tonight, no components built)

- React + Vite + Tailwind + shadcn/ui, phone-first, installable as a PWA.
- One font (Inter), Lucide icons, one accent color plus neutrals, 8-pt spacing.
- Core pattern: **input → one tap → AI result card → one next step.**
- Every screen has empty, loading, result, and error states.
