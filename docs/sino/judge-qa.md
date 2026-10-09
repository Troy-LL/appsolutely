# Sino: judge Q&A, risks, and mitigations

Judges ask about how it works, decisions made, architecture, the AI implementation, its limitations, and what each person built ([../00-event.md](../00-event.md)). Every answer must match the other docs in this folder. Quote only numbers logged in `docs/NOTES.md`.

## Likely questions

**"How is this different from any offline dementia assistant?"**
(a) The voices are real recordings by the family, never cloned or synthetic. Cloning a relative's voice for a confused elder is an ethics problem. (b) Silence is a decision: Sino ignores TV and chatter, only speaks to known questions, and escalates new or urgent ones to a human. (c) The family writes and records every reply in quick setup, so the AI never invents facts about the family. (d) The backstage screen shows each decision and its reason live.

**"Isn't this just a Google Home routine?"**
Lola won't say a wake word, so Sino listens without one and decides on its own. The replies are the family's own recorded voices, not a synthetic assistant. And it triages every line: comfort, caregiver, urgent, or silent.

**"Isn't the reply lying to her?"**
The family writes and records every word in quick setup (we show it live). For "Nasaan si Nanay?" (her late mother) the seeded reply validates instead of correcting or inventing: "Ma, ikwento mo nga si Nanay mo. Nandito lang kami." "Nasaan si Joy?" gets "Nasa trabaho ako" because Joy really is at work.

**"What if it mishears, or the TV says it?"**
Junk lines and likely-no-speech clips are dropped before the decision. If the matcher misses and the model says it's chatter, Sino stays silent and logs it. (Show it live with the TV clip.)

**"What if she's in pain?"**
Urgent words always alert; the model can only escalate, never downgrade. The hub plays a loud chime so anyone in the house hears it, and the caregiver phone gets a red card. Medication questions are never answered; they go to the caregiver.

**"How does the alert reach the phone with no internet?"**
It doesn't use push notifications (those need Apple's servers). The chime is the first channel; the caregiver page, open on the home network, is the second.

**"What does the AI actually do?"**
Silero VAD detects speech; whisper.cpp transcribes it on the hub; a filter drops junk; rules and a matcher handle urgent words and known questions; Qwen2.5 in Ollama decides the unclear lines as JSON. Backstage shows every step with its latency. The daily recap is plain counts computed by code.

**"Why not the cloud?"**
An always-on mic in Lola's sala must never stream anywhere. It also has to keep working when the internet is down.

**"How accurate is it on Tagalog? How fast?"**
Quote only our own smoke-test and 30-clip numbers from `docs/NOTES.md`. The Whisper paper's FLEURS Tagalog figures (small 27.7% WER, medium 19.1%) are benchmark numbers on read speech, not ours.

**"Who owns an M2 at home?"**
We measured on an M2. Cheaper hubs are a next step. (Only claim "any old laptop" if we timed one, e.g. Troy's 2017 MacBook Pro.)

**"Who built what?"**
See the owners table in [mvp-plan.md](mvp-plan.md#owners). Everyone explains their own part.

## Risks and mitigations

| Risk | Mitigation | Owner |
|---|---|---|
| Speech recognition mishears Lola's Taglish | Two phrasings per question, matcher threshold, silent-if-unsure, caregiver card for anything new; speech model picked by measurement | Troy, Donita |
| Whisper invents text from silence or TV sign-offs | Junk-line filter (quiet clips, likely-no-speech, known junk lines) before `decide()` | Donita |
| An urgent line is missed | Urgent words checked first; model can only escalate; urgent 10/10 in the pass/fail gate | Troy |
| TV or chatter triggers a reply | Silent when the matcher misses and the model says chatter; TV clips in the test set with a 0 false-trigger target | Troy |
| Always-listening floods the model | One model call at a time; stale clips dropped | Donita |
| Always-listening misses on stage | Hidden "listen now" button and typed-question box on backstage | Viviene |
| Model too slow or bad JSON | Known questions skip the model; error or timeout → caregiver; RAM rule picks 3B or 1.5B; rules + matcher fallback if the gate fails | Troy, Donita |
| No push notifications offline | Hub chime first, caregiver page on the local network second | Donita, Viviene |
| Internet Sharing doesn't work with no upstream | Tested at 11:15 PM; Android hotspot with data off or travel router as fallback | Donita |
| Hub owner asleep when the hub breaks | `start.sh` + health light, so anyone can restart it; handoff notes | Donita |
| Alert fatigue for the caregiver | Yellow cards are quiet and grouped; only red makes sound | Viviene |
| Lola is distressed by the system | Lola's screen is never red; greeting never quizzes her or announces names as a test | Ayen, Troy |
| Overnight scope creep | MVP frozen at 2:00 AM; add-ons behind a cut line in order a → b → c, cut at 5:00 AM | Troy |
| Face or voice names the wrong person | Name only on a high-confidence match plus a greeting; unknown → no name; voice ID last because two 10 s samples are thin | Troy, Donita |
| Overclaiming in the pitch | Unmeasured numbers labeled "to verify"; no "faster than cloud"; battery only if shown unplugged; CCTV labeled as a recorded clip; seed data disclosed | Everyone |
| Privacy of voices, faces, and transcripts | Everything stays on the hub; no audio stored by default; family can delete the log | Donita |
| Being read as a medical device | Recap is counts only and says "not a diagnosis"; always escalates to a human | Viviene |
