# 00 Event facts and rules

Source: https://appbuildersph.com/hackathon/ (and /participants). All times PH (UTC+8). Official theme, rules, and criteria below were revealed at the 1 PM Fri briefing.

## Basics

| Item | Fact |
|---|---|
| Event | AppBuildersPH Hackathon 2026, by App Builders PH |
| Format | 24-hour build. Remote on Fri Oct 9, in-person Demo Day Sat Oct 10 |
| Field | ~1,270 builders, 400+ teams. PUP is the top school (94 participants) |
| Theme | **Local AI** (see below). One challenge, no tracks |
| Judging criteria | Problem & Usefulness 25, Local AI Implementation 25, Technical Execution 20, Innovation 15, Product & Demo Quality 15 (see below) |
| Judges | 10, announced on Demo Day |
| Announcements | Official Telegram group and the App Builders PH Facebook page |

## Theme: Local AI (official)

"Useful AI experiences where meaningful AI computation happens on the user's device, rather than depending entirely on cloud inference."

This is **not** the same as building an AI product for a local (Filipino) audience. "Local" means the AI runs on the device.

### The challenge

> **"Build an AI product that remains genuinely useful when the cloud disappears."**

Create a working product that uses AI running locally on a user's device to solve a real problem. Show why running AI locally creates an experience that would be **difficult, expensive, slow, private, or impossible** with a cloud-only approach.

Any kind of product: productivity, developer tools, accessibility, education, finance, gaming, disaster, creative tools, enterprise tools, computer vision, personal assistants, privacy tools.

### In scope

Local LLMs, local vision models, local speech recognition, local embeddings and RAG, local AI agents, local image generation, edge AI, offline AI, privacy-preserving AI, hybrid local + cloud systems, AI on PCs, laptops, phones, and edge hardware. **Cloud services may be used, but meaningful AI functionality must run locally.**

### Tools you can use (examples, none required)

Ollama, LM Studio, llama.cpp, MLX, ONNX, PyTorch, TensorFlow, WebGPU, Core ML, AMD ROCm, DirectML, Hugging Face, plus open-source LLMs, vision, and speech models. No specific model, framework, OS, or hardware is required.

## Judging criteria (official)

| Criterion | Weight | What judges look for |
|---|---|---|
| Problem & Usefulness | **25%** | A genuine problem for a clear target user |
| Local AI Implementation | **25%** | Local inference is fundamental and gives a meaningful advantage |
| Technical Execution | **20%** | Works reliably enough for a live demo |
| Innovation | **15%** | Meaningfully different; does local AI enable something new? |
| Product & Demo Quality | **15%** | Usable UX; a convincing live demo |

Half the score is usefulness plus how real the local AI is.

## Schedule

| When | What |
|---|---|
| Fri 12:30 PM | Online room opens |
| Fri 12:45 PM | Participant briefing (rules and criteria now in this file) |
| Fri 1:00 PM | Challenge reveal, build starts (from anywhere) |
| Sat 10:00 AM | **Submissions close. No extensions.** |
| Sat 12:00 PM | Registration at Cyberzone, SM Makati |
| Sat 1:00 PM | Opening, finalists announced |
| Sat 5:45 PM | Awards |
| Sat 7:00 PM | Wrap |

## Rules that matter

### Official (from the briefing)

**Required:**
- Substantially built during the hackathon
- A meaningful part of AI inference executes locally
- A working product, demonstrated
- Models, APIs, frameworks, and major tools disclosed
- Core Local AI functionality works without depending entirely on a cloud AI API

**Allowed:** existing open-source models and libraries; AI-assisted development; Devin; cloud APIs as **secondary** components.

### Event rules (from the site)

- **Build from scratch** after 1:00 PM Fri. No project code before then. Planning docs are fine.
- **Only registered members build.** Nobody outside the official participant list may help with code, design, or ideas. Real-user testers may only *use* the app.
- **AI-assisted coding and Devin are allowed.** Disclose every tool used at submission.
- Mobile and hardware projects are allowed.
- **One submission per team**, on the Cerebral Valley event page (link TBD at briefing), by 10:00 AM Sat.
- **Repo must be public by 10:00 AM.** Judges review the code as it was at the deadline.
- Live deploy not required, but the README must let judges recreate the app.
- Each member's role and contributions are entered at submission.
- **Disqualifiers:** pre-existing project, external help, faking benchmarks.

## Knock-out list (any one ends the run)

- [ ] Missed the 10:00 AM submit
- [ ] Repo still private at 10:00 AM
- [ ] No ~1-minute demo video
- [ ] No X or LinkedIn post with the video, tagging Devin / Cognition, with #AppBuildersPH
- [ ] Project code written before 1:00 PM Fri
- [ ] Help from anyone not on the participant list
- [ ] Invented or rounded-up numbers
- [ ] Core AI only works through a cloud AI API (fails the Local AI rule)
- [ ] Nobody on-site by 12:00 PM Sat (not a DQ, but no finals)

Full checklist: [05-submission.md](05-submission.md).

## Judging signals (from the FAQ)

- Working product over slides.
- 5-minute pitch + live demo, then 3-minute judge Q&A (8 min per team). Finalists announced Sat Oct 10 at 1:00 PM. Prioritize a working product over many slides.
- Q&A covers: how it works, decisions made, architecture, **the AI implementation, its limitations, and what each person built**.
- Judges may read the code.

## Prizes (PHP 135,000 cash total)

| Award | Cash | Extras |
|---|---|---|
| Grand Champion | 50,000 | AMD/ASUS peripherals, Devin credits |
| WhiteCloak Award | 15,000 | WhiteCloak merch |
| Cognition / Devin Award | 10,000 | Devin credits |
| People's Choice (audience QR vote) | 10,000 | Devin credits |
| AMD Award | 10,000 | AMD/ASUS peripherals, Devin credits |
| Tutorials Dojo Award | 10,000 each, 4 winners | |

### Prize targets

- **Primary: Grand Champion (PHP 50,000).** The whole plan aims here.
- **Fallback: Tutorials Dojo Award (PHP 10,000 x 4).** Teams have won it without reaching finals, so a strong submission still has a shot.
- **Side awards are a bonus.** Side-award criteria are still TBD; copy them into [NOTES.md](NOTES.md) when announced. We tick their boxes only where it doesn't change the core app.

| Award | Criteria |
|---|---|
| Tutorials Dojo | TBD |
| WhiteCloak | TBD |
| Cognition / Devin | TBD |
| AMD | TBD |
| People's Choice | Audience QR vote on Demo Day; other details TBD |

## Demo Day logistics (Sat Oct 10)

- **Venue:** Cyberzone, SM Makati. Register by **12:00 PM**. Finalists (10 to 15 teams) come only from teams with at least one member on-site by noon.
- **On-site:** Troy, Viviene, and Ayen are going, even before finalists are announced. Donita TBD. Rule: at least one of us registered by **12:00 PM**, or we can't make finals.
- **Pitch:** 5 min live, then 3 min Q&A. No remote pitching. Max 4 to 5 slides.
- **Venue kit:** Wi-Fi, power, HDMI and USB-C. Bring your own laptop and charger. Coffee and sandwiches provided.
- **Bring:** demo laptop with inputs pre-loaded, phone for the mobile demo, offline fallback (recorded full demo), HDMI/USB-C adapter.
- **People's Choice:** attendees scan a QR during pitches. End the pitch with a "scan to vote" ask.
- **Payout:** bank transfer to one team representative. The team keeps its IP.

## Open questions (ask in Telegram)

- Sponsor award criteria, and whether a team can win more than one award
- Cerebral Valley submission link
- Whether Devin credits come with Build Day
