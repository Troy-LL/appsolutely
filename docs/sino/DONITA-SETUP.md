# Sino: M1 (8 GB) hub setup (Donita)

> Part of the Sino docs. Overview: [README.md](README.md). Where this fits: [architecture.md](architecture.md). The numbers you write down here go into `docs/NOTES.md` (Model smoke test) and replace the "to verify" items in [architecture.md](architecture.md#to-verify-at-smoke-test).

You can do this by hand, or paste it into an AI coding agent (Cursor or Claude Code) and tell it: "Run every step, verify each check, report anything that fails."

**Goal:** the M1 (8 GB) MacBook Air can transcribe Tagalog speech and run the decision model **fully offline**.
**Time:** about 30–45 min, mostly downloads (several GB; TODO: exact size). Do it on good Wi-Fi with the charger plugged in.

---

## 0. Check the machine
- Apple menu → About This Mac. **Note the RAM** (Donita's hub: 8 GB) and send it to the GC.
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
# optional, only for the fallback if small's Tagalog is unusable:
# sh ./models/download-ggml-model.sh medium
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
# only if small's transcript is unusable and you downloaded medium:
# time ./build/bin/whisper-cli -m models/ggml-medium.bin -l tl -f test.wav
```
Make the clip about **4 s** long. **Write down** the transcript and time. Rule for this 8 GB hub ([architecture.md](architecture.md#speech-model-selection-by-1130-pm)): small + qwen2.5:3b is the default; medium + qwen2.5:1.5b only if small's Tagalog is unusable. Medium + 3B and large-v3-turbo are out.

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
ollama pull qwen2.5:1.5b   # fallback only (with Whisper medium)
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

## 5. Network (D1)
macOS Internet Sharing doesn't work here: it needs an active upstream, and `bridge100` never appeared (Sat 1:20 AM). **Primary: Troy's iPhone 15 Personal Hotspot + a LAN-only firewall on the hub.** Backups, in order: a spare router or pocket Wi-Fi with no WAN / SIM data off; iPhone USB into the M1 + Internet Sharing from "iPhone USB" to Wi-Fi + the same firewall; venue Wi-Fi + the same firewall ([architecture.md](architecture.md#network)).

1. iPhone: Settings → Personal Hotspot → Allow Others to Join ON, **Maximize Compatibility ON**.
2. Join the hotspot from the M1, the iPad, and the caregiver phone.
3. On the M1: `ipconfig getifaddr en0` (expect `172.20.10.x`). That's the hub IP.
4. **Download every model and package BEFORE turning the firewall on** (Whisper, `ollama pull`, `npm install`, `pip install`).
5. Create the anchor `/etc/pf.anchors/sino` (with `sudo`):
```
pass out quick on lo0 all
pass out quick to { 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16, 224.0.0.0/4 }
pass out quick proto udp to any port { 67, 68, 5353 }
block drop out quick all
```
6. Create `/etc/pf.sino.conf` that loads it:
```
anchor "sino"
load anchor "sino" from "/etc/pf.anchors/sino"
```
7. Enable / disable (test before relying on it):
```bash
sudo pfctl -f /etc/pf.sino.conf -e   # enable
sudo pfctl -d                        # disable (do this before downloading anything)
```
8. Prove it:
```bash
curl -m 3 https://google.com   # must FAIL (timeout)
ping -c 3 <ipad-ip>            # must work
```
9. `mkcert <hub-ip> localhost`, point the server at the two files it makes, and install + trust `rootCA.pem` on the iPad and iPhone (Settings → General → About → Certificate Trust Settings). If the hub IP changes, regenerate.
10. Keep the iPhone on the Personal Hotspot screen so it doesn't sleep and drop the network.

All three 7 AM no-internet rehearsals use this same network.

## 6. Offline test (important)
Turn **Wi-Fi off**, then rerun Check 2 (whisper-cli on `test.wav`) and the Ollama check.
Both must still work with no internet. That's the whole point of Sino.

## 7. Bring to the café
- The M1 hub plus its charger
- The A16 iPad plus its charger
- A USB-C cable (to connect the iPad to the hub as a backup)
- Earphones

## Report to the GC
- RAM: 8 GB (M1, confirmed)
- whisper small: transcript "__", time __ s
- whisper medium (only if small was unusable): transcript "__", time __ s
- qwen2.5:3b: output __, time __ s
- Network used (1 iPhone hotspot + firewall / 2 router / 3 iPhone USB + Internet Sharing / 4 venue + firewall): __, hub IP: __, `curl` blocked: yes / no
- Offline test: pass / fail
- Anything that broke, with the error message

---
Notes for an AI agent running this: don't change system settings beyond the installs above. Don't commit models, certificates, or recordings to the repo. If a step fails, stop and report the exact error. Never invent a timing or transcript; if a step didn't run, write "not run".
