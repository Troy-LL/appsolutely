# Sino: demo script

Format (from [../00-event.md](../00-event.md)): 5-minute pitch with a live demo, then 3 minutes of judge Q&A. Max 4 to 5 slides. Working product over slides. End with the People's Choice "scan to vote" ask.

## Setup before going on stage

- Hub (M2) running from `start.sh`, seed loaded, health light green.
- iPad on `/lola`, "Simulan" already tapped. iPhone on `/caregiver`, open on the hub's network (no push without internet). Backstage on the projected screen.
- Internet off on every device. The OFFLINE badge is visible.
- Clips ready: the 20 s teleserye clip (TODO below), and the recorded CCTV clip only if add-on (b) is stable by 5:00 AM. Voice ID is cut and has no clip.
- Hub volume up for the urgent chime.

## Run of show

| Time | What happens | Screen |
|---|---|---|
| 0:00–0:30 | Opener (below) | Lola's iPad |
| 0:30–1:00 | Show there's no internet. Point at the OFFLINE badge. If the M2 is unplugged, say it runs on battery (only if it really is unplugged) | Backstage |
| 1:00–1:50 | **Live quick setup.** Ask "Nasaan yung aso?" (not in the seed) → quiet yellow card on `/caregiver` → on the iPhone, `/setup` adds the question, two phrasings, a held recording, and a photo → ask again → the family voice answers on the iPad. "Nasaan si Joy?" stays in the seed and is not added live | iPhone `/setup` + `/caregiver` → iPad |
| 1:50–2:20 | "Sino ka?" Lola asks who Troy is. Face match sees he is registered. The iPad shows his photo and calls him only while he is on the house Wi-Fi (no internet). If he is not on that network, the iPad shows his photo and plays the "Sino ka?" line he recorded in setup. | iPad + Troy |
| 2:20–3:30 | **TV test, its own beat.** Play the 20 s teleserye clip: a full dialogue that contains "nasaan si nanay" mid-sentence, not as the whole line. Sino stays silent. `/backstage` shows a dropped row and `TV lines ignored: N` ticks. Then Lola asks "Nasaan si Nanay?" plainly → the comfort reply and photo. The row shows transcript → rule or model → action, confidence, reason → ms | Backstage + iPad |
| 3:30–4:00 | "Masakit dibdib ko" → the hub chimes ([hub-chime.md](hub-chime.md)) and a red card appears on the phone. `/lola` stays calm and never red. A medication question goes to the caregiver | Hub + iPhone |
| 4:00–5:00 | Why local + close + scan-to-vote | Slide |

If add-on (b) is stable by 5:00 AM, show "Nasaan si Lola?" in 15 s at 3:30. Voice ID is cut and is not shown. Anything cut goes on the "next steps" slide.

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

On stage: the clip plays, Sino stays silent, and `TV lines ignored: N` ticks. Then Lola asks "Nasaan si Nanay?" as the whole line, and the seeded comfort reply plays. Backstage shows the dropped row for the clip and the rule-or-model row for her plain ask ([architecture.md](architecture.md#backstage-proof)).

## "Sino ka?" (live call)

A co-presenter playing Lola asks who Troy is. Face match sees that Troy is a registered person. The iPad shows the photo of Troy with Lola and calls him only while he is on the house Wi-Fi. The call does not use the internet. Troy answers live: "Lola, ako 'to, si Troy. Pamangkin mo. Ito tayo nung pasko."

If he is not on that network, the iPad shows his photo and plays the "Sino ka?" line he recorded in setup. A person who is not registered gets no name and no call. The screen never quizzes Lola.

If face match is not up and Troy is on the house Wi-Fi, he still talks to her live and the iPad shows his photo. If he is not on the network, the recorded line plays.

## "Nasaan si Lola?" (add-on b)

Only if it is stable by 5:00 AM. A registered person asks Sino, "Nasaan si Lola?" The M2 runs the person detector on a **recorded clip** of "Lola" moving between sala and kusina; backstage shows the detection box, and the phone answers from the last-seen log ("Nasa kusina, 1 minuto na"). Say out loud that it is a recorded clip. The answer is never hardcoded. "Kamusta si Lola?" and "Ano ang mga tanong niya?" pull the log already on `/caregiver`. That answer is the counts and her words. It is not a diagnosis.

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

Show no internet in the **first 10 seconds**, then the live "Nasaan yung aso?" setup, the TV clip staying silent while the counter ticks, the plain "Nasaan si Nanay?" comfort reply, and the urgent chime + red card. Full checklist: [../05-submission.md](../05-submission.md).
