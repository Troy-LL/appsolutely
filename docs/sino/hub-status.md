# Hub status (Donita's scope)

> Owner: Donita (hub). Status as of Sat Oct 10, 6:45 AM.
> Scope comes from the Owners table in [mvp-plan.md](mvp-plan.md) and from M1 (listening pipeline) and M6 (urgent chime) in [features.md](features.md). Problems in detail: [hub-problems.md](hub-problems.md). QA results: [qa/](qa/).

**Key:** ✅ done · 🟡 in progress · ❌ not done · ⚠️ at risk · ✂️ cut

## At a glance

| Task | What it is | Status |
|---|---|---|
| D1 | Network + HTTPS (offline) | ✅ Offline test passed. ❌ Caregiver iPhone untested |
| D2 | Whisper (speech to text) | ✅ Decided: keep **small** (PR #41) |
| D3 | Ollama + Qwen (decision model) | ✅ Kept warm; answers the same way every time (PR #46) |
| D4 | Listening pipeline (M1) | ✅ "Listen now" (PR #26). 🟡 Always-on listening being built |
| D5 | Questions + storage | ✅ (PR #23) |
| D6 | `start.sh` + health light + urgent chime (M6) | ✅ (PR #31) |
| D7, D8 | CCTV detector, voice ID | ✂️ Cut |

---

## D1: Network + HTTPS

- ✅ iPhone hotspot + LAN-only firewall + HTTPS certificate for the hub (`172.20.10.2`). The iPad loads pages with no warning (2:00 AM).
- ✅ **Offline test re-run passed** (~6:15 AM, reported by Donita): firewall on, internet blocked, hub still answers.
- ❌ **Caregiver iPhone not tested.** Troy's phone wasn't available. Install and trust `rootCA.pem`, then open `https://172.20.10.2:8000/caregiver`.
- ⚠️ **Firewall was off again at 6:33 AM.** Turn it on before every rehearsal: `sudo pfctl -f /etc/pf.sino.conf -e`
- ⚠️ **Hotspot is Donita's iPhone**, not Troy's as the docs say. Use the same phone for rehearsals and the demo.

## D2: Whisper

- ✅ Server running: model **small**, Tagalog, voice detection on, only reachable from the hub laptop.
- ✅ **Decided: keep small** (PR #41). Medium got more words right but **not more decisions right** (27/32 both), **missed "Saklolo"** (heard "Suck, Lolo."), and was several times slower (median 7.23 s vs 1.31 s on the test clips, with memory very tight).

## D3: Ollama + Qwen

- ✅ `qwen2.5:3b` stays loaded; a **keep-warm** request runs every 60 s (PR #31).
- ✅ **Temperature 0** (PR #46): the same line gets the same decision every time (36/36 lines in 5 runs, was 30/36).
- ⚠️ One answer in 180 took **4.07 s** and fell back to the caregiver (QA D-14). Keep other apps closed; memory was 20 to 24% free at 6:20 to 6:33 AM.

## D4: Listening pipeline (M1)

- ✅ **"Listen now"**: hub mic → Whisper → junk filter → decision (PR #26). Mic test 3 of 3.
- ✅ **Junk filter**: too quiet, likely no speech, known TV/junk lines.
- ✅ **Throttle**: one decision at a time; older lines are dropped, but **a line with an urgent word is never dropped** (PR #46).
- ✅ Typed question, WebSocket events, recordings deleted right after use.
- 🟡 **Always-on listening** (branch `donita/always-listen`, not merged; off unless switched on). Troy decides if it ships.

## D5: Questions + storage

- ✅ Save a question with its recording and photo, serve them at `/media` (PR #23). Tested on the iPad.

## D6: `start.sh` + health light + urgent chime (M6)

- ✅ `hub/start.sh` starts Whisper, Ollama, the hub server, and the keep-warm loop; `status` prints the health light; `stop` stops what it started (PR #31).
- ✅ **Urgent chime** from the hub speaker (`hub/chime.py`).
- ✅ **Health light** with a real OFFLINE check.

## Other work

- ✅ [hub-problems.md](hub-problems.md) (PR #24), QA fixes (PR #46), medium retest (PR #41), Taglish recordings (PR #39).
- ✅ [`.env.example`](../../.env.example): every hub setting, names only.
- ✅ [qa/](qa/): QA sheet, test scripts, and raw results from the hub.

---

## What's left, in order

1. **Restart the hub on the latest `main`.** At 6:33 AM it was still running 4:23 AM code, so `/lola`, `/caregiver`, and `/backstage` returned "not found":
   `git pull && hub/start.sh stop && hub/start.sh`
2. **Firewall on** for all three rehearsals, on the same hotspot.
3. **Caregiver iPhone** test when Troy's phone is free.
4. **Always-on listening**, only if Troy wants it.
5. Tell Troy: **OpenCV and the face-match models aren't installed on the hub**, so "Sino ka?" with the camera and "Nasaan si Lola?" won't run there.
