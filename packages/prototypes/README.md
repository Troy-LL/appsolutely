# Appsolutely

Team repo for the **AppBuildersPH Hackathon 2026** (Team Appsolutely: Troy, Ayen, Donita, Viviene). It holds the planning docs (event facts, roles, philosophy, playbook, idea filter, submission checklist) and the Sino spec in `docs/sino/`. Per the rules, the project is built from scratch after the challenge reveal at 1:00 PM Fri Oct 9.

## Our project: Sino

Sino is a small home hub that answers a lola's repeated questions in her family's own recorded voice, decides when to comfort her, get the caregiver, or raise an alarm, and keeps working with no internet. An always-on mic in a home must never stream anywhere, so speech recognition (whisper.cpp) and the decision model (Qwen2.5 in Ollama) run on a home device. Spec: **[docs/sino/README.md](docs/sino/README.md)**.

## Disclosures (running list, updated as we build)

- **Models:** Whisper small via whisper.cpp + Qwen2.5-3B (Ollama) on an M1 (8 GB) hub; fallback Whisper medium + Qwen2.5-1.5B only if small's Tagalog is unusable (final pick logged in docs/NOTES.md), Silero VAD. Planned after the freeze (add-on, not built yet): OpenCV YuNet + SFace for face match on the hub CPU; update this line if it ships. No person-detection or speaker models: CCTV and voice ID are cut (see `docs/sino/features.md`). No text-to-speech or voice cloning. Update this list to what was actually used.
- **Frameworks and tools:**
  - `python-multipart` (file uploads on the hub).
  - `ffmpeg` (records the hub mic for "listen now"; whisper-server also uses it to convert audio).
  - whisper.cpp `whisper-server` (serves Whisper small to the hub at `127.0.0.1:8080`).
  - macOS `afplay` (built in; plays the system sound `Glass.aiff` as the urgent chime on the hub speaker).
  - `curl` and `openssl` (macOS built-ins) and `mkcert` (local HTTPS certificates), used by `hub/start.sh` for the health light and the certificate check.
  - React 18, Vite 5 and TypeScript 5 (`web/caregiver`, the caregiver phone screen).
  - TODO, add the rest as each is introduced.
- **APIs and cloud services:** none at runtime. Test clips in brain/tests/audio/lola/ were generated before the event with ElevenLabs (synthetic, test input only; Sino itself runs offline).
- **Existing code and assets:** open-source libraries only. Fonts: Fredoka and DM Sans (SIL Open Font License, Fontsource 5.3.0), bundled in `web/caregiver/src/assets/fonts`. Demo data (`brain/seed.json` and the teammate-recorded replies and photos) is labeled as demo data.
- **AI development tools:** Claude Code, Cursor, Grok Bot (plus the Figma MCP if used). Claude (claude.ai chat) drafted the caregiver screen design and the `web/caregiver` code.

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

## Setup (to be written after 1 PM)

How to run the app goes here once it exists. Judges must be able to recreate it from this section.
