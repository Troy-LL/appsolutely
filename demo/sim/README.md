# Simulated demo recorder

One reproducible run of the three Sino screens, driven by the real hub in stub mode. The MP4 is for the submission video or a backup. It is not committed.

The story follows `docs/sino/demo.md`: Lola asks, a TV line is ignored, a meal is logged, an urgent line raises a red card, and the caregiver looks through the day's screens. Typed lines are `POST /listen` with `{"mode":"typed"}`. Caregiver taps, including Ask Sino, go through the pages on `/ws`.

## Run

From the repo root, after the caregiver app is built:

```bash
cd web/caregiver && npm ci && npm run build && cd ../..
python3 -m pip install fastapi 'uvicorn[standard]' python-multipart websockets playwright
python3 -m playwright install chromium
python3 demo/sim/record.py --out demo/sim/out
```

The script starts the hub itself:

`SINO_MODEL=stub`, `OFFLINE_PROBE=http://127.0.0.1:9` (so the OFFLINE badge is on), a temporary decisions log, and `CHIME=0`.

`demo/sim/out/sino-sim.mp4` is the 1920×1080 film. `lola.webm`, `caregiver.webm`, and `backstage.webm` are the raw Playwright recordings (they include the short setup before the idle shot). `marks.json` is the timeline the camera uses. Pass `--compose-only` to rebuild the MP4 from those files.

## What the camera does

ffmpeg builds one 3840×2160 stage: Lola's iPad on the left (viewport 820×1180), the caregiver iPhone on the right (390×844, device scale 3), backstage in the middle (1440×900). `zoompan` eases between framings in 0.55–0.75 s (smoothstep). It moves in on the iPad when Joy's clip plays, on backstage when the TV counter ticks, on the red card and then across to the calm iPad, on the safety-word + chip, and on the decision rows at the end. Between those beats it returns to the full layout.

The corner line `Simulated run on seeded demo data · stub model` and the English subtitles are drawn after the zoom, so they stay put. The film ends on a 4 s card: `assets/brand/sino-logo.png`, Team Appsolutely · #AppBuildersPH, and the repo URL. Taps draw an amber ring in the page.

## Sound

Joy's `nasaan-si-nanay-reply.m4a` and `meal-check-ate-reply.m4a` are muxed at the moment the iPad shows the answer. Playwright does not record page audio. The hub chime is macOS `afplay` of `Glass.aiff` (`docs/sino/hub-chime.md`); this recorder runs on Linux, so the urgent moment uses a short generated tone instead of that system sound.

## What the idle home says

`Sino is listening in the sala` is the English copy for a healthy hub (`salaOn` in `web/caregiver/src/i18n/en.ts`). In stub mode the health event marks Whisper, Ollama, and the mic down, so the sala card shows the not-working line. The script does not fake those lights. Backstage still shows OFFLINE and the health row. The phone stays in its default both-languages mode, so the buttons read Kumain na, Papunta na ako, Resibo, and Kamusta si Lola?.

Papunta na ako is included. It is on main (the urgent reply that reaches Lola's iPad).
