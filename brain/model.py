from __future__ import annotations

import json
import re

ACTIONS = ("comfort", "caregiver", "urgent", "silent")

PROMPT = """You are the fallback classifier for Sino, an offline home hub for an elderly person. You run locally (qwen2.5 via Ollama). You are not a cloud service.

You are only asked when the urgent-word check and the known-question matcher already missed. Decide what the hub should do with the transcript below.

Reply with JSON only. No prose, no markdown, no code fences. Use exactly these keys:
{"action": "...", "reason": "...", "trigger_words": [...], "confidence": 0.0}

action is one of: comfort, caregiver, urgent, silent.
reason is one short sentence.
trigger_words is the list of words from the transcript that drove your choice.
confidence is a number from 0.0 to 1.0.

Rules:
- Chatter or TV in the background: action silent.
- Anything new, unclear, or about medication: action caregiver.
- Do not return comfort. There is no recorded reply on file. Do not invent family facts.
- You may return urgent to escalate.
- Never choose silent for chest pain, falling, or being unable to breathe. Return urgent for those.

Transcript:
"""

_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)


def build_prompt(text: str) -> str:
    return f"{PROMPT}{text}\n\nJSON:"


def parse_model_json(raw: str) -> dict | None:
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip()
    fenced = _FENCE.match(cleaned)
    if fenced:
        cleaned = fenced.group(1)
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    action = data.get("action")
    if action not in ACTIONS:
        return None
    reason = data.get("reason")
    trigger_words = data.get("trigger_words")
    confidence = data.get("confidence")
    return {
        "action": action,
        "reason": reason if isinstance(reason, str) else "",
        "trigger_words": (
            list(trigger_words)
            if isinstance(trigger_words, list)
            and all(isinstance(word, str) for word in trigger_words)
            else []
        ),
        "confidence": (
            float(confidence)
            if isinstance(confidence, (int, float)) and not isinstance(confidence, bool)
            else 0.0
        ),
    }


def classify(text: str) -> dict | None:
    return None
