# Sino: features and scope

Scope rules (Troy, Sat 2:00 AM): the MVP is frozen at **3:30 AM Sat** (moved from 2:00 AM). Should items come after the freeze. **Add-ons (Troy, Sat 3:23 AM, revised ~4:30 AM):** (a) face match and (b) the recorded-clip demo are after-freeze add-ons on Troy's path (see Should below). Live CCTV, the door alert, and (c) voice ID stay in "Next steps". The live call is cut too. The recorded-clip demo ships only if the core gate is green, with a hard stop at 5:00 AM. "Next steps" items are pitch-only and are **not built**. Timeline: [mvp-plan.md](mvp-plan.md). Decision log: [../NOTES.md](../NOTES.md#decision-log).

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
- **iPad mic (Donita, Sat ~7:15 AM, after the freeze):** the iPad's mic is now the main way Lola is heard. `/lola` listens all the time in the browser and sends each clip to the hub (`POST /listen/audio`), which runs the same Whisper → junk filter → `decide()` path ([architecture.md](architecture.md#devices)). The hub mic stays for "listen now" and always-listening. To verify on the iPad.
- **Throttle:** one model call at a time; stale clips (older than the one being processed) are dropped.
- **Junk-line filter, before `decide()`:** drop clips that are too quiet, that Whisper marks as likely no speech, or whose transcript matches known junk lines ("Thank you for watching", "Salamat sa panonood", and similar). These never reach Lola or the caregiver. Backstage logs them as `heard` with `dropped` true ([architecture.md](architecture.md#the-3-interfaces-locked-in-the-first-15-minutes)).
- **Demo safety:** a hidden "listen now" button on `/backstage` forces a capture, and a hidden typed-question box sends text through the same `decide()` if the mic or Whisper fails.

### M2. Decision: comfort / caregiver / urgent / silent (Troy)

Keyword rules first, then the known-question matcher, then the local model (`qwen2.5:3b` via Ollama; `qwen2.5:1.5b` only with the Whisper medium fallback, see [architecture.md](architecture.md#speech-model-selection-by-1130-pm)) only for lines the rules and matcher can't settle. Order in `brain/decide.py`: urgent words → "sakit ng loob" idiom → medication → TV words → known-question matcher → model.

- Urgent words **always** alert. Only these rules raise urgent; a model urgent becomes caregiver. The stems in `brain/decide.py` (case- and spacing-insensitive): natumba, nadulas, nadapa, nahulog, bumagsak; masakit, sumasakit, ang sakit ng dibdib, masakit dibdib; di/hindi makahinga, hirap huminga, nahihirapan huminga; tulungan, tulong, saklolo. Whisper slips on those stems still alert. An explicit list maps masaket → masakit and didip/dibdip → dibdib. Other urgent tokens allow an edit distance of at most 1 when the shorter word is 4–6 letters, and at most 2 when it is 7 or more. A stem stuck to a short word still counts ("masaketang" is "masakit" + "ang"). "hindi makahinga" still needs both parts. hirap, huminga, and hinga use that same first-letter rule and alert as a pair: hirap with huminga or hinga, and di or hindi with huminga or hinga ("di maka hinga"). English stems match whole, because Whisper sometimes writes English: can't breathe, cannot breathe, help, I fell, fell down, chest pain, my chest hurts. A TV line does not become urgent this way.
- **Custom safety words.** On the caregiver's Safety words card, a + chip opens "Magdagdag ng salita / Add a word". Save calls `POST /safety-words`. The hub trims, lowercases, and stores the word in `hub/data/safety-words.json` (gitignored). `decide()` merges that list with the stems above. A custom word uses the same fuzzy rules: edit distance 1 when the shorter word is 4–6 letters, 2 when it is 7 or more, first letter must match, and a short word stuck on the front or back still counts. Under 4 letters, over 40 characters, empty, or a duplicate of a built-in or an already saved word is refused. Built-in words are not removed from the card. A built-in urgent hit still wins over a TV line. A custom word does not: if the line is a TV line, it stays silent with `ignored` `tv`, so one added word does not turn TV lines into alerts. Urgent stays rules-only. Other open caregiver screens and `/backstage` get `safety_word` and show the new word ([architecture.md](architecture.md#the-3-interfaces-locked-in-the-first-15-minutes)).
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
- **Safety words:** the card lists the built-in urgent words. A + chip at the end of that list adds one more (see M2). Built-in words stay.
- **Ask Sino about Lola** is a Should item after the freeze (see below), not MVP.

### M6. Urgent chime (Donita)

On urgent, the hub speaker plays a loud chime so anyone in the house hears it. The caregiver phone's red card is the second channel. Lola's screen never shows red. The `afplay` command and the 1:00 AM test are in [hub-chime.md](hub-chime.md).

### M7. Behind-the-scenes screen (Viviene)

Judges see the local AI decide. Each utterance is one row: transcript → rule hit or model → action + confidence + reason → ms. A dropped row covers a junk-line drop and a TV line Sino ignored. A running counter reads `TV lines ignored: N`. Also on this screen: an **OFFLINE** badge, the health light, the hidden "listen now" button, the typed-question box, the T5 badge in [mvp-plan.md](mvp-plan.md), and a line when the caregiver adds a safety word. Fields: [architecture.md](architecture.md#backstage-proof). Hidden from families.

### M8. Demo seed data, `seed.json` (Troy + team)

What `brain/seed.json` holds today: **6 questions** (`nasaan-si-nanay`, `nasaan-si-joy`, `sino-ka`, `nasaan-ako`, `gusto-ko-nang-umuwi`, `meal-check`), each with Tagalog and English phrasings and a `speaker`. `reply_audio` points at Joy's recordings in `brain/media/` for the four comfort questions and the three meal variants. `sino-ka` `by_person` points at Troy's, Joy's, and Donita's own lines (`sino-ka-troy-reply.m4a`, `sino-ka-joy-reply.m4a`, `sino-ka-donita-reply.m4a`); that question's top-level `reply_audio` stays empty, and every `photo` stays empty. `meal-check` also has `dynamic` `meal` and `replies` for `ate`, `ate_repeat`, and `unknown`; the top-level `reply_audio` and `photo` stay the fallback. Disclosed in the README as demo data.

Not in `seed.json` yet: the household name (Lola Cora) and earlier log entries (the T7 fake log lives in `brain/tests/ask_cases.json`). A meal is not a seed row. The caregiver's tap is a `meal_logged` line in the decisions log. The urgent, medication, and TV words live in `brain/decide.py`, not in the seed. Words the caregiver adds live in `hub/data/safety-words.json` and are merged when `decide()` runs.

**Recordings still needed (TODO):** photos. The three "Sino ka?" lines are recorded in `brain/media/` (`by_person` for troy, joy, and donita). Joy's four replies and three meal clips are recorded there too. A "Sino ka?" miss still uses the empty top-level `reply_audio`.

| Question | Reply (recorded by a teammate) | Speaker | Why |
|---|---|---|---|
| "Nasaan si Nanay?" (Lola's late mother) | "Ma, kwento mo nga ulit si Nanay mo." | Joy | Validation: invites the memory, no correction, no false claim. Recorded |
| "Nasaan si Joy?" | "Nasa trabaho pa ako, Ma. Uuwi ako mamaya, kain ka muna." | Joy | Joy is alive and at work, so this is true. Recorded |
| "Sino ka?" | "Lola, ako 'to, si Troy. Pamangkin mo. Ito tayo nung pasko." Troy, Joy, and Donita each have their own line in `by_person`. | Troy | A high-confidence face match plays that person's line ([demo.md](demo.md)). On stage, Troy then talks to "Lola" in person. There is no live call. Recorded. Photos not recorded yet |
| "Nasaan ako?" | "Dito ka lang, Ma. Kasama mo ako." | Joy | She is here with Joy. No room and no destination. Recorded |
| "Gusto ko nang umuwi" | "Ma, dito muna tayo ha." | Joy | Does not promise a trip home. Recorded |

## Should (after the 3:30 AM freeze)

- **Ask Sino about Lola (T7).** A registered person asks on the caregiver phone, in their own words. `answer_about_lola(question, log)` in `brain/ask.py` (merged, PR #11) picks one intent: `how`, `saying`, or `where` (rules first; Qwen only picks the intent when `SINO_MODEL=ollama`). Code builds the answer from the log: counts, her exact words, and the last urgent alert, ending with "Not a diagnosis." "Where is she" answers from a recorded clip when one was scanned ahead of time: "Huling nakita sa recording: sala (clip 0:42)." It names the room the recording showed, never where she is now. The caregiver snapshot is labeled "RECORDED CLIP · DEMO". With no detection, the answer stays "Walang camera sagot; hindi ko hulaan ang kwarto." and the caregiver gets a quiet card: "Hindi ko sigurado kung nasaan si Lola. Pakitingnan." Medication questions get no answer. It never invents a mood or a medical read. Lola's iPad is not this conversation. The `/caregiver` screen is still to wire; the socket events and the recorded-clip fields are in [architecture.md](architecture.md#the-3-interfaces-locked-in-the-first-15-minutes).
- **Meals check (T4m, in review).** The caregiver taps "Kumain na". That tap is the only source for whether she ate. `decide()` stays stateless and returns comfort `meal-check` for "Kumain na ba ako?" and the other phrasings in the seed. Medication still wins: a line with "gamot" plus "kumain" goes to the caregiver as medication, as before. Urgent still wins over everything. `server.py` reads the latest `meal_logged` line (broken jsonl lines are skipped) and picks the clip. The window is `MEAL_WINDOW_H`, default 3 hours.
  - **Meal logged within 3 hours, and she has not asked about food since that meal:** play `ate`. Joy: "Oo Ma, kumain ka na kanina. Busog ka pa ba? Gusto mo ng tubig?" No time and no dish.
  - **Same window, and she already asked about food since that meal:** play `ate_repeat`. Joy turns to how she feels and does not correct her again: "Busog ka pa ba, Ma? Gusto mo ng tubig o meryenda?"
  - **No meal logged, or the last one is older than 3 hours:** play `unknown`. Joy: "Gutom ka ba, Ma? Sasabihan ko si Ate, sandali lang ha." The caregiver gets a quiet yellow card: "Lola asked if she's eaten. No meal logged."
  - **Never say she has not eaten** ("hindi pa" / "not yet"). A missing log means we don't know, not that she didn't eat.
  - Food asks since that meal are on the same log, so "how is she" can count them ("asked about food 4× after lunch").
- **Clock answer:** recorded time clips for "Anong oras na?" (the big clock is already on Lola's screen).
- **Add-on (b) recorded clip demo (Troy).** "Nasaan si Lola?" reads clips already on the hub (`brain/clips/media/<room>.mp4`, also `.mov` and `.webm`), scanned in the background before anyone asks. OpenCV's HOG people detector keeps the last frame where a person showed twice in a row, at or above `CLIP_HOG_MIN`. Across rooms, the later sighting wins (file modified time plus the clip offset). The answer is past tense: "Huling nakita sa recording: {room} (clip m:ss)." The caregiver phone gets that frame from `GET /clips/snapshot`, labeled "RECORDED CLIP · DEMO". Footage stays on the hub, frames stay in memory, and Lola's screen never gets the snapshot. Live cameras, streams, and the door alert stay cut. If it is not reliable on the demo clips by 5:00 AM, it goes back to the next-steps slide.
- **Add-on (a) face match (T6, Troy; not built yet).** Starts only after the core runs end to end on the hub (W1) and T5 passes there, after the 3:30 AM freeze, with a hard stop at 5 AM. One frame on demand: when "Sino ka?" fires, Sino grabs **one** frame (no continuous stream, no polling loop; `POST /face/frame` is called once per trigger). OpenCV YuNet detects and SFace recognises (a few MB, hub CPU) against 3 family members enrolled on the hub (troy, joy, donita). A family member's line plays **only on a high-confidence match**; otherwise Troy's seeded line plays, never the wrong relative. Enrollment photos are gitignored; frames stay in memory only. If the hub starts swapping, fall back to `qwen2.5:1.5b`. The iPad still never quizzes Lola, and the reply plays through the normal reply screen (no face-match frame, A4 stays cut).
- **Daily recap:** counts and times computed by code only, no AI phrasing ("Asked about Nanay 6×, mostly 4 to 6 PM. 1 urgent alert at 5:15 PM."). Marked "not a diagnosis." The caregiver can ask "Kamusta si Lola?" or "Ano ang mga tanong niya?" and Sino pulls that same log up. "How is she" is the log. It is not a diagnosis.

## Cut tonight (moved to Next steps)

Decided by Troy, Sat 2:00 AM ([../NOTES.md](../NOTES.md#decision-log)); (a) face match was un-cut at Sat 3:23 AM and (b) the recorded-clip demo was un-cut at ~4:30 AM. Both are Should items above. Live CCTV stays cut. The rest are not built. If asked, they are next steps.

1. **(a) Face match:** un-cut Sat 3:23 AM, now a Should add-on (T6). Only the iPad face-match frame (A4) stays cut. Without a high-confidence match, "Sino ka?" plays Troy's seeded photo and line.
2. **(b) Live "Nasaan si Lola?" on CCTV.** Stays in next steps (D7, V5), and so does the door alert. The recorded-clip demo is the Should item above. It does not open a camera.
3. **(c) Voice ID.** Cut earlier. No speaker match, no voice samples, no voice panel on `/backstage`.
4. **Live call on the house Wi-Fi.** Cut. Calling a registered person is a next step.

**Distress rule:** the iPad never quizzes Lola ("Who is this?") and never announces names as a test. For "Sino ka?" it shows the photo and plays the recorded line.

## Next steps (not building)

Recording replies from family abroad (OFW), learning which voice calms her best, visitor recognition, "Nasaan si Lola?" from a live camera (person detector and last-seen log), voice ID, calling a registered person on the house Wi-Fi (WebRTC, no internet), calling a registered person over the internet (opt-in), a door alert (the hub notices Lola leaving and chimes), Lola's own device for calling and locating her outside the house (needs GPS and a network, opt-in), a native iPad app, cheaper hubs.

## A day with Sino (example story for the pitch)

1. **Sunday, setup (about 10 min):** Ate Joy adds "Nasaan si Nanay?", "Nasaan si Joy?" and "Kumain na ba ako?" with two phrasings each, records her replies, adds her photo, and tests once.
2. **4:30 PM:** Lola asks "Si Nanay, asan?" Ate Joy's photo and voice answer: "Ma, kwento mo nga ulit si Nanay mo." Lola starts talking about her mother.
3. **4:50 PM:** "Nasaan yung aso?" is not in the seed. Sino stays quiet with Lola and adds a quiet yellow card. The family adds it in `/setup`; the next ask plays their voice. Repeats before that reply group on the card ("Lola asked about the aso 3×"). This is the live demo question ([demo.md](demo.md)). "Nasaan si Joy?" stays in the seed.
4. **5:15 PM:** "Masakit dibdib ko." No comfort clip. The hub chimes loudly, and a red card shows Lola's exact words.
5. **5:30 PM:** a teleserye plays a longer dialogue that contains "nasaan si nanay" mid-sentence, not as the whole line. The matcher misses, the model says chatter, Sino stays silent, and `/backstage` counts it under `TV lines ignored` (that count on a model decision needs the model path to set `ignored` to `tv`: TODO, see [architecture.md](architecture.md#backstage-proof)). She can still ask "Nasaan si Nanay?" plainly and get the comfort reply.
6. **6:00 PM:** the internet is down. Sino keeps working, because everything runs inside the house.
7. **9:00 PM:** Joy asks Sino, "Kamusta si Lola?" and "Ano ang mga tanong niya?" Sino pulls the log: "Asked about Nanay 6×, mostly 4 to 6 PM. 1 urgent alert at 5:15 PM." Not a diagnosis. If she asks where Lola is, a scanned recording answers in the past tense ("Huling nakita sa recording: sala (clip 0:42).") and the caregiver sees that frame labeled "RECORDED CLIP · DEMO". It never says she is there now. With no detection, Sino says it has no camera answer and the caregiver gets a quiet card.

## UX rules

- **Lola's screen:** big clock, idle photo, full-screen photo with the voice. No menus, no text input, calm colors, never red.
- **Caregiver app:** one-handed, one action per card, Taglish labels. Only red makes sound.
- **Behind-the-scenes screen:** hidden from families; dense is fine.
- Every screen has empty, loading, result, and error states ([../../AGENTS.md](../../AGENTS.md)).
