# web/backstage

Desktop `/backstage` screen for Sino ("Sino's log"). Static HTML, no build step, no CDN.

## Files
- `index.html`: layout, styles, and the live client
- `fonts/`: Fredoka 500/600 and DM Sans 400/500/700 (latin, SIL OFL, Fontsource). Keep next to `index.html`.

## Run
From the repo root, with the stub model:

```bash
SINO_MODEL=stub python3 brain/server.py
```

Open `http://<hub>:8000/backstage/`. A request to `/backstage` redirects to `/backstage/`.

No query uses the fake feed (`web/fake-feed`) and shows a FAKE tag. `?feed=hub` uses the hub socket at `/ws?screen=backstage`.

`setTest({ time, urgent, comfort, tv, latency })` shows the T5 badge only after a real hub run is logged in `docs/NOTES.md`. Nothing calls it, and the page does not read that file.
