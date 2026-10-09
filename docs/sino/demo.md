# Sino: demo script

Format (from [../00-event.md](../00-event.md)): 5-minute pitch with a live demo, then 3 minutes of judge Q&A. Max 4 to 5 slides. Working product over slides. End with the People's Choice "scan to vote" ask.

## Setup before going on stage

- Hub (M1, 8 GB) running from `start.sh`, seed loaded, health light green.
- iPad on `/lola`, "Simulan" already tapped. iPhone on `/caregiver`, open on the hub's network (no push without internet). Backstage on the projected screen.
- The hub's LAN-only firewall is on and the OFFLINE badge is visible (it comes from a real outbound check failing). On rung 1 the house network is Troy's iPhone hotspot, which has cellular, so the claim is "the hub is firewalled to the house network", not "every device is offline". The iPhone cannot go to airplane mode, because that turns the hotspot off ([architecture.md](architecture.md#network)).
- Clips ready: the 20 s teleserye clip (TODO below). No CCTV clip and no voice ID: both are cut.
- Recordings loaded: Joy's four replies and Troy's "Sino ka?" line (TODO: not recorded yet as of Sat 2:00 AM).
- Hub volume up for the urgent chime.

## Run of show

| Time | What happens | Screen |
|---|---|---|
| 0:00–0:30 | Opener (below) | Lola's iPad |
| 0:30–1:00 | Show there's no internet. Point at the OFFLINE badge: "the hub is firewalled to the house network." If the hub is unplugged, say it runs on battery (only if it really is unplugged) | Backstage |
| 1:00–1:50 | **Live quick setup.** Ask "Nasaan yung aso?" (not in the seed) → quiet yellow card on `/caregiver` → on the iPhone, `/setup` adds the question, two phrasings, a held recording, and a photo → ask again → the family voice answers on the iPad. "Nasaan si Joy?" stays in the seed and is not added live | iPhone `/setup` + `/caregiver` → iPad |
| 1:50–2:20 | "Sino ka?" Lola asks who Troy is. It is a known question, so the iPad shows Troy's photo and plays the line he recorded in setup. Then Troy talks to "Lola" in person. No face match and no call | iPad + Troy |
| 2:20–3:30 | **TV test, its own beat.** Play the 20 s teleserye clip: a full dialogue that contains "nasaan si nanay" mid-sentence, not as the whole line. Sino stays silent. `/backstage` shows a dropped row and `TV lines ignored: N` ticks. Then Lola asks "Nasaan si Nanay?" plainly → the comfort reply and photo. The row shows transcript → rule or model → action, confidence, reason → ms | Backstage + iPad |
| 3:30–4:00 | "Masakit dibdib ko" → the hub chimes ([hub-chime.md](hub-chime.md)) and a red card appears on the phone. `/lola` stays calm and never red. A medication question goes to the caregiver | Hub + iPhone |
| 4:00–5:00 | Why local + close + scan-to-vote | Slide |

The "Nasaan si Lola?" camera view, the door alert, voice ID, and the live call are cut. They go on the "next steps" slide. Face match is one optional beat below, only if built after the freeze. If Ask Sino about Lola is wired after the freeze, show "Kamusta si Lola?" on `/caregiver` in 15 s at the 3:30 mark (TODO: only if wired).

**Pitch order:** lead with the always-on mic privacy line and the four differentiators in [README.md](README.md#what-makes-it-different) (real family voices, silence as a decision, family-written replies, visible decisions). The offline/brownout angle is supporting proof, not the hook.

### Opener

> "Nasaan si Nanay?" If you've cared for a lola with dementia, you've heard a question like this many times in one afternoon. Every time, someone has to choose: tell her the truth again and watch her hurt, or find something gentle to say. Sino lets the family answer once, in their own voices. Then when Lola asks again, the home answers for them, kindly, with a photo she knows. And an always-on mic in Lola's sala never streams anywhere: everything runs inside the house, with no internet.

**Caregiver line:** TODO — one real quote from a caregiver/nurse we talk to before 7 AM, with permission. Do not read a quote until that slot is filled. Do not invent one.

### Why local (closing, 4:00)

Lead with: **"An always-on mic in Lola's sala must never stream anywhere."** Then recap the differentiators: her family's real voices (never cloned), silence when it isn't sure, replies the family wrote, every decision visible. Then: it works with the internet off (show the OFFLINE badge again). Mention battery only if the hub was shown unplugged. Don't claim it's faster than the cloud.

## Live quick setup

The live question is **"Nasaan yung aso?"** It is not in the seed. "Nasaan si Joy?" stays in the seed ([features.md](features.md)).

Beat: ask it → quiet yellow card on `/caregiver` → the family adds it in `/setup` on the iPhone → ask again → the family voice answers on the iPad. Owner of the screen: Ayen.

## TV test (its own beat)

TODO (Viviene): source or record a 20 s clip with "nasaan si nanay" buried mid-dialogue, not as the whole line.

On stage: the clip plays, Sino stays silent, and `TV lines ignored: N` ticks. TODO (Troy): today the counter only ticks when the clip's words hit the TV-word rule; a model `silent` does not set `ignored` `tv` ([architecture.md](architecture.md#backstage-proof)). Check the real clip on the hub. Then Lola asks "Nasaan si Nanay?" as the whole line, and the seeded comfort reply plays. Backstage shows the dropped row for the clip and the rule-or-model row for her plain ask ([architecture.md](architecture.md#backstage-proof)).

## "Sino ka?" (photo + recorded line)

A co-presenter playing Lola asks "Sino ka?". It matches the seeded question `sino-ka`, so the iPad shows the photo of Troy with Lola and plays the line he recorded in setup: "Lola, ako 'to, si Troy. Pamangkin mo. Ito tayo nung pasko." Then Troy talks to "Lola" in person, on stage. There is no call (a next step, [features.md](features.md#cut-tonight-moved-to-next-steps)); face match is the optional beat below.

The screen never quizzes Lola. Without face match, "Sino ka?" always plays Troy's line, whoever is in the room (TODO: Troy, confirm that is fine for the pitch).

### Optional: face match (only if T6 is built and works on the hub)

Joy (a teammate enrolled as joy) stands in front of the camera. Lola asks "Sino ka?". Sino grabs one frame; on a high-confidence match the iPad shows Joy's photo and plays Joy's line, and `/backstage` shows `face_seen` and `decided.who`. Anything less plays Troy's line. Skip this beat if it is not built, or if it misfires once in rehearsal.

## Ask Sino about Lola (Should, only if wired after the freeze)

A registered person asks on `/caregiver`. "Kamusta si Lola?" and "Ano ang mga tanong niya?" pull the log: the counts and her words, not a diagnosis. "Nasaan si Lola?" gets the no-camera answer and never names a room, because the CCTV add-on is cut. Code: `brain/ask.py` (PR #11). Skip this beat if it is not wired.

## Fallbacks (internet stays off)

| If this fails on stage | Do this |
|---|---|
| Always-listening misses Lola | Hidden "listen now" button on backstage |
| The mic or Whisper fails | Type Lola's question into the hidden box on backstage; it goes through the same `decide()` |
| The model is slow or wrong | Rules + matcher still answer known questions; backstage shows the decision |
| The hub's network | Primary is the iPhone hotspot + hub LAN-only firewall (keep the iPhone on the hotspot screen). Then down the ladder ([architecture.md](architecture.md#network)): spare router/pocket Wi-Fi with no WAN → iPhone USB + Internet Sharing + firewall → venue Wi-Fi + firewall. Regenerate the mkcert cert if the hub IP changes. Last resort, USB-C cable to the iPad |
| The hub crashes | `start.sh`, wait for the health light |
| The whole live demo | Play the backup video (recorded at the 7 AM rehearsals, internet off in the first 10 s) |
| Ask Sino about Lola not wired | Skip it; the core beats don't depend on it |
| A recording is missing | Comfort has no audio to play. Record it before 7 AM; don't substitute text-to-speech |

## Submission video (~1 min)

Show no internet in the **first 10 seconds**, then the live "Nasaan yung aso?" setup, the TV clip staying silent while the counter ticks, the plain "Nasaan si Nanay?" comfort reply, and the urgent chime + red card. Full checklist: [../05-submission.md](../05-submission.md).
