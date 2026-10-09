# Sino: features and scope

Scope rules (Troy, Sat 2:00 AM): the MVP is frozen at **3:30 AM Sat** (moved from 2:00 AM). Should items come after the freeze. **Add-ons (Troy, Sat 3:23 AM):** only (a) face match is back, as an after-freeze add-on on Troy's path (see Should below). (b) The "Nasaan si Lola?" CCTV clip, the door alert, and (c) voice ID stay in "Next steps". The live call is cut too. "Next steps" items are pitch-only and are **not built**. Timeline: [mvp-plan.md](mvp-plan.md). Decision log: [../NOTES.md](../NOTES.md#decision-log).

## MVP (frozen by 3:30 AM)

**Core to protect until the freeze:**

1. The hub hears Lola, transcribes her, and runs `decide()`.
2. A known question gets the family's recorded voice and photo on the iPad.
3. An urgent line gets the hub chime and a red card on the caregiver phone.
4. TV stays silent, and `/backstage` shows every decision.
5. Quick setup works live with "Nasaan yung aso?".

Always-listening hub mic (Silero VAD) → whisper.cpp → junk-line filter → `decide()` (urgent rules + matcher, Qwen for unclear lines) → iPad plays the family's recorded reply + photo → caregiver log and alerts, urgent chime from the hub → behind-the-scenes screen with the OFFLINE badge. The family adds questions and replies through quick setup.

### M1. Listening pipeline (Donita)

- **Always-listening:** Silero VAD on the hub mic cuts clips when someone speaks.
- **Throttle:** one model call at a time; stale clips (older than the one being processed) are dropped.
- **Junk-line filter, before `decide()`:** drop clips that are too quiet, that Whisper marks as likely no speech, or whose transcript matches known junk lines ("Thank you for watching", "Salamat sa panonood", and similar). These never reach Lola or the caregiver. Backstage logs them as `heard` with `dropped` true ([architecture.md](architecture.md#the-3-interfaces-locked-in-the-first-15-minutes)).
- **Demo safety:** a hidden "listen now" button on `/backstage` forces a capture, and a hidden typed-question box sends text through the same `decide()` if the mic or Whisper fails.

### M2. Decision: comfort / caregiver / urgent / silent (Troy)

Keyword rules first, then the known-question matcher, then the local model (`qwen2.5:3b` via Ollama; `qwen2.5:1.5b` only with the Whisper medium fallback, see [architecture.md](architecture.md#speech-model-selection-by-1130-pm)) only for lines the rules and matcher can't settle. Order in `brain/decide.py`: urgent words → "sakit ng loob" idiom → medication → TV words → known-question matcher → model.

- Urgent words **always** alert. Only these rules raise urgent; a model urgent becomes caregiver. The stems in `brain/decide.py` (case- and spacing-insensitive): natumba, nadulas, nadapa, nahulog, bumagsak; masakit, sumasakit, ang sakit ng dibdib, masakit dibdib; di/hindi makahinga, hirap huminga, nahihirapan huminga; tulungan, tulong, saklolo. Whisper slips on those stems still alert. An explicit list maps masaket → masakit and didip/dibdip → dibdib. Other urgent tokens allow an edit distance of at most 1 when the shorter word is 4–6 letters, and at most 2 when it is 7 or more. A stem stuck to a short word still counts ("masaketang" is "masakit" + "ang"). "hindi makahinga" still needs both parts. hirap, huminga, and hinga use that same first-letter rule and alert as a pair: hirap with huminga or hinga, and di or hindi with huminga or hinga ("di maka hinga"). English stems match whole, because Whisper sometimes writes English: can't breathe, cannot breathe, help, I fell, fell down, chest pain, my chest hurts. A TV line does not become urgent this way.
- The idiom "masakit ang loob" / "sakit ng loob" (hurt feelings) goes to the **caregiver**, not urgent.
- Medication questions (gamot, dosis, reseta, tableta) are **never answered**. They always go to the caregiver.
- Known TV lines and words ("Thank you for watching", "Salamat sa panonood", abangan, kabanata, palabas, teleserye, dula, bes, balita, commercial) are **silent** by rule, with `ignored` set to `tv`. A TV word counts inside a longer word ("sateleserye"). A real urgent hit still wins.
- Known-question matcher: drops filler words (po, opo, lola, ma, na, ba) and punctuation, reads "asan" as "nasaan" and "where's" as "where is", and needs a similarity of at least 0.85 to a seeded phrasing. If that misses, it retries once after a light repair of the seed words only: two fragments joined back into a seed word, or one stuck token split into seed words ("na fan si Nanai", "nasaanzi na nai"). The 0.85 bar does not move. Below that, Sino does not answer Lola.
- If the matcher misses and the model says it's chatter (TV, conversation) with confidence ≥ 0.9, and the line has no breathing, pain, or fall word, Sino stays **silent** and logs it. Lower confidence, a body word, a model urgent, or a model comfort goes to the caregiver. A missed urgent is never silent.
- If the model errors, returns bad JSON, or takes longer than 4 s, Sino defaults to the caregiver, never to silence.
- `SINO_MODEL=stub` (the default) never calls the model, so every line the rules and matcher miss goes to the caregiver. `SINO_MODEL=ollama` calls Ollama at `HUB_URL` (default `http://localhost:11434`).

### M3. Family voice replies on Lola's screen (Ayen: screen; Troy: matching)

The matched reply plays in the family member's recorded voice with their photo, full screen on the iPad. Pre-recorded family voices are **the** reply for every known question, not a fallback. **Rule: no cloned or synthetic family voices, and no text-to-speech.** Only recordings the family made themselves are played. Silent if unsure. "Sino ka?" is one of these known questions: the iPad shows the registered person's photo and plays the line they recorded. Lola's screen is never red and shows nothing else (see [architecture.md](architecture.md#viewports)).

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
- **Ask Sino about Lola** is a Should item after the freeze (see below), not MVP.

### M6. Urgent chime (Donita)

On urgent, the hub speaker plays a loud chime so anyone in the house hears it. The caregiver phone's red card is the second channel. Lola's screen never shows red. The `afplay` command and the 1:00 AM test are in [hub-chime.md](hub-chime.md).

### M7. Behind-the-scenes screen (Viviene)

Judges see the local AI decide. Each utterance is one row: transcript → rule hit or model → action + confidence + reason → ms. A dropped row covers a junk-line drop and a TV line Sino ignored. A running counter reads `TV lines ignored: N`. Also on this screen: an **OFFLINE** badge, the health light, the hidden "listen now" button, the typed-question box, and the T5 badge in [mvp-plan.md](mvp-plan.md). Fields: [architecture.md](architecture.md#backstage-proof). Hidden from families.

### M8. Demo seed data, `seed.json` (Troy + team)

What `brain/seed.json` holds today: **5 questions** (`nasaan-si-nanay`, `nasaan-si-joy`, `sino-ka`, `nasaan-ako`, `gusto-ko-nang-umuwi`), each with Tagalog and English phrasings and a `speaker`. `reply_audio` and `photo` are empty strings until the recordings and photos exist. Disclosed in the README as demo data.

Not in `seed.json` yet: the household name (Lola Cora), earlier log entries, and a meal log (TODO: unknown whether they are still needed; the T7 fake log lives in `brain/tests/ask_cases.json`). The urgent, medication, and TV words live in `brain/decide.py`, not in the seed.

**Recordings still needed (TODO):** Joy's four replies and Troy's "Sino ka?" line. Until they exist, a comfort decision has no audio to play.

| Question | Reply (recorded by a teammate) | Speaker | Why |
|---|---|---|---|
| "Nasaan si Nanay?" (Lola's late mother) | "Ma, kwento mo nga ulit si Nanay mo." | Joy | Validation: invites the memory, no correction, no false claim. Audio not recorded yet |
| "Nasaan si Joy?" | "Nasa trabaho pa ako, Ma. Uuwi ako mamaya, kain ka muna." | Joy | Joy is alive and at work, so this is true. Audio not recorded yet |
| "Sino ka?" | "Lola, ako 'to, si Troy. Pamangkin mo. Ito tayo nung pasko." | Troy | The iPad shows Troy's photo and plays this line ([demo.md](demo.md)). On stage, Troy then talks to "Lola" in person. There is no live call. Audio not recorded yet |
| "Nasaan ako?" | "Dito ka lang, Ma. Kasama mo ako." | Joy | She is here with Joy. No room and no destination. Audio not recorded yet |
| "Gusto ko nang umuwi" | "Ma, dito muna tayo ha." | Joy | Does not promise a trip home. Audio not recorded yet |

## Should (after the 3:30 AM freeze)

- **Ask Sino about Lola (T7).** A registered person asks on the caregiver phone, in their own words. `answer_about_lola(question, log)` in `brain/ask.py` (merged, PR #11) picks one intent: `how`, `saying`, or `where` (rules first; Qwen only picks the intent when `SINO_MODEL=ollama`). Code builds the answer from the log: counts, her exact words, and the last urgent alert, ending with "Not a diagnosis." "Where is she" gets the no-camera answer ("Walang camera sagot; hindi ko hulaan ang kwarto.") and never names a room, because add-on (b) is cut. Medication questions get no answer. It never invents a mood or a medical read. Lola's iPad is not this conversation. Still to do after the freeze: wire it to `/caregiver` (TODO: contract gap, no event or route for it in [architecture.md](architecture.md#the-3-interfaces-locked-in-the-first-15-minutes) yet).
- **Meals check:** the caregiver taps "Kumain na" → "Kumain na ba ako?" gets a true answer from the local log.
- **Clock answer:** recorded time clips for "Anong oras na?" (the big clock is already on Lola's screen).
- **Add-on (a) face match (T6, Troy; not built yet).** Starts only after the core runs end to end on the hub (W1) and T5 passes there, after the 3:30 AM freeze, with a hard stop at 5 AM. One frame on demand: when "Sino ka?" fires, Sino grabs **one** frame (no continuous stream, no polling loop; `POST /face/frame` is called once per trigger). OpenCV YuNet detects and SFace recognises (a few MB, hub CPU) against 3 family members enrolled on the hub (troy, joy, donita). A family member's line plays **only on a high-confidence match**; otherwise Troy's seeded line plays, never the wrong relative. Enrollment photos are gitignored; frames stay in memory only. If the hub starts swapping, fall back to `qwen2.5:1.5b`. The iPad still never quizzes Lola, and the reply plays through the normal reply screen (no face-match frame, A4 stays cut).
- **Daily recap:** counts and times computed by code only, no AI phrasing ("Asked about Nanay 6×, mostly 4 to 6 PM. 1 urgent alert at 5:15 PM."). Marked "not a diagnosis." The caregiver can ask "Kamusta si Lola?" or "Ano ang mga tanong niya?" and Sino pulls that same log up. "How is she" is the log. It is not a diagnosis.

## Cut tonight (moved to Next steps)

Decided by Troy, Sat 2:00 AM ([../NOTES.md](../NOTES.md#decision-log)); (a) face match was un-cut at Sat 3:23 AM and moved to Should above. The rest are not built. If asked, they are next steps.

1. **(a) Face match:** un-cut Sat 3:23 AM, now a Should add-on (T6). Only the iPad face-match frame (A4) stays cut. Without a high-confidence match, "Sino ka?" plays Troy's seeded photo and line.
2. **(b) "Nasaan si Lola?" on CCTV footage.** Cut (D7, V5). "Nasaan si Lola?" gets the no-camera answer and never guesses a room.
3. **(c) Voice ID.** Cut earlier. No speaker match, no voice samples, no voice panel on `/backstage`.
4. **Live call on the house Wi-Fi.** Cut. Calling a registered person is a next step.

**Distress rule:** the iPad never quizzes Lola ("Who is this?") and never announces names as a test. For "Sino ka?" it shows the photo and plays the recorded line.

## Next steps (not building)

Recording replies from family abroad (OFW), learning which voice calms her best, visitor recognition, "Nasaan si Lola?" from a camera (person detector and last-seen log), voice ID, calling a registered person on the house Wi-Fi (WebRTC, no internet), calling a registered person over the internet (opt-in), a door alert (the hub notices Lola leaving and chimes), Lola's own device for calling and locating her outside the house (needs GPS and a network, opt-in), a native iPad app, cheaper hubs.

## A day with Sino (example story for the pitch)

1. **Sunday, setup (about 10 min):** Ate Joy adds "Nasaan si Nanay?", "Nasaan si Joy?" and "Kumain na ba ako?" with two phrasings each, records her replies, adds her photo, and tests once.
2. **4:30 PM:** Lola asks "Si Nanay, asan?" Ate Joy's photo and voice answer: "Ma, kwento mo nga ulit si Nanay mo." Lola starts talking about her mother.
3. **4:50 PM:** "Nasaan yung aso?" is not in the seed. Sino stays quiet with Lola and adds a quiet yellow card. The family adds it in `/setup`; the next ask plays their voice. Repeats before that reply group on the card ("Lola asked about the aso 3×"). This is the live demo question ([demo.md](demo.md)). "Nasaan si Joy?" stays in the seed.
4. **5:15 PM:** "Masakit dibdib ko." No comfort clip. The hub chimes loudly, and a red card shows Lola's exact words.
5. **5:30 PM:** a teleserye plays a longer dialogue that contains "nasaan si nanay" mid-sentence, not as the whole line. The matcher misses, the model says chatter, Sino stays silent, and `/backstage` counts it under `TV lines ignored` (that count on a model decision needs the model path to set `ignored` to `tv`: TODO, see [architecture.md](architecture.md#backstage-proof)). She can still ask "Nasaan si Nanay?" plainly and get the comfort reply.
6. **6:00 PM:** the internet is down. Sino keeps working, because everything runs inside the house.
7. **9:00 PM:** Joy asks Sino, "Kamusta si Lola?" and "Ano ang mga tanong niya?" Sino pulls the log: "Asked about Nanay 6×, mostly 4 to 6 PM. 1 urgent alert at 5:15 PM." Not a diagnosis. If she asks where Lola is, Sino says it has no camera answer and does not guess a room.

## UX rules

- **Lola's screen:** big clock, idle photo, full-screen photo with the voice. No menus, no text input, calm colors, never red.
- **Caregiver app:** one-handed, one action per card, Taglish labels. Only red makes sound.
- **Behind-the-scenes screen:** hidden from families; dense is fine.
- Every screen has empty, loading, result, and error states ([../../AGENTS.md](../../AGENTS.md)).
