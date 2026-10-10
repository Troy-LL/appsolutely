# Appsolutely

<img src="assets/brand/sino-logo.png" alt="Sino" width="280">

Team repo for the **AppBuildersPH Hackathon 2026** (Team Appsolutely: Troy, Ayen, Donita, Viviene). It holds the planning docs (event facts, roles, philosophy, playbook, idea filter, submission checklist) and the Sino spec in `docs/sino/`. Per the rules, the project is built from scratch after the challenge reveal at 1:00 PM Fri Oct 9.

## Our project: Sino

Sino is a small home hub that answers a lola's repeated questions in her family's own recorded voice, decides when to comfort her, get the caregiver, or raise an alarm, and keeps working with no internet. An always-on mic in a home must never stream anywhere, so speech recognition (whisper.cpp) and the decision model (Qwen2.5 in Ollama) run on a home device. Spec: **[docs/sino/README.md](docs/sino/README.md)**.

## Disclosures (running list, updated as we build)

- **Models:** Whisper small via whisper.cpp + Qwen2.5-3B (Ollama) on an M1 (8 GB) hub; fallback Whisper medium + Qwen2.5-1.5B only if small's Tagalog is unusable (final pick logged in docs/NOTES.md), Silero VAD. Face match on the hub CPU uses OpenCV YuNet + SFace when OpenCV is installed (`POST /face/frame`, `POST /face/enroll/<person>`); if it is missing, enrollment returns `engine: "missing"` and writes nothing. Recorded-clip "where" uses OpenCV's HOG people detector on files in `brain/clips/media/`. Those room files are gitignored and are not in the clone (`brain/clips/media/README.md`). Live CCTV and voice ID stay cut (see `docs/sino/features.md`). No text-to-speech or voice cloning. Update this list to what was actually used.
- **Frameworks and tools:**
  - `fastapi`, `uvicorn[standard]`, and `python-multipart` (hub server and file uploads; install line in `docs/sino/architecture.md`).
  - `numpy` and `opencv-python-headless` (`brain/requirements.txt`) for the recorded-clip people detector and face match.
  - `ffmpeg` (records the hub mic for "listen now"; whisper-server also uses it to convert audio).
  - whisper.cpp `whisper-server` (serves Whisper small to the hub at `127.0.0.1:8080`).
  - macOS `afplay` (built in; plays the system sound `Glass.aiff` as the urgent chime on the hub speaker).
  - `curl` and `openssl` (macOS built-ins) and `mkcert` (local HTTPS certificates), used by `hub/start.sh` for the health light and the certificate check.
  - Google Chrome, headless (test only, not part of the app): `web/lola/reply.test.py` drives it over the DevTools protocol, offline on `127.0.0.1`, to test how Lola's screen plays family replies.
  - TODO, add the rest as each is introduced.
- **APIs and cloud services:** none at runtime. Test clips in brain/tests/audio/lola/ were generated before the event with ElevenLabs (synthetic, test input only; Sino itself runs offline).
- **Existing code and assets:** open-source libraries only. Demo data (`brain/seed.json` and the teammate-recorded replies and photos) is labeled as demo data. The default replies in `brain/media/` are real human recordings: Joy's four comfort replies and three meal clips, and the three "Sino ka?" lines by Troy, Joy, and Donita (no ElevenLabs, no text-to-speech). `/backstage` serves the Fontsource OFL files already in `web/backstage/fonts/` (Fredoka 500/600, DM Sans 400/500/700). Official mark: `assets/brand/sino-logo.png` (house roofline, green word, amber dot on the i), plus the trimmed web copies next to it. No new runtime dependency.
- **AI development tools:** Claude Code, Cursor, Grok Bot, Kiro (plus the Figma MCP if used). Kiro built Lola's iPad screen (`web/lola/`). Cursor placed the official mark in the READMEs, the favicons, the caregiver top bar, the backstage header, and the Lola idle corner. Claude Code wrote the Lola reply-playback browser test (`web/lola/reply.test.py`) and the tap-retry fix it found in `web/lola/lola.js`. Cursor (Grok) wired the caregiver's urgent reply through the hub to Lola's iPad.

## Key dates (PH time, UTC+8)

| When | What |
|---|---|
| Fri Oct 9, 12:30 PM | Online room opens (12:45 PM briefing) |
| Fri Oct 9, 1:00 PM | Challenge reveal. Build starts. |
| Fri Oct 9, 4:00 PM | Pivot lock (no idea changes after this) |
| Sat Oct 10, 3:30 AM | Sino MVP freeze (moved from 2:00 AM; see `docs/sino/mvp-plan.md`) |
| Sat Oct 10, 7:00 AM | Feature freeze (team rule) |
| Sat Oct 10, 8:30 AM | Our submit target (team rule) |
| Sat Oct 10, 10:00 AM | **Submissions close. Repo must be public. No extensions.** |
| Sat Oct 10, 12:00 PM | On-site at Cyberzone, SM Makati (required for finals) |

## Start here

- **[docs/INDEX.md](docs/INDEX.md)**: every doc, who owns it, when to read it, plus the glossary.
- **[AGENTS.md](AGENTS.md)**: rules for AI coding assistants working in this repo.

## Setup

The documented hub is Donita's M1 MacBook Air (8 GB). Long form (Homebrew, Whisper, Ollama, mkcert, hotspot, and the firewall) is [docs/sino/DONITA-SETUP.md](docs/sino/DONITA-SETUP.md). One-command start is `hub/start.sh` ([docs/sino/architecture.md](docs/sino/architecture.md), "Running the hub server"). Download models and packages before turning the firewall on.

### 1. Prerequisites

- Apple menu → About This Mac. The written-down hub is an M1 with 8 GB RAM. Free disk: at least 10 GB. Plug in the charger ([DONITA-SETUP.md](docs/sino/DONITA-SETUP.md) section 0).
- Homebrew, then the tools in section 1:

```bash
brew install git cmake ffmpeg mkcert node python
```

- `hub/start.sh` runs Python from `~/sino/hub-venv/bin/python` unless `PY` is set.

### 2. One-time model install

Follow [DONITA-SETUP.md](docs/sino/DONITA-SETUP.md) sections 2 and 3. Checklist:

- whisper.cpp cloned to `~/sino/whisper.cpp`, `models/ggml-small.bin` downloaded, and `./build/bin/whisper-server` built (section 2). Medium is only the fallback if small's Tagalog is unusable.
- Ollama installed from https://ollama.com, then `ollama pull qwen2.5:3b`. Pull `qwen2.5:1.5b` only for that same fallback (section 3).
- If `~/sino/whisper.cpp/models/ggml-silero-v6.2.0.bin` is missing, `hub/start.sh` still starts Whisper, without `--vad`.

### 3. Clone and Python packages

`brain/requirements.txt` is numpy and opencv-python-headless. The hub server also needs the packages named in [architecture.md](docs/sino/architecture.md) (the stub install line). Put them in the venv `hub/start.sh` uses:

```bash
git clone https://github.com/Troy-LL/appsolutely.git
cd appsolutely
python3 -m venv "$HOME/sino/hub-venv"
"$HOME/sino/hub-venv/bin/pip" install fastapi 'uvicorn[standard]' python-multipart
"$HOME/sino/hub-venv/bin/pip" install -r brain/requirements.txt
```

`/caregiver` is served only when `web/caregiver/dist` exists. Build it once ([web/caregiver/README.md](web/caregiver/README.md)):

```bash
cd web/caregiver
npm install
npm run build
cd ../..
```

`/lola` and `/backstage` are static files under `web/lola` and `web/backstage`. No extra build.

Room clips (`sala.mp4` and the other rooms) are not in this clone. They stay on the hub, gitignored, one file per room (`brain/clips/media/README.md`). iPhone `.mov` files often need the ffmpeg convert line in that file before OpenCV can read them.

### 4. HTTPS (iPad and iPhone)

The iPad mic needs the hub's mkcert URL. Section 4 of [DONITA-SETUP.md](docs/sino/DONITA-SETUP.md): `mkcert -install`. After the Mac is on the hotspot and `ipconfig getifaddr en0` prints the hub IP (section 5), write the cert where `hub/start.sh` looks:

```bash
mkdir -p "$HOME/sino/certs"
mkcert -cert-file "$HOME/sino/certs/hub.pem" -key-file "$HOME/sino/certs/hub-key.pem" <hub-ip> localhost
```

AirDrop `rootCA.pem` (`mkcert -CAROOT`) to the iPad and iPhone and trust it (Settings → General → About → Certificate Trust Settings). If the hub IP changes, run `mkcert` again and restart the hub. `hub/start.sh status` warns when the cert does not name the current IP.

### 5. Start

From the repo root:

```bash
hub/start.sh          # start what is not answering, warm qwen2.5:3b, print the health light
hub/start.sh status   # health light only
hub/start.sh stop     # stop only what this script started
```

Default port is 8000. Open the three screens on the hub URL it prints (`https://<hub-ip>:8000`):

| Screen | Path | On the device |
|---|---|---|
| Lola | `/lola/?feed=hub` | iPad. "Simulan" asks for the mic. `?mic=off` does not listen. |
| Caregiver | `/caregiver/?feed=hub` | iPhone, after the `dist` build above |
| Backstage | `/backstage/?feed=hub` | The Mac |

`/lola` and `/backstage` redirect to the trailing-slash paths. Plain `http://` on the LAN does not give Safari a microphone.

### 6. Practice feed

There is no `?feed=fake` switch. With no `feed` query, `/lola`, `/caregiver`, and `/backstage` play the scripted practice feed in `web/fake-feed` and show a FAKE label (`web/fake-feed/index.js`, `web/lola/README.md`, `web/backstage/README.md`). Add `?feed=hub` for the live hub socket.

### 7. Offline

`hub/start.sh` does not turn the firewall on or off. The LAN-only pf setup, the enable and disable commands, and the checks are [DONITA-SETUP.md](docs/sino/DONITA-SETUP.md) section 5. Section 6 is the no-Wi-Fi check: whisper-cli and Ollama must still answer. Do that only after the models and packages are already downloaded.
