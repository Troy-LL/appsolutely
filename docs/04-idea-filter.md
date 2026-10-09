# 04 Idea filter and locked spec

> **Idea locked Fri Oct 9: Sino.** The locked spec now lives in [docs/sino/](sino/README.md) (features, AI contract and interfaces in `architecture.md`, failure cases in `judge-qa.md`, demo in `demo.md`). The empty spec template below is kept for reference only; don't fill it in.

Fill this in live from 1:10 PM Fri. At 2:30 PM, sections 2 to 7 **are the spec**. Changing them after 4:00 PM needs the whole team.

## Challenge (official)

> "Build an AI product that remains genuinely useful when the cloud disappears."

Meaningful AI computation must happen **on the user's device**. Full rules and criteria: [00-event.md](00-event.md#theme-local-ai-official).

## 1. Filter

### Gates (fail any one, drop the idea)

1. A real Filipino user we can **actually reach today** to test
2. A painful moment that **happens often**
3. AI does something a form or a list **can't**
4. Fits the challenge statement **word for word**
5. **Runs on the user's real device, network off.** The core AI runs on the user's actual device (their phone or their laptop) in airplane mode. A team laptop serving a phone does **not** count as the user's device unless that is the real-world setup
6. **One-sentence "why local?"** using one of the five official reasons: difficult, expensive, slow, private, or impossible with cloud-only
7. **Not an obvious or common idea.** It must have a twist other teams won't think of
8. **Survives a hard critique of its weakest point** (written down, answered before lock)

### Scores (official weights; score 1 to 5, multiply by weight, max 500)

| Criterion | Weight | What a 5 looks like |
|---|---|---|
| Problem & Usefulness | ×25 | A clear target user with a genuine, frequent problem; felt the same day (life-improving) |
| Local AI Implementation | ×25 | Local inference is fundamental: move it to the cloud and the product loses something real |
| Technical Execution | ×20 | The exact model runs on the demo device reliably enough for a live demo; buildable in ~14 h by 4 people |
| Innovation | ×15 | Meaningfully different from the obvious ideas; local AI enables something new |
| Product & Demo Quality | ×15 | A stranger uses it right in 10 seconds on a phone; one clear wow moment in airplane mode |

Tie-breakers (not scored): simple and visual (our UI-first bet), free sponsor angle (Devin, AMD hardware) without bending the idea.

| Idea | Gates 1-8 pass? | Why local (one sentence) | Useful ×25 | Local AI ×25 | Exec ×20 | Innov ×15 | Demo ×15 | **Total /500** |
|---|---|---|---|---|---|---|---|---|
| | | | | | | | | |
| | | | | | | | | |
| | | | | | | | | |

**Kill rule:** if the only AI is "chat with it", the core only works with a cloud AI API, or no tester can be reached for this user, go back to the filter.

**Pick:** highest total. Troy breaks ties.

## 2. The user and the moment

**The user** (one named person, age, where they are, what they have on them):

**The moment** (when it hurts, how often, what they do today):

**The sentence:**
> When [user] is [moment], they [pain]. With our app they [one action] and get [result] in [seconds].

## 3. The one screen

- **Input:**
- **One tap:**
- **AI result card** (what's on it):
- **Next step:**
- **Wow moment:**
- **States:** empty / loading / result / error (link frames):

## 4. AI contract

- **Model** (primary / fallback, exact name, size, quantization):
- **Runtime** (e.g. WebGPU in the browser, ONNX, llama.cpp, Ollama, MLX):
- **Where it runs** (which device; must be the user's own device):
- **What happens offline** (airplane mode: what still works, what waits):
- **What's cloud** (secondary only, optional; disclosed in README):
- **Why local** (one sentence: difficult / expensive / slow / private / impossible with cloud-only):
- **Prompt sketch:**
- **Tool or retrieval step:**
- **Interface:** local function or on-device endpoint (no cloud AI call on the core path)

Request:

```json
{
  "input": ""
}
```

Response:

```json
{
  "understood": "what the AI read from the input, shown to the user",
  "result": {},
  "confidence": 0.0,
  "next_step": "",
  "warnings": [],
  "error": null
}
```

## 5. Known failure cases

| # | Input that breaks it | What the user sees | Guardrail |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |

## 6. Demo script (click by click)

1. 
2. 
3. 

## 7. Cut list

| Cut | Why | Cut at |
|---|---|---|
| Login / accounts | Not in the demo | Default |
| Settings, admin, landing page, payments | Not in the demo | Default |
| Mascot (Ayen, optional stretch) | Only if the core works and it serves the UI, not decoration | Default; revisit after 7 PM |
| Second platform | Phone-first web only | Default |
| | | |
