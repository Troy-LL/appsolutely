# Appsolutely

Team repo for the **AppBuildersPH Hackathon 2026** (Team Appsolutely: Troy, Ayen, Donita, Viviene). It holds the planning docs (event facts, roles, philosophy, playbook, idea filter, submission checklist) and the Sino spec in `docs/sino/`. Per the rules, the project is built from scratch after the challenge reveal at 1:00 PM Fri Oct 9.

## Our project: Sino

Sino is a small home hub that answers a lola's repeated questions in her family's own recorded voice, decides when to comfort her, get the caregiver, or raise an alarm, and keeps working with no internet. An always-on mic in a home must never stream anywhere, so speech recognition (whisper.cpp) and the decision model (Qwen2.5 in Ollama) run on a home device. Spec: **[docs/sino/README.md](docs/sino/README.md)**.

## Disclosures (running list, updated as we build)

- **Models:** Whisper via whisper.cpp (small, medium, or large-v3-turbo; final pick logged in docs/NOTES.md), Qwen2.5-3B or Qwen2.5-1.5B (Ollama), Silero VAD. Added only if an add-on ships: face (face-api.js or MobileFaceNet ONNX), person detection (MediaPipe or YOLO), speaker (sherpa-onnx or SpeechBrain ECAPA). Update this list to what was actually used.
- **Frameworks and tools:** TODO, add as each is introduced.
- **APIs and cloud services:** none at runtime.
- **Existing code and assets:** open-source libraries only. Demo data (`seed.json`, teammate-recorded replies and photos, and the recorded CCTV clip if used) is labeled as demo data.
- **AI development tools:** Claude Code, Cursor, Grok Bot (plus the Figma MCP if used).

## Key dates (PH time, UTC+8)

| When | What |
|---|---|
| Fri Oct 9, 12:30 PM | Online room opens (12:45 PM briefing) |
| Fri Oct 9, 1:00 PM | Challenge reveal. Build starts. |
| Fri Oct 9, 4:00 PM | Pivot lock (no idea changes after this) |
| Sat Oct 10, 7:00 AM | Feature freeze (team rule) |
| Sat Oct 10, 8:30 AM | Our submit target (team rule) |
| Sat Oct 10, 10:00 AM | **Submissions close. Repo must be public. No extensions.** |
| Sat Oct 10, 12:00 PM | On-site at Cyberzone, SM Makati (required for finals) |

## Start here

- **[docs/INDEX.md](docs/INDEX.md)**: every doc, who owns it, when to read it, plus the glossary.
- **[AGENTS.md](AGENTS.md)**: rules for AI coding assistants working in this repo.

## Setup (to be written after 1 PM)

How to run the app goes here once it exists. Judges must be able to recreate it from this section.
