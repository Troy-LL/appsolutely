# Sino: demo script

Format (from [../00-event.md](../00-event.md)): 5-minute pitch with a live demo, then 3 minutes of judge Q&A. Max 4 to 5 slides. Working product over slides. End with the People's Choice "scan to vote" ask.

## Setup before going on stage

- Hub (M2) running from `start.sh`, seed loaded, health light green.
- iPad on `/lola`, "Simulan" already tapped. iPhone on `/caregiver`, open on the hub's network (no push without internet). Backstage on the projected screen.
- Internet off on every device. The OFFLINE badge is visible.
- Clips ready: a TV clip ("Nasaan si Nanay?" from a show), and the recorded CCTV clip only if add-on (b) shipped.
- Hub volume up for the urgent chime.

## Run of show

| Time | What happens | Screen |
|---|---|---|
| 0:00–0:30 | Opener (below) | Lola's iPad |
| 0:30–1:00 | Show there's no internet. Point at the OFFLINE badge. If the M2 is unplugged, say it runs on battery (only if it really is unplugged) | Backstage |
| 1:00–1:30 | **Live quick setup:** add "Nasaan si Joy?", two phrasings, hold to record a reply, add a photo, test (~20 s). Proof that the family writes every reply | Setup → iPad |
| 1:30–3:00 | "Lola" asks "Nasaan si Nanay?" in 2 phrasings → the family's validation reply + photo plays. Backstage shows transcript, decision, latency. Then the "Sino ka?" roleplay | iPad + backstage |
| 3:00–3:30 | Point judges at `/backstage` and say "Silence is a decision." Then play the TV clip: Sino stays silent (backstage shows why). Ask a new question: a quiet yellow card appears; ask again and it groups | Backstage + iPhone |
| 3:30–4:00 | "Masakit dibdib ko" → the hub chimes and a red card appears on the phone. Lola's screen stays calm. A medication question goes to the caregiver | Hub + iPhone |
| 4:00–5:00 | Why local + close + scan-to-vote | Slide |

If an add-on shipped, it replaces part of 1:30–3:00 (face greeting) or is shown in 15 s at 3:30 ("Nasaan si Lola?"). Otherwise it goes on the "next steps" slide.

**Pitch order:** lead with the always-on mic privacy line and the four differentiators in [README.md](README.md#what-makes-it-different) (real family voices, silence as a decision, family-written replies, visible decisions). The offline/brownout angle is supporting proof, not the hook.

### Opener

> "Nasaan si Nanay?" If you've cared for a lola with dementia, you've heard a question like this ten times in one afternoon. Every time, someone has to choose: tell her the truth again and watch her hurt, or find something gentle to say. Sino lets the family answer once, in their own voices. Then when Lola asks again, the home answers for them, kindly, with a photo she knows. And an always-on mic in Lola's sala never streams anywhere: everything runs inside the house, with no internet.

### Why local (closing, 4:00)

Lead with: **"An always-on mic in Lola's sala must never stream anywhere."** Then recap the differentiators: her family's real voices (never cloned), silence when it isn't sure, replies the family wrote, every decision visible. Then: it works with the internet off (show the badge again). Mention battery only if the hub was shown unplugged. Don't claim it's faster than the cloud.

## "Sino ka?" roleplay (MVP)

"Sino ka?" is a seeded question. A co-presenter playing Lola asks "Sino ka?" → the iPad shows a photo of Troy with Lola and plays Troy's recorded voice: "Lola, ako 'to, si Troy, pamangkin mo. Ito tayo nung pasko." Then Troy says it live.

If add-on (a) face greeting shipped, Troy instead walks up and says "Hi Lola, ako 'to"; Lola's screen shows his photo and line only on a high-confidence match. It never quizzes Lola and never announces names as a test. If it isn't reliable, use the seeded reply above.

## "Nasaan si Lola?" (add-on b)

Only if it is stable by 5:00 AM. The caregiver taps "Nasaan si Lola?" on the iPhone. The M2 runs the person detector live on a **recorded clip** of "Lola" moving between sala and kusina; backstage shows the detection box, and the phone answers from the last-seen log ("Nasa kusina, 1 minuto na"). Say out loud that it is a recorded clip. The answer is never hardcoded.

## Fallbacks (internet stays off)

| If this fails on stage | Do this |
|---|---|
| Always-listening misses Lola | Hidden "listen now" button on backstage |
| The mic or Whisper fails | Type Lola's question into the hidden box on backstage; it goes through the same `decide()` |
| The model is slow or wrong | Rules + matcher still answer known questions; backstage shows the decision |
| The hub's network | Switch to the backup network chosen at the 11:15 PM checkpoint; last resort, USB-C cable to the iPad |
| The hub crashes | `start.sh`, wait for the health light |
| The whole live demo | Play the backup video (recorded at the 7 AM rehearsals, internet off in the first 10 s) |
| Any add-on | Skip it; it goes on the next-steps slide |

## Submission video (~1 min)

Show no internet in the **first 10 seconds**, then quick setup, the comfort reply, the TV clip staying silent, and the urgent chime + red card. Full checklist: [../05-submission.md](../05-submission.md).
