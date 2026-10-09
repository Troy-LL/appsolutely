# Sino design system

**Owner:** Viviene.

> **Spec alignment (Sat 2:20 AM).** This file is the visual source of truth. Where it disagrees with the product spec ([README.md](README.md), [features.md](features.md), [architecture.md](architecture.md)), the spec wins on *behavior* and this file wins on *look*. Known gaps, to resolve before building the affected screen:
>
> 1. **"Call Lola / Tawagan si Lola" on the urgent card.** Lola has no phone and calling is cut tonight ([features.md](features.md) Next steps). Until decided, the urgent card's one action is **"Mark as read / Nabasa na"**. TODO: Troy.
> 2. **Urgent sound.** The spec's first urgent channel is the **hub chime** ([hub-chime.md](hub-chime.md)); the phone card is second. "No chimes on the iPad" still holds: the chime plays from the hub, not the iPad.
> 3. **Setup length.** Quick setup is 5 steps (question, two phrasings, hold to record, photo, test), not "Step 3 of 9".
> 4. **"No ask anything box" vs. Ask Sino about Lola (T7).** T7 lets a registered person ask about Lola on the caregiver phone, with answers built from the log. Design it as a few fixed question chips ("Kamusta si Lola?", "Ano mga tanong niya?", "Nasaan si Lola?"), not a free-text box. TODO: Ayen + Viviene.
> 5. **ReceiptStrip vs. /backstage.** The judges' screen also needs dropped/silent lines, "TV lines ignored: N", the OFFLINE badge from a real check, the health light, and the hidden "listen now" + typed question ([architecture.md](architecture.md)). Add a ⚪ Silent node style (ink outline on paper). Latency is in seconds per this file.
> 6. **AI-suggested phrasings** (KnowsList) and **tapping a frame to see replies** (MemoryWall) are not in the MVP. Skip them tonight.
> 7. **Fonts** must be bundled locally in `fonts/` (offline). TODO: add the woff2 files.


Sino · Appsolutely · v6, the sala

Sino is a small home box that answers a lola's repeated questions in her family's own voice. Its world is the **sala**: the family living room, drawn flat like a toy house, where every memory hangs on the wall in a picture frame. Two goals decide every screen:

1. **Elder-friendly and calm.** Lola has dementia. The caregiver is tired and often one-handed. Nothing may confuse, startle or hurry either of them. One clear object at a time, one clear action per card.
2. **Clean, with a face of its own.** Flat 2D, confident ink outlines, the document's five colours and nothing else. The picture frame is Sino's signature: no other app hangs its people on a wall.

There are three surfaces:

- **Lola's iPad** (`LolaScreen`, `MemoryFrame`): one wall of the sala. A clock while Sino waits, one framed memory when family answers.
- **The caregiver phone and setup** (`MemoryWall`, `LogEntry`, `RecordReply`, `Button`, `TextScale`, `StepIndicator`, `KnowsList`): the sala itself. The family hung on the wall, today's moments as cards beneath.
- **The technical view** (`ReceiptStrip`): hidden from families.

## Principles

1. **One thing at a time** on Lola's screen, like one frame on a wall.
2. **Always 2D.** Flat fills, ink outlines, flat ink shadows. No gradients, glows, blur, glass, 3D or realistic textures.
3. **Only the stated palette.** Paper, ink, green, amber, red, and white for text on green or red. No tints, no pastels, no opacity tricks, no new hues.
4. **Every person is framed.** A family photo never appears without a `MemoryFrame`.
5. **Never `red` for Lola.** Red exists only on the caregiver phone, only for urgent.
6. **Never "I didn't understand."** If Sino is unsure, Lola's screen returns to Waiting, the family's optional holding clip may play, and the caregiver gets a card.
7. **Status is always mark + word + colour.** Never colour alone.
8. **Name the person and the time.** No "Oops", no "Something went wrong."
9. **No timers, countdowns or timeouts**, anywhere.
10. **Everything is visible and undoable.** Every action has Undo. Deleting shows what will be lost first.
11. **Offline by construction.** No external links, no CDN fonts, no remote images. Load the files in `fonts/` locally with `font-display: swap`.

## Content fundamentals

- Every UI string comes in English and Tagalog (Bisaya later), from one strings file per language, never hardcoded in a screen. Pair them where space allows: "Simulan / Start", "Bawiin / Undo".
- Speak like family in the sala: "Magandang hapon, Joy." "Pamilya ni Lola." "Add someone." Name people the way Lola does (Ate, Kuya, Tita).
- Buttons are verbs: **Record a reply / Mag-record ng sagot**, **Call Lola / Tawagan si Lola**, **Remove / Alisin**, **Delete / Burahin**.
- Write times out in words: "5:15 in the afternoon / ng hapon", never "PM". No abbreviations anywhere.
- Name the person and quote them: `She asked: "Where is the dog?"`, `"Where's Mom?" Ate Joy's voice played.`
- Lola is addressed with "po": "Nandito lang po kami. / We're right here.", "Nakikinig po ako. / I'm listening."
- Setup copy reassures: "You can go back and redo anything, anytime. / Pwedeng bumalik at ulitin anumang oras."
- No emoji. Status marks are typographic: ✓ Answered, ● Needs you, ▲ Urgent.
- Names, photos and lines in examples are placeholders. The real family's photos, voices and words replace them; emotionally sensitive wording is written by people, not generated.

## Colour

Five colours, each with one job, plus white only as text on green or red. Exactly as the source document states them; nothing is tinted, lightened or added.

| Name | Hex | Job in the UI | In the sala illustration |
|---|---|---|---|
| `paper` | `#F4EDE0` | Every background; every frame's mat | The wall |
| `ink` | `#2B2420` | All text, all outlines, every frame, the flat shadow | Frames, floor, picture rail |
| `green` | `#2F5E4E` | Main actions; "Answered" | The sofa |
| `amber` | `#E9A83A` | "Needs a person": marker or card tab, never text | The lamp |
| `red` | `#C23232` | Urgent, caregiver phone only | Never |
| `white` | `#FFFFFF` | Text on green or red fills only | Never |

- Lola's screen is **`ink` on `paper` only**. No green, amber or red there, not even as decoration. The 36px mark on Waiting is the one recorded exception (see LolaScreen).
- Colour on a card lives in three places only: the 10px tab on its left edge, its status mark, and (for urgent) the whole card turning red. Card bodies stay `paper`.
- Every amber shape carries an `ink` outline, because amber on paper is only 1.8:1.
- In illustration, green and amber are furniture, never a signal; red never appears, so it always means urgent.
- The official mark (`assets/brand/sino-logo.png`) is filled with the same two colours. Opaque pixels sample as green `#2F5E4E` and amber `#E9A83A`, matching the `green` and `amber` tokens. Tokens are unchanged.

| Pair | Ratio | Use |
|---|---|---|
| `ink` on `paper` | 13.1 : 1 | All text, including Lola's screen |
| `white` on `green` | 7.4 : 1 | Buttons |
| `green` on `paper` | 6.4 : 1 | Answered mark and word |
| `white` on `red` | 5.5 : 1 | Urgent card, 22px or larger |
| `ink` on `amber` | 7.4 : 1 | Text on an amber fill |
| `red` on `paper` | 4.7 : 1 | **Not for text** |
| `amber` on `paper` | 1.8 : 1 | **Never** text or a lone signal; always ink-outlined |
| `ink` on `green` | 2.1 : 1 | **Never** |

## Type

Two families only.

| Role | Face | Family token | Where |
|---|---|---|---|
| Headings | Fredoka | `heading` | Everything that titles, names, labels or counts: the wordmark, greetings, setup questions, section titles, status words, name plates, step counts, times, tags, chips and totals |
| Text | DM Sans | `text` | Everything read as a sentence: Lola's reply lines, card quotes, helper copy, button labels, list rows |

- **The rule:** if it is a heading, a name, a label, a number or a time, it is Fredoka. If it is a sentence, it is DM Sans. When in doubt, ask "would this be bold in a newspaper?"; if yes, Fredoka.
- Headings: `heading-xl` 56, `heading-l` 35, `heading-m` 22, `heading-s` 16 (SemiBold); `eyebrow` 14 for step counts and dates; `time-l` 56 for Lola's clock time and `time-m` 22 for log times; names in `name-tag` 16, `name-m` 22, `name-l` 35 (Medium). Fredoka is for a few words at a time, never for sentences.
- Text: `text-l` 35, `text-m` 22, `text-s` 16, `label` 16 Bold for buttons, `log-s` 15 with tabular figures. Left-aligned, never justified, short lines.
- **Wordmark:** "Sino" in Fredoka SemiBold, ink on paper, when the name is set in type. The official drawn mark is `assets/brand/sino-logo.png` (house roofline, green word, amber dot). Do not invent another mark.
- Lola's screen uses `text-l` and `text-m`, names in `name-m`. The **Bigger** option swaps in `text-l-big` 44 and `text-m-big` 28 (names 28 / 44); the family picks it on the real iPad.
- The caregiver app scales every style by A / A+ / A++ (`scale-a`, `scale-a-plus`, `scale-a-plus-plus`). No pinch gestures.
- Both faces are SIL OFL.

## The picture frame

The `MemoryFrame` is the brand. It is how Sino shows a person, everywhere.

- An `ink` moulding (`frame` 8px; `frame-l` 12px on Lola's screen) with `r-frame` corners, a `paper` mat (`mat`), and the photo inside with an ink hairline.
- A name plate under it: a small `paper` tag with an ink outline, in Fredoka.
- On the caregiver wall, frames sit on `shadow-flat` and tilt by at most 2 degrees, alternating, so the wall looks hung by hand. On Lola's screen, frames hang straight, without a shadow.
- No photo yet: the name or first letter in Fredoka inside the empty mat. Add someone: a dashed frame with a +.
- The photo brings all the colour of real life; the frame stays ink. No filters, stickers or borders in other colours.

## Shape, line and space

- **Line:** every object has an `outline` (2px) ink border. Pictures get the heavier `frame` moulding.
- **Shadow:** `shadow-flat`, a solid 4px ink offset with no blur, under cards, buttons and frames on the caregiver phone; `shadow-flat-s` (2px) under small tags. Never on Lola's screen.
- **Radius:** `r-card` 18 for cards and sheets, `r-button` 14 for buttons, `r-frame` 6 for frames, `r-photo` 2 for photos, `r-round` for the clock, ring, markers and icon buttons.
- **Space:** a 4px base. `space-4` (16) card padding and between frames, `space-6` (24) phone gutter, `space-8` (32) between sections, `space-12` (48) around Lola's screen.
- **Buttons:** chunky, `green` with `white` labels, ink outline, `shadow-flat`, at least `tap-min` (48px). Pressed, a button drops onto its shadow. Focus: a `focus-width` ink ring, `focus-offset` away.

## Motion

Only three things move:

- A **400ms fade** between Lola's states (`--fade: 400ms`).
- The **breathing ring** while Sino listens: a thick ink ring, 4s cycle, scale 1 to 1.05 (`--breathe: 4s`).
- A button dropping onto its shadow when pressed.

With reduced motion on: no fade, a still ring, a colour-only press. No bouncing, wobbling frames, ticking clock hands, tap hints, countdowns or auto-dim. These values are not tokens here (the system has no motion family).

## Lola's iPad: one wall of the sala

The family taps **Simulan / Start** once. Lola never touches anything: Guided Access is on, so touches and the home gesture do nothing.

| State | On screen |
|---|---|
| Waiting · Naghihintay | A flat ink wall clock, the time in `time-l` with "ng hapon / in the afternoon" in `heading-m`, then "Nandito lang po kami. / We're right here." |
| Listening · Nakikinig | The breathing ink ring and "Nakikinig po ako. / I'm listening." |
| Answer · Sagot | One large `MemoryFrame`, the speaker's name in `name-m`, the reply line in `text-l`. Stays until a new question. |
| Urgent | **Nothing changes** on the iPad. The alert goes to the caregiver phone only (open decision D1). |
| Unsure or silent | Back to Waiting. No text. The holding clip plays once if the family recorded one and left it on (D2). |

- One object on the wall at a time, with wide `space-12` margins.
- **Photo:** one face, front-facing, at least 800px on the short side, cropped 4:5 in a preview the family confirms. An unconfirmed crop is never saved.
- **No photo yet:** the name in `name-l` inside the empty frame. Never a gray box, a silhouette or a stock face.

### Sound

- Every sound Lola hears is a family recording. No chimes, beeps, confirmation tones or effects on the iPad.
- Playback fades in over 300ms and never exceeds the volume set in test-together.
- One clip at a time. If Lola speaks during a clip, it finishes; it is never cut off or restarted.
- The recording screen suggests "about 10 seconds or less", with no cutoff and no timer.
- The caregiver phone has its own sound: urgent alerts repeat until read, even in quiet hours. Answered and needs-you entries are visual only by default.
- **Holding clip (optional):** one short recording made once in setup in the family's words ("Sandali lang, Ma, nandito lang ako."). It never answers the question or promises anything, plays only when Sino is unsure, and has an off switch.

## Caregiver phone: the sala

The home screen reads top to bottom:

1. The greeting in `heading-l` ("Magandang hapon, Joy") and one line summing up the day.
2. **Pamilya ni Lola** (`MemoryWall`): the family hung in frames under a picture rail; the voice Lola heard last hangs first.
3. **Today** (`LogEntry`): one card per moment, newest first. At most three things per card: **what, when, one button.**

- **Answered · Nasagot na:** `green` tab, ✓ and the word in `green`. Button: Undo / Bawiin.
- **Lola needs you · Kailangan ka ni Lola:** `amber` tab and an ink-outlined amber ●. Button: Record a reply, which opens `RecordReply`.
- **Urgent:** ▲ the whole card turns `red` with `white` text. Pinned on top until someone marks it read and always the loudest thing on screen. Button: Call Lola.
- **Setup:** one question per sheet: the step count, ink-outlined segments filled green when done (they count steps, never time), the question in `heading-l`, Back and Next always visible.
- **What Sino knows · Ano ang alam ni Sino:** every question (with its number of phrasings), every safety word and the log count, each row with Remove or Delete. AI-suggested phrasings arrive unchecked. Nothing is added silently.

## Technical view

Hidden from families, but still made to be read. **Sino's log** (`ReceiptStrip`) prints the day as a torn paper receipt: the date and an "Offline all day" tag on top, then a timeline with one row per decision (the time in Fredoka, a green ✓, amber ● or red ▲ node, the words heard in large bold type, and chips for the route, a 10-block confidence meter and the seconds it took), and the day's totals at the bottom like a receipt's sum.

## Illustration and iconography

- The sala is drawn, never photographed: flat shapes, ink outlines, the five colours. Wall (`paper`), picture rail and floor (`ink`), sofa (`green`), lamp (`amber`), frames (`ink`).
- Illustrations appear only on the cover, onboarding and empty states ("No moments yet today"), never on Lola's screen and never behind content.
- Icons are simple ink glyphs inside round paper buttons with an ink outline (back, play, start over), always with a text label for screen readers. Status uses ✓ ● ▲, never emoji.
- Inspired by toy-house games, but no characters, mascots, props or art are copied from any of them. No people are drawn; the only faces are the family's own photos.

## What we do not do

- No pastels, tints, opacity fades or colours outside the six.
- No gradients, glows, blur, glass, 3D or realistic textures.
- No unframed photos, stock faces, silhouettes or avatars made of initials in coloured circles.
- No red outside the urgent card. No colour on Lola's screen, except the 36px mark on Waiting (see LolaScreen).
- No grid of identical feature cards, no dashboard of numbers, no "ask anything" box.
- No timers, countdowns or timeouts. No "Oops".
- No irreversible action without showing what will happen, with Undo.
- No hidden memory: everything lives in "What Sino knows".

**Review every new screen** with the silhouette test (reduced to ink outlines, does it still look like the sala, with frames on a wall?), a removal pass (one thing fewer is usually calmer) and the reason test (each choice ties to Lola, the caregiver or the family's memories).

## Not synced

- Built from the attached `Sino_Design_System.md`; the `Troy-LL/appsolutely` repository was not readable from this session.
- v5 sala direction (`MemoryFrame`, `MemoryWall`, `RecordReply`, the flat shadow, spacing and radii, Fredoka and DM Sans) is a design change made here; the palette is the source document's, unchanged. The source document still names Atkinson Hyperlegible, Literata and IBM Plex Mono.
- Not tokens: `--fade` and `--breathe` (no motion family).
- Fonts are SIL OFL releases from Fontsource 5.3.0, latin subset: Fredoka 500 and 600; DM Sans 400, 500 and 700.
- Components are static renditions, not built from code.

---

## Tokens

### Color

| Token | Hex | Usage |
|---|---|---|
| `paper` | `#F4EDE0` | The sala wall: every background, and the mat inside every picture frame. Ink text 13.1:1. |
| `ink` | `#2B2420` | All text, every outline, every picture frame, the floor line and the flat offset shadow. The only text colour Lola ever sees. Never text on green (2.1:1). |
| `green` | `#2F5E4E` | Main actions and the Answered mark and word (6.4:1 on paper). In illustration, the sofa. Text on a green fill is white. |
| `amber` | `#E9A83A` | Needs a person: the ● marker or a card's side tab, always with an ink outline; never text (1.8:1 on paper). In illustration, the lamp's light. Ink text on an amber fill is 7.4:1. |
| `red` | `#C23232` | Urgent only, caregiver phone only: the solid urgent card with white text at 22px or larger (5.5:1). Never in illustration, never on Lola's screen, never text on paper. |
| `white` | `#FFFFFF` | Text on green (7.4:1) or red (5.5:1) fills only. Nothing else. |

### Type

| Font file | Family | Weight |
|---|---|---|
| `fonts/Fredoka-Medium.woff2` | Fredoka | 500 |
| `fonts/Fredoka-SemiBold.woff2` | Fredoka | 600 |
| `fonts/DMSans-Regular.woff2` | DM Sans | 400 |
| `fonts/DMSans-Medium.woff2` | DM Sans | 500 |
| `fonts/DMSans-Bold.woff2` | DM Sans | 700 |

| Family token | Stack |
|---|---|
| `heading` | `"Fredoka", "DM Sans", system-ui, sans-serif` |
| `text` | `"DM Sans", system-ui, sans-serif` |

| Style | Font | Size | Line height | Weight | Usage |
|---|---|---|---|---|---|
| `heading-xl` | Fredoka | 56px | 1.05 | 600 | The wordmark and the first onboarding screen. |
| `heading-l` | Fredoka | 35px | 1.15 | 600 | One per screen: the caregiver greeting or the setup question. |
| `heading-m` | Fredoka | 22px | 1.25 | 600 | Section titles and status words on cards. |
| `name-tag` | Fredoka | 16px | 1.2 | 500 | The name plate under a picture frame on the caregiver phone. |
| `name-m` | Fredoka | 22px | 1.25 | 500 | Speaker name under the frame on Lola's screen (28px with Bigger). |
| `name-l` | Fredoka | 35px | 1.2 | 500 | No-photo fallback on Lola's screen: the name alone in an empty frame (44px with Bigger). |
| `heading-s` | Fredoka | 16px | 1.25 | 600 | Small headings: row titles in the log, card kickers, tags such as OFFLINE. |
| `eyebrow` | Fredoka | 14px | 1.3 | 500 | Counters and labels above a heading: the setup step count, the date above the log. |
| `time-l` | Fredoka | 56px | 1.05 | 600 | The time on Lola's Waiting screen, under the wall clock (72px with Bigger). |
| `time-m` | Fredoka | 22px | 1.1 | 600 | Times that head a row in the log. |
| `text-l` | DM Sans | 35px | 1.35 | 400 | Lola's screen: the reply line. Ink on paper only. |
| `text-m` | DM Sans | 22px | 1.45 | 400 | Urgent text (never smaller), Lola's second lines. Scaled by A / A+ / A++ on the caregiver phone. |
| `text-s` | DM Sans | 16px | 1.5 | 400 | Card body, times, helper copy, list rows. Scaled by A / A+ / A++. |
| `label` | DM Sans | 16px | 1.25 | 700 | Button labels. |
| `log-s` | DM Sans | 15px | 1.6 | 400 | Detail lines in the technical log, with tabular figures. |
| `text-l-big` | DM Sans | 44px | 1.3 | 400 | Lola's Bigger option for text-l. |
| `text-m-big` | DM Sans | 28px | 1.4 | 400 | Lola's Bigger option for 22px lines. |

### Spacing

A 4px base. The sala feels tidy because things hang on a grid.

| Token | Value | Usage |
|---|---|---|
| `tap-min` | `48px` | Minimum height of every button and tappable row. |
| `space-1` | `4px` | Between a mark and its word. |
| `space-2` | `8px` | Between a frame and its name plate; stacked lines in a card. |
| `space-3` | `12px` | Between cards; between buttons. |
| `space-4` | `16px` | Card padding; gaps between frames on the wall. |
| `space-6` | `24px` | Phone side gutter; padding of the setup sheet. |
| `space-8` | `32px` | Between sections. |
| `space-12` | `48px` | Lola's screen margins; above the greeting. |

### Radius

| Token | Value | Usage |
|---|---|---|
| `r-frame` | `6px` | Picture frames: soft corners, like a toy frame. |
| `r-photo` | `2px` | The photo inside a frame's mat. |
| `r-card` | `18px` | Cards, sheets and the urgent card. |
| `r-button` | `14px` | Buttons and chips. |
| `r-round` | `999px` | The wall clock, the listening ring, markers, round icon buttons. |

### Border

Toy-house drawing: every object has a confident ink outline. Pictures are framed in ink.

| Token | Value | Usage |
|---|---|---|
| `outline` | `2px` | Every object: cards, buttons, markers, the clock, furniture. |
| `frame` | `8px` | The ink moulding of a picture frame on the caregiver phone (12px on Lola's screen). |
| `frame-l` | `12px` | The picture frame on Lola's screen. |
| `mat` | `8px` | The paper mat between frame and photo (12px on Lola's screen). |
| `focus-width` | `3px` | Keyboard focus ring, solid ink (13.1:1 on paper). |
| `focus-offset` | `2px` | Gap between an element and its focus ring. |

### Shadow

Flat, never blurred: an ink offset, like a cut-out sitting on the wall.

| Token | Value | Usage |
|---|---|---|
| `shadow-flat` | `0 4px 0 #2b2420` | Under cards, buttons and frames on the caregiver phone. Removed when a button is pressed. Never on Lola's screen. |
| `shadow-flat-s` | `0 2px 0 #2b2420` | Under small things: chips, name plates, markers. |

### Text scale

Text-size multiplier for the caregiver and setup screens. Never on Lola's screen, which has Bigger.

| Token | Value | Usage |
|---|---|---|
| `scale-a` | `1` | A, the default. |
| `scale-a-plus` | `1.25` | A+. |
| `scale-a-plus-plus` | `1.5` | A++. |

---

## Components

### MemoryFrame

A picture frame hanging on the sala wall: the signature object of Sino, holding one family member or one memory.

**Use** for every photo of a person, everywhere: on Lola's answer screen, on the caregiver's Memory wall, in setup when a photo is added. A photo never appears without its frame.

**The consumer provides** the photo (one face, 4:5, the crop the family confirmed), the name as Lola says it, and on the caregiver phone an optional line under it ("6 replies").

- The frame is `ink` (`frame` 8px, `frame-l` 12px on Lola's screen) with `r-frame` corners, a `paper` mat (`mat`), and the photo inside with `r-photo` corners and an ink hairline.
- The name plate is a small `paper` tag with an `outline` and `shadow-flat-s`, set in `name-tag` (Fredoka).
- On the caregiver wall, frames sit on `shadow-flat` and may tilt by 2 degrees (`sn-frame--tilt-l`, `sn-frame--tilt-r`) so the wall feels hung by hand; never more, never on Lola's screen.
- No photo yet: the first letter in Fredoka inside the empty mat. Add someone: a dashed `outline` frame with a + .
- Never a gray box, silhouette, stock face, sticker or filter. The photo is the colour; the frame stays ink.

### MemoryWall

The family whose voices Sino uses, hung as framed photos under a picture rail.

**Use** at the top of the caregiver home screen, right under the greeting. The caregiver's day starts with the people, not the machine.

**The consumer provides** each family member's `MemoryFrame` (photo, name, reply count) in the order the family chose, and an Add someone action.

- A `paper` wall with a single `outline` ink picture rail; frames hang `space-4` apart with alternating 2 degree tilts (left, straight, right).
- The person whose voice Lola heard last sits first. No badges, counters or dots on the frames.
- More than four people: the wall scrolls sideways; frames never shrink.
- Tapping a frame opens that person's replies.

### LogEntry

One card per moment in Lola's day: what happened, when, and one button.

**Use** for every event on the caregiver phone, under the Memory wall, newest first, `space-4` apart.

**The consumer provides** the kind (answered, needs-you, urgent), the time in words, the quoted line with the person named, and the one action.

- Card: `paper`, `outline` ink border, `r-card`, `shadow-flat`, with a 10px colour tab down the left edge. Status word in `heading-m`, time in `eyebrow` (both Fredoka), the quote in `text-s`.
- **Answered · Nasagot na:** `green` tab, ✓ and the word in `green`. Action: Undo.
- **Lola needs you · Kailangan ka ni Lola:** `amber` tab and an ink-outlined `amber` ●, the word in ink. Action: Record a reply.
- **Urgent:** the whole card turns solid `red` with `white` text at 22px or larger. Pinned on top until marked read; its alert sound repeats until then. Action: Call Lola.
- Colour never works alone: mark + word + colour. No tinted backgrounds: colour lives only in the tab, the mark and the urgent card.

### RecordReply

The recording card where a family member answers Lola in their own voice.

**Use** after Record a reply on a Needs-you card, and in setup for each question.

**The consumer provides** the question being answered, the live waveform, and play back, start over and save actions.

- A `paper` card with `outline` and `shadow-flat`. The question on top with the amber ● it came from.
- Waveform bars are ink-outlined paper; the part already recorded fills `green`.
- The record button is a big round `green` button with a `white` label; round icon buttons either side.
- The tip "about 10 seconds or less" is advice, never a limit: no timer, no countdown, no cutoff.

### Button

A chunky, ink-outlined button that sits on a flat ink shadow, like a toy you can press.

**Use** for every action on the caregiver phone and in setup. Lola's screen has no buttons.

**The consumer provides** a verb label from the strings file ("Call Lola / Tawagan si Lola"), never "OK" or "Submit".

- Primary: `green` fill, `white` `label` (DM Sans Bold), `outline` ink border, `r-button`, `shadow-flat`, at least `tap-min` tall. One per card.
- Quiet (`sn-btn--quiet`): `paper` fill, `ink` label. Undo, Back, Remove.
- Icon (`sn-icon-btn`): a round `paper` button with an ink outline for back, play and start over; always with an `aria-label`.
- Pressed: the button drops 4px onto its shadow. Focus: a `focus-width` ink ring at `focus-offset`.
- Inside the urgent card the button is quiet (paper on red).

### LolaScreen

Lola's iPad as one wall of the sala: a clock while Sino waits, one framed memory when family answers.

**Use** full-screen on the iPad after the family taps Simulan / Start once, with Guided Access on. Lola never touches it.

**The consumer provides** the current state, the time in words, and for an answer the family photo (4:5, confirmed crop), the speaker's name and the reply line, all from the strings file.

- `ink` on `paper` only. Wide `space-12` margins, one object on the wall at a time.
- Waiting: a flat ink wall clock (no ticking, no second hand), the time in `time-l` and "ng hapon / in the afternoon" in `heading-m`, both Fredoka.
- Listening: a thick ink ring breathing on a 4s cycle (scale 1 to 1.05); static with reduced motion. States fade in 400ms.
- Answer: one `MemoryFrame` (`frame-l`, straight, no shadow), the name in `name-m` (Fredoka), the reply in `text-l`.
- No photo yet: the name in `name-l` inside the empty frame. Never a gray box, silhouette or stock face.
- No green, amber or red on this screen. Urgent changes nothing here. No buttons, hints, countdowns or auto-dim.
- Waiting is the one exception: a 36px official mark in the corner. It is not faded (this file forbids opacity tricks) and it is absent from Listening and Answer, so it does not sit with the clock or a reply. A full-colour mark is still outside the ink-on-paper rule above; the corner placement is the calmest fit, not a new colour on Lola's wall.

### StepIndicator

The setup sheet: where you are, the one question, and the way back.

**Use** for each one-question setup screen.

**The consumer provides** the step number, the total, and the question in both languages.

- A `paper` sheet with `outline` and `shadow-flat`. "Hakbang 3 ng 9 · Step 3 of 9" in `eyebrow` (Fredoka), then ink-outlined segments filled `green` when done. They count steps, never time.
- The question in `heading-l` (Fredoka), its Tagalog line and a reassurance line in `text-s`.
- Back (quiet) and Next (primary) always visible. One question per screen.

### TextScale

Three chunky buttons that set the text size of the caregiver and setup screens.

**Use** in setup and the caregiver app. Never on Lola's screen, which has its own Bigger option.

**The consumer provides** the current scale and applies it to every caregiver style: A = `scale-a` (1), A+ = `scale-a-plus` (1.25), A++ = `scale-a-plus-plus` (1.5).

- Paper buttons with ink outlines and Fredoka labels (A, A+, A++ are headings, not sentences); the chosen size is pressed flat and filled `ink` with `paper` text, with `aria-pressed`.
- No pinch gestures and no slider.

### KnowsList

"What Sino knows": the visible, editable list of everything Sino remembers.

**Use** as its own caregiver screen. Nothing Sino uses may live outside it.

**The consumer provides** every question with its number of phrasings, every safety word, the log count, and Remove or Delete actions.

- One `paper` card with `outline` and `shadow-flat`, rows ruled by ink lines, `text-s`, a quiet button per row. Title in `heading-m`.
- AI-suggested phrasings arrive unchecked; the caregiver ticks, edits or removes them. Nothing is added silently.
- Delete first shows what will be lost, then offers Undo.

### ReceiptStrip

Sino's log: the day printed as a torn paper receipt, with each decision on a timeline you can read at a glance.

**Use** only in the hidden technical view, for the team and anyone checking how Sino decided. Families never see it.

**The consumer provides** the date, whether Sino stayed offline, and for each decision: the time, what was heard (with the trigger word if one fired), the route (comfort reply, sent to caregiver, urgent), the confidence (0 to 1) and how long it took.

- The strip: `paper` with ink side edges and zigzag torn ends drawn in SVG (2D, no shadow), a dashed ink rule under the header and above the totals.
- Header: the date in `eyebrow`, "Sino's log" in `heading-m`, and an ink "Offline all day" tag with a green dot.
- Each row: the time in `time-m` (seconds smaller underneath), a round node on an ink timeline, the kicker ("Heard", "Safety word") in `heading-s`, and the words heard in 22px DM Sans Bold, so the row reads like a sentence.
- Nodes and route chips use the signal colours: `green` ✓ comfort reply, `amber` ● sent to caregiver, `red` ▲ urgent; always mark + word + colour. A trigger word gets an `amber` underline band.
- Confidence is a 10-block ink meter plus words ("91% sure"); time taken is written in seconds, never "ms".
- The totals at the bottom, like a receipt's sum: Answered, Waiting and Urgent counts in Fredoka.
- Every chip, count, time and kicker is Fredoka; the words heard and detail lines are DM Sans.

---

## Open decisions

People decide these, not the document. Until decided, build to "Today".

- **D1 · Urgent and Lola's screen.** Today: nothing changes, so she isn't frightened. Risk: silence while she is in pain. Decide with a caregiver of someone with dementia, and decide whether a holding clip should ever play here.
- **D2 · Holding clip.** Yes or no, and the exact words, written by the family.
- **D3 · Lola's default text size.** `text-l` (35) or Bigger (`text-l-big`, 44). Test on the real iPad.
- **D4 · Night variant.** Worth building (paper and ink swapped, clock only), or leave the family to dim the iPad. Not a theme here until decided.
- **D5 · Default volume.** Set during test-together; confirm with someone who knows her hearing.

### Before shipping, check

- Every pair in the contrast table, with a contrast checker
- Fonts bundled; the full flow works with the network off
- Lola's five states and the urgent band on the real iPad and phone
- Reduced motion on: no fade, static ring, colour-only button press
- Audio tested at the real distance and volume; no chime or beep anywhere on the iPad
- Guided Access on; touching the iPad does nothing
- Text size (35 vs Bigger) checked on the real iPad from Lola's seat
- No-photo fallback shown once on purpose
- Every string comes from the language file
- Wording and the answer screen shown to someone over 60, noting what confuses them
- Fonts and any other existing assets listed in the README
- Fredoka names and DM Sans lines read from Lola's seat at 35 and Bigger
- Frames on the caregiver wall tilt no more than 2 degrees, and never on Lola's screen
- Every screen uses only paper, ink, green, amber, red and white, with no tints or gradients

### How Sino applies the 12 rules for 60+

| # | Rule | Sino |
|---|---|---|
| 1 | Adjustable size | A / A+ / A++ in setup and the caregiver app. No pinch gestures. |
| 2 | Text formatting | Line height 1.4 to 1.5, no justified text, short lines, generous space. |
| 3 | Color coding | Mark + word + color always (▲ Urgent, ● Needs you, ✓ Answered). |
| 4 | Contrast | At least 4.5:1 everywhere, about 13:1 on Lola's screen. |
| 5 | Show what's tappable | Chunky buttons with a 2px ink outline and a flat ink shadow, a verb label, at least 48px; pressed, they drop onto the shadow. |
| 6 | External links | None. The app is offline. |
| 7 | Where am I? | "Step 3 of 9" and a clear title on every setup screen. |
| 8 | Animations | Only the breathing ring, a 400ms fade and the button press, with reduced-motion support. |
| 9 | Time limits | No timeouts in setup or recording. No countdowns. |
| 10 | Language | No abbreviations. Test wording with a real family. |
| 11 | Error tolerance | Undo on every action, confirm before deleting, urgent pinned until read. |
| 12 | Physical analogies | The family sala: photos in picture frames on the wall, a wall clock, a breathing ring to show listening. |

These cover 60+ users in general. Lola's screen is stricter because she has dementia.

---

## Appendix A · tokens.css

```css
:root {
  --paper: #f4ede0;
  --ink: #2b2420;
  --green: #2f5e4e;
  --amber: #e9a83a;
  --red: #c23232;
  --white: #ffffff;
  --tap-min: 48px;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  --space-12: 48px;
  --r-frame: 6px;
  --r-photo: 2px;
  --r-card: 18px;
  --r-button: 14px;
  --r-round: 999px;
  --outline: 2px;
  --frame: 8px;
  --frame-l: 12px;
  --mat: 8px;
  --focus-width: 3px;
  --focus-offset: 2px;
  --shadow-flat: 0 4px 0 #2b2420;
  --shadow-flat-s: 0 2px 0 #2b2420;
  --scale-a: 1;
  --scale-a-plus: 1.25;
  --scale-a-plus-plus: 1.5;
  --font-heading: "Fredoka", "DM Sans", system-ui, sans-serif;
  --font-text: "DM Sans", system-ui, sans-serif;
  --fade: 400ms;
  --breathe: 4s;
}
@media (prefers-reduced-motion: reduce) {
  :root { --fade: 0ms; --breathe: 0s; }
}

.heading-xl { font-family: var(--font-heading); font-size: 56px; line-height: 1.05; font-weight: 600; }
.heading-l { font-family: var(--font-heading); font-size: 35px; line-height: 1.15; font-weight: 600; }
.heading-m { font-family: var(--font-heading); font-size: 22px; line-height: 1.25; font-weight: 600; }
.name-tag { font-family: var(--font-heading); font-size: 16px; line-height: 1.2; font-weight: 500; }
.name-m { font-family: var(--font-heading); font-size: 22px; line-height: 1.25; font-weight: 500; }
.name-l { font-family: var(--font-heading); font-size: 35px; line-height: 1.2; font-weight: 500; }
.heading-s { font-family: var(--font-heading); font-size: 16px; line-height: 1.25; font-weight: 600; }
.eyebrow { font-family: var(--font-heading); font-size: 14px; line-height: 1.3; font-weight: 500; }
.time-l { font-family: var(--font-heading); font-size: 56px; line-height: 1.05; font-weight: 600; }
.time-m { font-family: var(--font-heading); font-size: 22px; line-height: 1.1; font-weight: 600; }
.text-l { font-family: var(--font-text); font-size: 35px; line-height: 1.35; font-weight: 400; }
.text-m { font-family: var(--font-text); font-size: 22px; line-height: 1.45; font-weight: 400; }
.text-s { font-family: var(--font-text); font-size: 16px; line-height: 1.5; font-weight: 400; }
.label { font-family: var(--font-text); font-size: 16px; line-height: 1.25; font-weight: 700; }
.log-s { font-family: var(--font-text); font-size: 15px; line-height: 1.6; font-weight: 400; }
.text-l-big { font-family: var(--font-text); font-size: 44px; line-height: 1.3; font-weight: 400; }
.text-m-big { font-family: var(--font-text); font-size: 28px; line-height: 1.4; font-weight: 400; }

@font-face { font-family: "Fredoka"; src: url("fonts/Fredoka-Medium.woff2") format("woff2"); font-weight: 500; font-style: normal; font-display: swap; }
@font-face { font-family: "Fredoka"; src: url("fonts/Fredoka-SemiBold.woff2") format("woff2"); font-weight: 600; font-style: normal; font-display: swap; }
@font-face { font-family: "DM Sans"; src: url("fonts/DMSans-Regular.woff2") format("woff2"); font-weight: 400; font-style: normal; font-display: swap; }
@font-face { font-family: "DM Sans"; src: url("fonts/DMSans-Medium.woff2") format("woff2"); font-weight: 500; font-style: normal; font-display: swap; }
@font-face { font-family: "DM Sans"; src: url("fonts/DMSans-Bold.woff2") format("woff2"); font-weight: 700; font-style: normal; font-display: swap; }
```

## Appendix B · Component styles (bundle.css)

```css
/* Sino component styles: the sala. Flat 2D, ink outlines, the document's five colours plus white. Values come from tokens.css. */
body { margin: 0; background: var(--paper); color: var(--ink); font-family: var(--font-text); line-height: 1.5; -webkit-font-smoothing: antialiased; }
:focus-visible { outline: var(--focus-width) solid var(--ink); outline-offset: var(--focus-offset); }

/* The sala wall */
.sn-sala { background: var(--paper); padding: var(--space-6); box-sizing: border-box; min-height: 100%; }
.sn-rail { height: 0; border-top: var(--outline) solid var(--ink); margin: 0 calc(-1 * var(--space-6)) var(--space-6); }
.sn-greet { font: 600 35px/1.15 var(--font-heading); margin: 0 0 var(--space-2); }
.sn-sub { font-size: 16px; margin: 0 0 var(--space-8); }
.sn-title { font: 600 22px/1.25 var(--font-heading); margin: 0 0 var(--space-4); }

/* Picture frame: the signature object */
.sn-frame { display: inline-flex; flex-direction: column; align-items: center; gap: var(--space-2); }
.sn-frame__box { box-sizing: border-box; width: 120px; aspect-ratio: 4 / 5; background: var(--paper); border: var(--frame) solid var(--ink); border-radius: var(--r-frame); padding: var(--mat); box-shadow: var(--shadow-flat); }
.sn-frame__photo { width: 100%; height: 100%; border-radius: var(--r-photo); box-shadow: inset 0 0 0 var(--outline) var(--ink); display: flex; align-items: center; justify-content: center; overflow: hidden; }
.sn-frame__photo img { width: 100%; height: 100%; object-fit: cover; }
.sn-frame__initial { font: 600 35px/1 var(--font-heading); }
.sn-frame__plate { font: 500 16px/1.2 var(--font-heading); background: var(--paper); border: var(--outline) solid var(--ink); border-radius: var(--r-button); padding: 2px 10px; box-shadow: var(--shadow-flat-s); }
.sn-frame__meta { font-size: 14px; }
.sn-frame--tilt-l { transform: rotate(-2deg); }
.sn-frame--tilt-r { transform: rotate(2deg); }
.sn-frame--l .sn-frame__box { width: 220px; border-width: var(--frame-l); padding: var(--frame-l); box-shadow: none; }
.sn-frame--add .sn-frame__box { border-style: dashed; border-width: var(--outline); box-shadow: none; }

/* Memory wall */
.sn-wall { display: flex; flex-wrap: wrap; gap: var(--space-6) var(--space-4); align-items: flex-start; }

/* Button: chunky, outlined, sitting on a flat ink shadow */
.sn-btn { box-sizing: border-box; min-height: var(--tap-min); padding: 0 var(--space-6); border: var(--outline) solid var(--ink); border-radius: var(--r-button); background: var(--green); color: var(--white); font: 700 16px/1.25 var(--font-text); box-shadow: var(--shadow-flat); cursor: pointer; }
.sn-btn--quiet { background: var(--paper); color: var(--ink); }
.sn-btn:active, .sn-btn.is-pressed { box-shadow: none; transform: translateY(4px); }
.sn-icon-btn { box-sizing: border-box; width: var(--tap-min); height: var(--tap-min); border-radius: var(--r-round); border: var(--outline) solid var(--ink); background: var(--paper); display: inline-flex; align-items: center; justify-content: center; font: 700 18px/1 var(--font-text); box-shadow: var(--shadow-flat-s); }

/* Log cards */
.sn-log { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--space-4); }
.sn-entry { position: relative; padding: var(--space-4) var(--space-4) var(--space-4) calc(var(--space-4) + 10px); background: var(--paper); border: var(--outline) solid var(--ink); border-radius: var(--r-card); box-shadow: var(--shadow-flat); overflow: hidden; }
.sn-entry::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 10px; border-right: var(--outline) solid var(--ink); background: var(--paper); }
.sn-entry--ok::before { background: var(--green); }
.sn-entry--needs::before { background: var(--amber); }
.sn-entry__top { display: flex; justify-content: space-between; align-items: baseline; gap: var(--space-4); margin-bottom: var(--space-1); }
.sn-entry__time { font: 500 14px/1.3 var(--font-heading); }
.sn-entry__status { font: 600 22px/1.25 var(--font-heading); margin: 0; display: flex; align-items: center; gap: var(--space-2); }
.sn-entry__what { font-size: 16px; margin: 0 0 var(--space-3); }
.sn-mark--ok { color: var(--green); }
.sn-dot { display: inline-block; box-sizing: border-box; width: 16px; height: 16px; border-radius: var(--r-round); background: var(--amber); border: var(--outline) solid var(--ink); }
.sn-urgent { background: var(--red); color: var(--white); border: var(--outline) solid var(--ink); border-radius: var(--r-card); padding: var(--space-4); box-shadow: var(--shadow-flat); display: block; }
.sn-urgent p { margin: 0 0 var(--space-2); font-size: 22px; line-height: 1.4; }
.sn-urgent .sn-urgent__head { font: 600 22px/1.25 var(--font-heading); }
.sn-urgent .sn-btn { background: var(--paper); color: var(--ink); }

/* Lola's screen: one framed memory on the wall */
.sn-lola { min-height: 100%; box-sizing: border-box; padding: var(--space-12) var(--space-8); display: flex; flex-direction: column; justify-content: center; background: var(--paper); }
.sn-lola p { margin: 0; }
.sn-clock { box-sizing: border-box; width: 96px; height: 96px; border-radius: var(--r-round); border: var(--frame) solid var(--ink); background: var(--paper); position: relative; }
.sn-clock::before, .sn-clock::after { content: ""; position: absolute; left: 50%; bottom: 50%; width: 4px; margin-left: -2px; border-radius: 2px; background: var(--ink); transform-origin: 50% 100%; }
.sn-clock::before { height: 22px; transform: rotate(var(--h, 135deg)); }
.sn-clock::after { height: 30px; transform: rotate(var(--m, 180deg)); }
.sn-ring { box-sizing: border-box; width: 88px; height: 88px; border-radius: var(--r-round); border: var(--frame) solid var(--ink); animation: sn-breathe 4s ease-in-out infinite; }
@keyframes sn-breathe { 50% { transform: scale(1.05); } }
@media (prefers-reduced-motion: reduce) { .sn-ring { animation: none; } .sn-btn:active, .sn-btn.is-pressed { transform: none; } }

/* Record a reply */
.sn-record { background: var(--paper); border: var(--outline) solid var(--ink); border-radius: var(--r-card); box-shadow: var(--shadow-flat); padding: var(--space-6); display: grid; gap: var(--space-6); justify-items: center; }
.sn-wave { display: flex; align-items: center; gap: 3px; height: 48px; }
.sn-wave span { box-sizing: border-box; width: 6px; border-radius: 3px; background: var(--paper); border: 1.5px solid var(--ink); }
.sn-wave span.is-heard { background: var(--green); }
.sn-record__row { display: flex; align-items: center; gap: var(--space-6); }
.sn-mic { box-sizing: border-box; width: 88px; height: 88px; border-radius: var(--r-round); border: var(--outline) solid var(--ink); background: var(--green); color: var(--white); font: 700 16px/1 var(--font-text); box-shadow: var(--shadow-flat); }

/* Setup */
.sn-sheet { background: var(--paper); border: var(--outline) solid var(--ink); border-radius: var(--r-card); box-shadow: var(--shadow-flat); padding: var(--space-6); }
.sn-step__count { font: 500 14px/1.3 var(--font-heading); margin: 0 0 var(--space-3); }
.sn-progress { display: flex; gap: var(--space-1); margin-bottom: var(--space-6); }
.sn-progress span { box-sizing: border-box; flex: 1; height: 10px; border-radius: var(--r-round); border: var(--outline) solid var(--ink); background: var(--paper); }
.sn-progress span.is-done { background: var(--green); }
.sn-step__title { font: 600 35px/1.15 var(--font-heading); margin: 0 0 var(--space-3); }

/* Text scale */
.sn-scale { display: inline-flex; gap: var(--space-3); }
.sn-scale .sn-btn { min-width: 64px; background: var(--paper); color: var(--ink); font-family: var(--font-heading); font-weight: 600; }
.sn-scale .sn-btn.is-pressed { background: var(--ink); color: var(--paper); transform: none; box-shadow: none; }

/* Receipt strip: Sino's log, a torn paper receipt with a timeline. Hidden from families. */
.sn-receipt { box-sizing: border-box; position: relative; background: var(--paper); border-left: var(--outline) solid var(--ink); border-right: var(--outline) solid var(--ink); padding: var(--space-4) var(--space-6); max-width: 564px; margin: 0 auto; }
.sn-tear { display: block; width: 100%; height: 12px; max-width: 564px; margin: 0 auto; }
.sn-tear path { fill: var(--paper); stroke: var(--ink); stroke-width: var(--outline); stroke-linejoin: round; }
.sn-receipt__head { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--space-4); padding-bottom: var(--space-4); border-bottom: var(--outline) dashed var(--ink); }
.sn-receipt__title { font: 600 22px/1.25 var(--font-heading); margin: 0; }
.sn-receipt__date { font: 500 14px/1.3 var(--font-heading); margin: 0 0 var(--space-1); }
.sn-offline { display: inline-flex; align-items: center; gap: var(--space-2); font: 600 14px/1 var(--font-heading); background: var(--ink); color: var(--paper); border-radius: var(--r-button); padding: 6px 12px; }
.sn-offline::before { content: ""; width: 8px; height: 8px; border-radius: var(--r-round); background: var(--green); box-shadow: 0 0 0 1.5px var(--paper); }
.sn-tl { list-style: none; margin: 0; padding: var(--space-4) 0 0; }
.sn-tl__row { display: grid; grid-template-columns: 64px 28px 1fr; gap: 0 var(--space-3); padding-bottom: var(--space-6); position: relative; }
.sn-tl__row::before { content: ""; position: absolute; left: calc(64px + var(--space-3) + 13px); top: 28px; bottom: 0; border-left: var(--outline) solid var(--ink); }
.sn-tl__row:last-child::before { display: none; }
.sn-tl__time { font: 600 22px/1.1 var(--font-heading); font-variant-numeric: tabular-nums; }
.sn-tl__sec { display: block; font: 500 14px/1.3 var(--font-heading); }
.sn-tl__node { box-sizing: border-box; width: 28px; height: 28px; border-radius: var(--r-round); border: var(--outline) solid var(--ink); display: flex; align-items: center; justify-content: center; font: 700 13px/1 var(--font-text); background: var(--paper); position: relative; z-index: 1; }
.sn-tl__node--ok { background: var(--green); color: var(--white); }
.sn-tl__node--needs { background: var(--amber); color: var(--ink); }
.sn-tl__node--urgent { background: var(--red); color: var(--white); }
.sn-tl__kicker { font: 600 16px/1.25 var(--font-heading); margin: 2px 0 var(--space-1); }
.sn-tl__heard { font: 700 22px/1.3 var(--font-text); margin: 0 0 var(--space-3); }
.sn-tl__heard mark { background: transparent; color: inherit; box-shadow: inset 0 -8px 0 var(--amber); }
.sn-chips { display: flex; flex-wrap: wrap; gap: var(--space-2); align-items: center; }
.sn-chip { display: inline-flex; align-items: center; gap: var(--space-1); font: 600 14px/1 var(--font-heading); border: var(--outline) solid var(--ink); border-radius: var(--r-button); padding: 6px 10px; background: var(--paper); box-shadow: var(--shadow-flat-s); }
.sn-chip--ok { background: var(--green); color: var(--white); }
.sn-chip--needs { background: var(--amber); color: var(--ink); }
.sn-chip--urgent { background: var(--red); color: var(--white); }
.sn-meter { display: inline-flex; align-items: center; gap: var(--space-2); font: 600 14px/1 var(--font-heading); }
.sn-meter__bar { display: inline-flex; gap: 2px; }
.sn-meter__bar i { box-sizing: border-box; width: 8px; height: 14px; border: 1.5px solid var(--ink); border-radius: 2px; background: var(--paper); }
.sn-meter__bar i.on { background: var(--ink); }
.sn-receipt__total { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-3); padding-top: var(--space-4); border-top: var(--outline) dashed var(--ink); text-align: center; }
.sn-total__n { display: block; font: 600 35px/1 var(--font-heading); }
.sn-total__l { display: block; font: 500 14px/1.3 var(--font-heading); margin-top: var(--space-1); }
.sn-total--ok .sn-total__n { color: var(--green); }

/* What Sino knows */
.sn-knows { list-style: none; margin: 0; padding: 0 var(--space-4); background: var(--paper); border: var(--outline) solid var(--ink); border-radius: var(--r-card); box-shadow: var(--shadow-flat); }
.sn-knows li { display: flex; align-items: center; justify-content: space-between; gap: var(--space-4); padding: var(--space-3) 0; border-bottom: var(--outline) solid var(--ink); font-size: 16px; }
.sn-knows li:last-child { border-bottom: 0; }
.sn-check { width: 22px; height: 22px; accent-color: var(--green); }
```
