# web/backstage

Desktop `/backstage` screen for Sino ("Sino's log"). Static HTML, no build step, no CDN.

## Files
- `index.html`: layout, styles, render code (sample feed in `SAMPLE`)
- `fonts/`: Fredoka 500/600 and DM Sans 400/500/700 (latin, SIL OFL, Fontsource). Keep next to `index.html`.

## Hooking to the hub
- Feed: replace `SAMPLE` or call `addRow(event)` from the WebSocket (see the comment above `SAMPLE`).
- Test badge: call `setTest({ time, urgent, comfort, tv, latency })` only after a real hub run is logged in `docs/NOTES.md`.
- TODO: `POST /listen` for "Listen now", and `decide()` for the typed question.

## Run
Open `index.html` directly, or serve the folder from the hub.
