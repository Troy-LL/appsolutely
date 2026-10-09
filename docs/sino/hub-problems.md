# Hub problems

> Owner: Donita (hub). Last updated: Sat Oct 10, 3:40 AM.
> Every number here was measured on the hub laptop (MacBook Air M1, 8 GB memory). Real results also go in [../NOTES.md](../NOTES.md).

## Words used

- **Whisper**: turns speech into text. Comes in sizes: **small** (faster, less accurate) and **medium** (slower, usually more accurate).
- **Qwen**: the decision model. When the fixed rules can't decide, it picks **comfort** (play the family's reply to Lola), **caregiver** (card on the caregiver's phone), **urgent** (alarm), or **silent** (do nothing).
- **Fixed rules**: Troy's checks that run before Qwen. Urgent words always alarm; medication always goes to the caregiver; known questions get comfort.
- **Test clips**: 32 computer-generated "Lola" recordings in `brain/tests/audio/lola/` (Troy, PR #18). Cleaner than a real elderly voice.

## At a glance

| # | Problem | How bad | Who fixes it | Status |
|---|---|---|---|---|
| 1 | Whisper mishears Tagalog questions | High | Donita + team | ❌ Open |
| 2 | Misheard lines can go **silent** or raise a **false alarm** | **Very high** | Troy | Fixed in code, pending hub retest |
| 3 | Qwen sometimes takes longer than its 4-second limit | Medium | Donita | 🟡 Better |
| 4 | Unclear if Whisper medium + Qwen 3B fit in 8 GB | Medium | Team | ❌ Open |
| 5 | Network: caregiver iPhone not tested, firewall off | Medium | Donita | ❌ Open |
| 6 | ElevenLabs missing from the README disclosures | Low (but a rule) | Troy | Fixed |

---

## 1. Whisper mishears Tagalog questions

**What happened:** Donita said "Nasaan si Nanay?" twice on the hub mic.

| Recording | Whisper small wrote | Whisper medium wrote |
|---|---|---|
| 1st | "nasaanzi na nai." ❌ | "Nasaan si nanay." ✅ |
| 2nd | "I'm Zina Nait." ❌ | "Masa, I was in our night." ❌ |

On the 32 test clips, Whisper small misheard **4 of 12** known questions, for example "Gusto ko nang umuwi" → "Gusto ko na mo mo wei."

**Why it matters:** if the words come out wrong, the hub doesn't recognize the question, and Lola doesn't hear her family's reply.

**Good news:** Troy's fix (PR #21) now recognizes the 1st recording's mistake, so it gets comfort.

**What to do:** retest with Whisper medium, using more recordings and voices (see the test plan below). One voice and two recordings isn't proof.

## 2. Misheard lines can go silent or raise a false alarm

The worst results from the 32 test clips (Whisper small + Qwen, Sat 3:31 AM):

| Lola said | Whisper wrote | Hub chose | Should be |
|---|---|---|---|
| "Hirap huminga" (hard to breathe) | "Herap huminga." | **silent** 🚨 | urgent |
| "Sa teleserye, sino ka ba talaga?" (TV) | "Sateleserye si no kabatalaga." | **urgent** 🔔 | silent |
| "Who is this?" | "Who is this?" | **urgent** 🔔 | caregiver |
| "Asan ka, Joy?" | "A Thunkah Joy." | **silent** | comfort |
| "Gusto ko nang umuwi" | "Gusto ko na mo mo wei." | **silent** | comfort |

**Why it matters:**
- **Silent** means nobody responds. For "hard to breathe", that's a **missed emergency**.
- **False alarms** scare the family and teach them to ignore the alarm.

**Score against the team's pass/fail gate** ([mvp-plan.md](mvp-plan.md)):

| | Result | Gate |
|---|---|---|
| Urgent | 8 of 9 | all |
| Comfort | 8 of 12 | at least 8 of 10 |
| TV stays silent | 4 of 5 (1 false alarm) | no false alarms |

It doesn't pass yet. One run per clip, computer voices, and a quick script rather than Troy's official runner.

**Status:** fixed in code (Sat ~3:45 AM), pending a hub retest. Urgent is rules-only, so a model urgent becomes caregiver. The model may stay silent only at confidence ≥ 0.9, and only when the line has no breathing, pain, or fall word. "Herap huminga.", "hirap humenga", "di maka hinga", and "I can't breathe" alarm. "Sateleserye si no kabatalaga." stays silent. "Who is this?", "A Thunkah Joy.", and "Gusto ko na mo mo wei." go to the caregiver instead of silent.

**What to do:** retest on the hub and log the numbers in NOTES:

```bash
SINO_MODEL=ollama WHISPER_BIN=... WHISPER_MODEL=.../ggml-medium-q5_0.bin python3 brain/tests/run_t5.py --audio --out docs/sino/t5-hub-medium.jsonl
```

## 3. Qwen sometimes takes longer than its 4-second limit

**What happened:** when the laptop ran low on memory, 2 of 3 requests took over 4 seconds and fell back to caregiver ("model unavailable").

**Fix so far:** we closed Chrome tabs and stopped another project's website (resume-classifier, 2,881 MB). After that, Qwen answered in **1.06 to 1.92 s** with no timeouts. The first request after a quiet break can still time out (happened once at 3:28 AM).

**What to do:**
- Keep other apps closed during rehearsals and the demo.
- Add a "keep-warm" ping to the hub (D6): a tiny request to Qwen about once a minute so it stays ready.

## 4. Do Whisper medium + Qwen 3B fit in 8 GB?

**The plan says no:** use medium only with the smaller Qwen 1.5B ([architecture.md](architecture.md)).

**What we measured:** both loaded together and fit, with 39% and 53% of memory still free. Those were short tests, not a full demo run.

**Why it matters:**
- If medium + 3B fits, we keep the better decision model.
- Qwen 1.5B gave different answers on the same chest-pain line (silent once, caregiver once).

**What to do:** check memory during the medium retest, then decide as a team.

## 5. Network checks left (D1)

- ❌ **Caregiver iPhone not tested.** Install and trust `rootCA.pem`, then open `https://172.20.10.2:8000/questions`.
- ⚠️ **Firewall was off** at 2:14 AM. Turn it on before rehearsals: `sudo pfctl -f /etc/pf.sino.conf -e`
- ⚠️ **Which phone is the hotspot?** It was tested on Donita's iPhone, but the docs say Troy's. If it changes, the hub's address and certificate must be redone.

## 6. ElevenLabs missing from the README disclosures

Troy used ElevenLabs (a cloud text-to-speech service) to make the test clips. The repo rules ([../../AGENTS.md](../../AGENTS.md)) say every service and AI tool must be listed in the README. Listed in the root README disclosures (Sat ~3:45 AM).

---

## Test plan: retest with Whisper medium

1. **Record** each known question on the hub mic, in as many voices as possible: Nasaan si Nanay? · Nasaan si Joy? · Sino ka? · Nasaan ako? · Gusto ko nang umuwi
   On the hub laptop, one command records and checks both models:
   ```bash
   ~/sino/try-recording.sh nanay-donita-2
   ```
2. **Write down** for each recording: what small wrote, what medium wrote, and the hub's decision.
3. **Check memory** while medium and Qwen are loaded: `memory_pressure | tail -1`
4. **Decide as a team.** TODO (team): agree first how many recordings small must get right to count as "usable".

## Solved

- The hub is an **M1 with 8 GB**, not an M2: docs fixed.
- Internet Sharing wouldn't work offline: switched to iPhone hotspot + firewall.
- Firewall blocked replies to the iPad: rules fixed (2:00 AM).
- Qwen calls chest pain "caregiver": fixed rules catch urgent words first.
- Model download kept restarting: resumed and verified.
- Voice detection wasn't on: Whisper server restarted with it (2:47 AM).
- Old test page on port 8443: stopped (3:26 AM).
- The 1st "nasaanzi na nai." went silent: Troy's PR #21 fixed it.
- Saving new questions (D5, PR #23): merged by Troy (3:29 AM).
