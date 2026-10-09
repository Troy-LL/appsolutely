# Synthetic Lola test clips

These 32 clips are synthetic. They were made with ElevenLabs text-to-speech before the event and are only test input for Whisper and the T5 pass/fail runner (`brain/tests/run_t5.py`). They stand in for Lola's side of the conversation until real recordings exist.

- Lola's lines use the ElevenLabs premade voice "Lily" (the most mature female voice on the account; there was no elderly female voice). Model `eleven_v3`, language `fil`, a `[tired]` delivery tag, stability 0.5.
- TV lines use the premade broadcaster voice "Daniel" so they sound like a show, not Lola.
- Format: 16 kHz, mono, 16-bit PCM WAV, the format whisper.cpp expects.
- `manifest.json` lists each clip with its text, category, expected action, and the seed question id for comfort lines. Text and expected action come from `brain/tests/cases.json`, except `v01` to `v03`, which are new variants checked against `decide()` in stub mode.

Limits:

- These voices are cleaner than real elderly speech. Whisper will do better on them than on Lola. Mix them with real clips recorded by Donita and Troy before trusting any Whisper result.
- None of this is family audio. Joy's replies and Troy's "Sino ka?" reply stay real recordings. No voice cloning.
- Sino stays offline. ElevenLabs was used once, on a laptop, to make these files. Nothing in the product calls a cloud service at runtime.
