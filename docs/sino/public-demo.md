# Public demo on Fly.io

Host the public demo on Fly.io. Use an always-on shared-cpu-1x machine with 1 GB of RAM, about $3–5 per month. HTTPS is required. Fly terminates TLS at the edge. The process inside the machine speaks plain HTTP.

## Why Fly, not Render's free tier

Render's free web service spins down after idle, and its proxy closes WebSockets after about five minutes.
A pitch left open on `/demo/` would drop in the middle.
Fly with `min_machines_running = 1` and auto-stop off keeps one machine up, so the socket stays connected.
That machine is shared-cpu-1x with 1024 MB, enough for the OpenCV clip scan, at about $3–5 per month.
Fly terminates HTTPS. The process speaks HTTP inside the machine and does not load certificates.
Recommend Fly.io for the public demo.

## Prerequisites

- [flyctl](https://fly.io/docs/flyctl/install/) installed.
- `fly auth login` (a Fly account).
- A card on file. The always-on machine is a paid size, not the free allowance.

`fly launch` is not required. `fly.toml` is already in the repo.

## Deploy

From a clean clone, once, after you are logged in:

```bash
fly apps create appsolutely-sino
```

The name in `fly.toml` is a placeholder. Rename `app` there before `fly apps create` if you want a different name, and use that same name in the create command. `primary_region` is `sin` (Singapore). Change that line before the first deploy if you want another region.

Then, from the repo root, the deploy command:

```bash
fly deploy
```

That builds the root `Dockerfile` and ships it. Do not put secrets, a `.env` file, or certificate files in the image. Fly's proxy is the HTTPS endpoint.

## Cost

shared-cpu-1x, 1024 MB RAM, one machine left running (`min_machines_running = 1`, `auto_stop_machines = "off"`). About $3–5 per month while it stays up. Stop or destroy the app when the demo is over if you do not want the charge to continue.

## What the URL serves

The process is `python brain/server.py` from `/app` (the repo root). `main()` binds `0.0.0.0` and `PORT` (default 8000). The image sets `SINO_MODE=demo`, `SINO_MODEL=stub`, `CHIME=0`, and `ALWAYS_LISTEN=0`.

| Path | What it is |
|---|---|
| `/` | Public front door |
| `/demo/` | Simulated walkthrough |
| `/lola/` | Lola's screen (`web/lola`) |
| `/caregiver/` | Caregiver app, built into `web/caregiver/dist` in the image |
| `/backstage/` | Decisions |

`/lola/`, `/caregiver/`, and `/backstage/` are mounted by `brain/server.py`. `/` and `/demo/` are the public front door and the simulated walkthrough when those pages are in the image.

The public demo is simulated: stub decisions, seeded questions and recordings, no Ollama, and no microphone.

An empty `brain/clips/models` directory still builds. This image does not download detector weights.

## Health check

`GET /health` must return HTTP 200. Fly uses that path. The JSON includes `"server": true`. In this demo, Whisper and Ollama show false. That is expected: they are not in the image.

## WebSockets

Open `https://<app>.fly.dev/demo/` and leave it open. The page keeps a WebSocket to the hub (`/ws`). The machine is not allowed to auto-stop, so a demo is not cut off by spin-down.

## Secrets

The image has no `.env`, no API keys, and no cert files. TLS stops at Fly. The home hub's mkcert files stay on the Mac (`~/sino/certs`) and are not copied in.
