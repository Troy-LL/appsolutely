# Hub status (Donita's scope)

> Owner: Donita (hub). Status as of Sat Oct 10, 3:54 AM.
> Scope comes from the Owners table in [mvp-plan.md](mvp-plan.md) and from M1 (listening pipeline) and M6 (urgent chime) in [features.md](features.md). Problems in detail: [hub-problems.md](hub-problems.md).

**Key:** ✅ done · 🟡 in progress · ❌ not done · ⚠️ at risk or failing · ✂️ cut

## At a glance

| Task | What it is | Status |
|---|---|---|
| D1 | Network + HTTPS | 🟢 Almost: caregiver iPhone and firewall left |
| D2 | Whisper (speech to text) + model timing | 🟡 Running; small vs medium not decided |
| D3 | Ollama + Qwen (decision model) | ✅ Done; watch memory |
| D4 | Listening pipeline (M1) | 🟡 "Listen now" done; always-on listening not built |
| D5 | Questions + storage | ✅ Done |
| D6 | `start.sh` + health light + urgent chime (M6) | 🟡 Being built now |
| D7, D8 | CCTV detector, voice ID | ✂️ Cut |

---

## D1: Network + HTTPS

| ✅ Done | ❌ Not done / ⚠️ at risk |
|---|---|
| Tested Internet Sharing with no internet. It **failed**, so the plan switched to an iPhone hotspot + firewall | ❌ **Caregiver iPhone** not tested. Install and trust `rootCA.pem`, then open `https://172.20.10.2:8000/questions` |
| Firewall rules written and fixed so the iPad gets the hub's replies (PR #14) | ⚠️ **Firewall was off** when last checked (2:14 AM). It must be on for the no-internet rehearsals: `sudo pfctl -f /etc/pf.sino.conf -e` |
| HTTPS certificate for the hub (`172.20.10.2`); the iPad loads pages with no warning | ⚠️ **Which phone is the hotspot** isn't locked (tested on Donita's, the docs say Troy's). If it changes, the hub's address and certificate must be redone |

## D2: Whisper + model timing

| ✅ Done | ❌ Not done / ⚠️ failing |
|---|---|
| Whisper server running: model small, Tagalog, voice detection on, only reachable from the hub laptop (`127.0.0.1:8080`) | ❌ **Small vs medium not decided** |
| Timed on a Tagalog clip: small **0.55 s**, medium **1.52 s** (not counting model loading); logged | ⚠️ **Small misheard both of Donita's real recordings**; medium got 1 of 2 right |
| Silence returns no text (voice detection works) | ⚠️ Small misheard **4 of 12** known questions on the test recordings |

## D3: Ollama + Qwen

| ✅ Done | ⚠️ At risk |
|---|---|
| `qwen2.5:3b` loaded and kept in memory; answers in about **1 to 2 s** | ⚠️ The first request after a quiet period can still go over the **4 s** limit. Needs the keep-warm ping (D6) |
| Works with the firewall on | ⚠️ Memory is tight on 8 GB. Keep other apps closed during rehearsals and the demo |

## D4: Listening pipeline (M1)

| ✅ Done | ❌ Not done |
|---|---|
| **"Listen now"**: hub mic → Whisper → junk filter → decision (PR #26, merged 3:52 AM). Mic test passed **3 of 3** (silence dropped, "Nasaan si Nanay?" got comfort, "Thank you for watching" dropped) | ❌ **Always-on listening** (Silero voice detection watching the mic all the time). For now the hub only listens when "listen now" is pressed |
| **Junk filter**: drops clips that are too quiet, likely no speech, or known TV/junk lines | |
| **Throttle**: one decision at a time; older clips are dropped (`brain/server.py`) | |
| **Typed question** and **WebSocket events** (`POST /listen`, `/ws`) | |
| **Recordings deleted** right after use (privacy rule) | |

## D5: Questions + storage

| ✅ Done |
|---|
| Saves a new question with its recording and photo, and serves them at `/media` (PR #23, merged 3:29 AM). Tested on the iPad: the recording played and the photo showed |

## D6: `start.sh` + health light + urgent chime (M6)

| ✅ Done | 🟡 Being built now (branch `donita/start-sh`) |
|---|---|
| The **health check** exists in the hub server: Whisper, Ollama, server, mic, and a **real OFFLINE check** (tries to reach the internet) | 🟡 **`start.sh`**: starts Whisper, Ollama and the hub server so anyone can restart the hub |
| | 🟡 **Urgent chime** from the hub speaker ([hub-chime.md](hub-chime.md)) |
| | 🟡 **Keep-warm ping**: a tiny request to Qwen about once a minute so it stays fast |

## D7, D8

✂️ **Cut.** The CCTV detector and voice ID won't be built.

## Other work

- ✅ [hub-problems.md](hub-problems.md): problems found while testing (PR #24)
- ✅ Hub setup results logged in [../NOTES.md](../NOTES.md)

---

## What's left, in order

1. **Finish D6**: `start.sh`, urgent chime, keep-warm ping (in progress).
2. **Turn the firewall on** and **test the caregiver iPhone** (D1).
3. **Record more voices** and decide **Whisper small vs medium** with the team (D2). See the test plan in [hub-problems.md](hub-problems.md).
4. **Always-on listening** (D4), only if there's time. "Listen now" already covers the demo.
