# Sino: features and scope

Scope rules: the MVP is frozen at **2:00 AM Sat**. Should items come next. Add-ons (a) and (b) sit **behind a cut line**, are built only after the freeze, in that order, and each has an off switch and a fallback. (b) ships only if it is stable by 5:00 AM. (c) voice ID is cut. "Next steps" items are pitch-only and are **not built**. Timeline: [mvp-plan.md](mvp-plan.md).

## MVP (frozen by 2:00 AM)

Always-listening hub mic (Silero VAD) → whisper.cpp → junk-line filter → `decide()` (urgent rules + matcher, Qwen for unclear lines) → iPad plays the family's recorded reply + photo → caregiver log and alerts, urgent chime from the hub → behind-the-scenes screen with the OFFLINE badge. The family adds questions and replies through quick setup.

### M1. Listening pipeline (Donita)

- **Always-listening:** Silero VAD on the hub mic cuts clips when someone speaks.
- **Throttle:** one model call at a time; stale clips (older than the one being processed) are dropped.
- **Junk-line filter, before `decide()`:** drop clips that are too quiet, that Whisper marks as likely no speech, or whose transcript matches known junk lines ("Thank you for watching", "Salamat sa panonood", and similar). These never reach Lola or the caregiver. Backstage logs them as `heard` with `dropped` true ([architecture.md](architecture.md#the-3-interfaces-locked-in-the-first-15-minutes)).
- **Demo safety:** a hidden "listen now" button on `/backstage` forces a capture, and a hidden typed-question box sends text through the same `decide()` if the mic or Whisper fails.

### M2. Decision: comfort / caregiver / urgent / silent (Troy)

Keyword rules first, then the known-question matcher, then the local model (Qwen2.5-3B via Ollama, or 1.5B depending on RAM; see [architecture.md](architecture.md)) only for lines the rules and matcher can't settle.

- Urgent words (masakit, nahulog, tulong, hindi makahinga) **always** alert. The model can only escalate, never downgrade.
- Medication questions are **never answered**. They always go to the caregiver.
- If the matcher misses and the model says it's chatter (TV, conversation), Sino stays **silent** and logs it.
- If the model errors or times out, Sino defaults to the caregiver, never to silence.

### M3. Family voice replies on Lola's screen (Ayen: screen; Troy: matching)

The matched reply plays in the family member's recorded voice with their photo, full screen on the iPad. **Rule: no cloned or synthetic family voices.** Only recordings the family made themselves are played. Silent if unsure. Lola's screen is never red and shows nothing else (see [architecture.md](architecture.md#viewports)).

### M4. Quick setup = onboarding (Ayen)

The family's whole setup, and the live proof that the family wrote the replies:

1. Add a question.
2. Add two phrasings of how Lola says it.
3. Hold to record the reply.
4. Add a photo.
5. Test: say the question and see what Sino heard and decided.

### M5. Caregiver phone (Viviene)

- Live log.
- **Red (urgent):** card with Lola's exact words. The only card that makes a sound.
- **Yellow (caregiver):** quiet card, repeats grouped ("Lola asked about the aso 3×"), with one-tap record-a-reply.
- **Green (comforted):** quiet log entry.
- `/caregiver` only receives alerts while it is open on the hub's local network. There are no push notifications with the internet off (iOS push needs Apple's servers).

### M6. Urgent chime (Donita)

On urgent, the hub speaker plays a loud chime so anyone in the house hears it. The caregiver phone's red card is the second channel. Lola's screen never shows red. The `afplay` command and the 1:00 AM test are in [hub-chime.md](hub-chime.md).

### M7. Behind-the-scenes screen (Viviene)

Judges see the local AI decide. Each utterance is one row: transcript → rule hit or model → action + confidence + reason → ms. A dropped row covers a junk-line drop and a TV line Sino ignored. A running counter reads `TV lines ignored: N`. Also on this screen: an **OFFLINE** badge, the health light, the hidden "listen now" button, the typed-question box, and the T5 badge in [mvp-plan.md](mvp-plan.md). Fields: [architecture.md](architecture.md#backstage-proof). Hidden from families.

### M8. Demo seed data, `seed.json` (Troy + team)

Lola Cora; 5 to 6 questions with phrasings; teammate-recorded replies and photos; safety words; earlier log entries; meal log. Disclosed in the README as demo data. Seeded replies include:

| Question | Reply (recorded by a teammate) | Why |
|---|---|---|
| "Nasaan si Nanay?" (Lola's late mother) | "Ma, kwento mo nga ulit si Nanay mo." | Validation: invites the memory, no correction, no false claim |
| "Nasaan si Joy?" | "Nasa trabaho pa ako, Ma. Uuwi ako mamaya, kain ka muna." | Joy is alive and at work, so this is true |
| "Sino ka?" | "Lola, ako 'to, si Troy. Pamangkin mo. Ito tayo nung pasko." with a photo of Troy and Lola | The "Sino ka?" roleplay ([demo.md](demo.md)) |
| "Nasaan ako?" | "Dito ka lang, Ma. Kasama mo ako." | She is here with Joy. No room and no destination. Speaker: Joy. Audio not recorded yet |
| "Gusto ko nang umuwi" | "Ma, dito muna tayo ha." | Does not promise a trip home. Speaker: Joy. Audio not recorded yet |

## Should (after the freeze, before add-ons)

- **Meals check:** the caregiver taps "Kumain na" → "Kumain na ba ako?" gets a true answer from the local log.
- **Clock answer:** recorded time clips for "Anong oras na?" (the big clock is already on Lola's screen).
- **Daily recap:** counts and times computed by code only, no AI phrasing ("Asked about Nanay 6×, mostly 4 to 6 PM. 1 urgent alert at 5:15 PM."). Marked "not a diagnosis."

## Add-ons (behind the cut line, after the 2:00 AM freeze, in this order)

(a) and (b) are optional, each has an off switch, and each is cut at **5:00 AM** if not stable. (b) ships only if it is stable by 5:00 AM. (c) voice ID is already cut and is not started.

**Not the story:** the face greeting (a) and the "Nasaan si Lola?" camera view (b) overlap with common offline dementia-assistant ideas (photo/face tagging, wandering cameras), so they add little innovation. They are demo extras. The pitch stays on the differentiators in [README.md](README.md#what-makes-it-different).

1. **(a) Face greeting for 3 enrolled family members** (not Lola). About 5 photos each; face-api.js or MobileFaceNet ONNX. Rule: high-confidence face match AND a greeting transcript ("Hi Lola", "Lola, ako 'to") → Lola's screen shows that person's photo with Lola and their recorded line. Unknown person → no name. If cut, the seeded "Sino ka?" reply covers the demo. Owners: Troy (match + rule), Ayen (greeting view).
2. **(b) "Nasaan si Lola?" on seeded footage.** A pre-recorded clip of "Lola" moving between sala and kusina; the M2 runs a person detector (MediaPipe or YOLO) on it live and keeps a last-seen log, so the answer is computed ("Nasa kusina, 1 minuto na"), never hardcoded. Labeled in the demo as a recorded clip. Owners: Donita (detector), Viviene (view).
3. **(c) Voice ID is cut.** Not built. No speaker match, no voice samples, no voice panel on `/backstage`. [mvp-plan.md](mvp-plan.md).

**Distress rule for all add-ons:** the greeting never quizzes Lola ("Who is this?") and never announces names as a test. It only adds a photo and a recorded line when a family member greets her.

## Next steps (not building)

Recording replies from family abroad (OFW), learning which voice calms her best, visitor recognition, night wandering alerts, a native iPad app, cheaper hubs.

## A day with Sino (example story for the pitch)

1. **Sunday, setup (about 10 min):** Ate Joy adds "Nasaan si Nanay?", "Nasaan si Joy?" and "Kumain na ba ako?" with two phrasings each, records her replies, adds her photo, and tests once.
2. **4:30 PM:** Lola asks "Si Nanay, asan?" Ate Joy's photo and voice answer: "Ma, kwento mo nga ulit si Nanay mo." Lola starts talking about her mother.
3. **4:50 PM:** "Nasaan yung aso?" is not in the seed. Sino stays quiet with Lola and adds a quiet yellow card. The family adds it in `/setup`; the next ask plays their voice. Repeats before that reply group on the card ("Lola asked about the aso 3×"). This is the live demo question ([demo.md](demo.md)). "Nasaan si Joy?" stays in the seed.
4. **5:15 PM:** "Masakit dibdib ko." No comfort clip. The hub chimes loudly, and a red card shows Lola's exact words.
5. **5:30 PM:** a teleserye plays a longer dialogue that contains "nasaan si nanay" mid-sentence, not as the whole line. The matcher misses, the model says chatter, Sino stays silent, and `/backstage` counts it under `TV lines ignored`. She can still ask "Nasaan si Nanay?" plainly and get the comfort reply.
6. **6:00 PM:** the internet is down. Sino keeps working, because everything runs inside the house.
7. **9:00 PM recap:** "Asked about Nanay 6×, mostly 4 to 6 PM. 1 urgent alert at 5:15 PM."

## UX rules

- **Lola's screen:** big clock, idle photo, full-screen photo with the voice. No menus, no text input, calm colors, never red.
- **Caregiver app:** one-handed, one action per card, Taglish labels. Only red makes sound.
- **Behind-the-scenes screen:** hidden from families; dense is fine.
- Every screen has empty, loading, result, and error states ([../../AGENTS.md](../../AGENTS.md)).
