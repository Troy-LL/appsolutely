# 04 Idea filter and locked spec

Fill this in live from 1:10 PM Fri. At 2:30 PM, sections 2 to 7 **are the spec**. Changing them after 4:00 PM needs the whole team.

## Challenge (paste verbatim at 1:00 PM)

> 

## 1. Filter

### Gates (fail any one, drop the idea)

1. A real Filipino user we can **actually reach today** to test
2. A painful moment that **happens often**
3. AI does something a form or a list **can't**
4. Fits the challenge statement **word for word**

### Scores (1 to 5 each, for ideas that pass all gates)

| Criterion | What a 5 looks like |
|---|---|
| Challenge fit | A judge sees the fit instantly, no stretching |
| Demo in under 3 min with one wow moment | One clear "oh!" a stranger notices |
| AI is load-bearing and explainable | Remove the AI and the product dies; Troy can explain every step |
| Buildable in ~14 hours by 4 people | Happy path fits in one slice by 7 PM |
| Simple and visual (our UI-first bet) | A stranger uses it right in 10 seconds on a phone |
| Life-improving | Clear before/after for the user, felt the same day |
| Free sponsor angle | Real Devin use, AMD hardware, or similar, without bending the idea |

| Idea | Gates pass? | Fit | Demo | AI | Build | Simple | Life | Sponsor | **Total** |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | |
| | | | | | | | | | |
| | | | | | | | | | |

**Kill rule:** if the only AI is "chat with it", or no tester can be reached for this user, go back to the filter.

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

- **Model** (primary / fallback):
- **Where it runs:**
- **Prompt sketch:**
- **Tool or retrieval step:**
- **Endpoint:** `POST /api/<action>`

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
