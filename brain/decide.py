import json
import re
import time
from pathlib import Path

from model import classify

SEED_PATH = Path(__file__).resolve().parent / "seed.json"

URGENT_TOKENS = ("masakit", "nahulog", "tulong")
BREATHING_TRIGGER = "hindi makahinga"
MEDICATION_TOKENS = ("gamot", "dosis", "reseta", "tableta")
ACTIONS = ("comfort", "caregiver", "urgent", "silent")

_PUNCTUATION = re.compile(r"[^\w\s]|_")


def normalize(text):
    return " ".join(_PUNCTUATION.sub(" ", str(text).lower()).split())


def _load_seed():
    try:
        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if isinstance(data, dict):
        data = data.get("questions", [])
    return [entry for entry in data if isinstance(entry, dict)] if isinstance(data, list) else []


def _match_known_question(normalized):
    for entry in _load_seed():
        candidates = [entry.get("question", "")] + list(entry.get("phrasings", []))
        for candidate in candidates:
            phrase = normalize(candidate)
            if phrase and phrase == normalized:
                return entry.get("id", "")
    return None


def _result(action, reason, trigger_words, confidence, started, reply_id=""):
    return {
        "action": action,
        "reply_id": reply_id,
        "reason": reason,
        "trigger_words": trigger_words,
        "confidence": confidence,
        "latency_ms": int((time.monotonic() - started) * 1000),
    }


def _from_model(output, started):
    if not isinstance(output, dict) or output.get("action") not in ACTIONS:
        return _result("caregiver", "model unavailable", [], 0.0, started)

    action = output["action"]
    if action == "comfort":
        action = "caregiver"

    reason = output.get("reason")
    if not isinstance(reason, str) or not reason:
        reason = "model"

    trigger_words = output.get("trigger_words")
    if not isinstance(trigger_words, list):
        trigger_words = []
    trigger_words = [word for word in trigger_words if isinstance(word, str)]

    confidence = output.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        confidence = 0.0

    return _result(action, reason, trigger_words, float(confidence), started)


def decide(text: str) -> dict:
    started = time.monotonic()
    normalized = normalize(text)
    tokens = normalized.split()

    urgent_hits = [token for token in tokens if token in URGENT_TOKENS]
    if BREATHING_TRIGGER in normalized or ("hindi" in tokens and "makahinga" in tokens):
        return _result("urgent", "urgent word", [BREATHING_TRIGGER], 1.0, started)
    if urgent_hits:
        return _result("urgent", "urgent word", urgent_hits, 1.0, started)

    medication_hits = [token for token in tokens if token in MEDICATION_TOKENS]
    if medication_hits:
        return _result("caregiver", "medication", medication_hits, 1.0, started)

    reply_id = _match_known_question(normalized)
    if reply_id is not None:
        return _result("comfort", "known question", [], 1.0, started, reply_id=reply_id)

    return _from_model(classify(text), started)
