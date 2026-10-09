# Sino: M2 hub setup (Donita)

> Part of the Sino docs. Overview: [README.md](README.md). Where this fits: [architecture.md](architecture.md). The numbers you write down here go into `docs/NOTES.md` (Model smoke test) and replace the "to verify" items in [architecture.md](architecture.md#to-verify-at-smoke-test).

You can do this by hand, or paste it into an AI coding agent (Cursor or Claude Code) and tell it: "Run every step, verify each check, report anything that fails."

**Goal:** the M2 MacBook can transcribe Tagalog speech and run the decision model **fully offline**.
**Time:** about 30–45 min, mostly downloads (several GB; TODO: exact size). Do it on good Wi-Fi with the charger plugged in.

---

## 0. Check the machine
- Apple menu → About This Mac. **Note the RAM (8 / 16 / 24 GB)** and send it to the GC.
- Free disk space: at least **10 GB**.
- Plug in the charger. Close other heavy apps.

## 1. Homebrew + tools
If `brew --version` fails, install Homebrew first:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
(Follow the "Next steps" lines it prints to add brew to your PATH.)

Then:
```bash
brew install git cmake ffmpeg mkcert node python
```
**Check:** `ffmpeg -version`, `cmake --version`, `mkcert -help`, and `node -v` all print something.

## 2. Speech model (whisper.cpp)
```bash
mkdir -p ~/sino && cd ~/sino
git clone https://github.com/ggml-org/whisper.cpp.git
cd whisper.cpp
sh ./models/download-ggml-model.sh small
sh ./models/download-ggml-model.sh medium
sh ./models/download-ggml-model.sh large-v3-turbo
cmake -B build
cmake --build build -j --config Release
```
**Check 1 (transcribes the sample):**
```bash
./build/bin/whisper-cli -m models/ggml-small.bin -f samples/jfk.wav
```
You should see the JFK sentence printed as text.

**Check 2 (Tagalog):** record a 3–5 s voice memo of yourself saying "Nasaan si Nanay?", export it as `test.m4a` into `~/sino/whisper.cpp`, then:
```bash
ffmpeg -y -i test.m4a -ar 16000 -ac 1 -c:a pcm_s16le test.wav
time ./build/bin/whisper-cli -m models/ggml-small.bin -l tl -f test.wav
time ./build/bin/whisper-cli -m models/ggml-medium.bin -l tl -f test.wav
time ./build/bin/whisper-cli -m models/ggml-large-v3-turbo.bin -l tl -f test.wav
```
Make the clip about **4 s** long. **Write down** the transcript and time for all three. Rule ([architecture.md](architecture.md#speech-model-selection-by-1130-pm)): use medium if it's under about 1.5 s. With 16 GB RAM: medium + qwen2.5:3b. With 8 GB: small + qwen2.5:3b, or medium + qwen2.5:1.5b.

**Check 3 (server starts):**
```bash
./build/bin/whisper-server -m models/ggml-small.bin -l tl --host 0.0.0.0 --port 8080 --convert
```
Leave it running and open http://localhost:8080 in a browser; a page should load. Press Ctrl+C to stop.

## 3. Decision model (Ollama)
1. Download and install the Ollama app from https://ollama.com and open it once.
2. Then:
```bash
ollama pull qwen2.5:3b
ollama pull qwen2.5:1.5b
```
**Check:**
```bash
time ollama run qwen2.5:3b 'Reply only with JSON {"action":"comfort|caregiver|urgent|silent","reason":"..."}. Lola said: "Masakit ang dibdib ko"'
```
It should reply with JSON, ideally `"urgent"`. **Write down** how long it took.

## 4. HTTPS prep (for recording replies in quick setup)
```bash
mkcert -install
mkcert -CAROOT
```
Note the folder it prints. We'll AirDrop `rootCA.pem` from there to the iPad and iPhone at the café. Don't generate the site certificate yet, because we need the hub's network IP first.

## 5. Network test: Internet Sharing with no upstream
Tonight's checkpoint (11:15 PM). Turn on System Settings → General → Sharing → Internet Sharing, sharing to Wi-Fi, with **no** internet connection on the Mac. Check that the iPad and iPhone can join the network and open a page served by the M2. If macOS won't share with no upstream, use an Android hotspot with mobile data off, or a travel router. Write down which one works.

## 6. Offline test (important)
Turn **Wi-Fi off**, then rerun Check 2 (whisper-cli on `test.wav`) and the Ollama check.
Both must still work with no internet. That's the whole point of Sino.

## 7. Bring to the café
- The M2 plus its charger
- The A16 iPad plus its charger
- A USB-C cable (to connect the iPad to the M2 as a backup)
- Earphones

## Report to the GC
- RAM: __ GB
- whisper small: transcript "__", time __ s
- whisper medium: transcript "__", time __ s
- whisper large-v3-turbo: transcript "__", time __ s
- qwen2.5:3b: output __, time __ s
- Internet Sharing with no upstream: works / fails (fallback used: __)
- Offline test: pass / fail
- Anything that broke, with the error message

---
Notes for an AI agent running this: don't change system settings beyond the installs above. Don't commit models, certificates, or recordings to the repo. If a step fails, stop and report the exact error. Never invent a timing or transcript; if a step didn't run, write "not run".
