# Fake event feed (V1)

Lets `/lola`, `/caregiver` and `/backstage` build without the hub. Owner: Viviene.

- `index.js`: `openFeed(screen, onEvent)` plays a scripted run of Lola's lines and calls `onEvent` with the same `/ws` messages the hub sends to that screen ([architecture.md](../../docs/sino/architecture.md#the-3-interfaces-locked-in-the-first-15-minutes)). Add `?feed=hub` to the page URL to switch to the real hub socket with no other code change.
- `check.mjs`: plays the script fast and checks every message's keys and per-screen routing against the contract. Run `node web/fake-feed/check.mjs`.

The script covers: comfort (known questions), urgent (red card), caregiver (medication, "sakit ng loob", model fallback, and one repeat so the yellow card groups to `count: 2`), a TV line ignored by the rule, a junk-line drop, a too-quiet drop, and Ollama going down and back up on the health light. Backstage should end with `TV lines ignored: 2`.

The decisions are real `brain/decide.py` stub-mode output. `latency_ms` is the stub's own number, not a hub measurement. `reply_audio` and `photo` are empty, as in `brain/seed.json`. Screens should show a FAKE label while `IS_FAKE` is true.

Not covered: `ask_about_lola` / `about_lola` and `meal_logged` (Should items, after the freeze). No dependencies.
