"""T7 Ask Sino about Lola: answer_about_lola(question, log) (docs/sino/mvp-plan.md).

The caregiver asks about Lola; the answer is built by code from the local
log: counts, her exact words, and the last urgent. Qwen only picks the
intent when the rules miss, and only when SINO_MODEL=ollama. Never a
diagnosis or a mood.
"""

import json
import os
import re
import time
import urllib.request
from pathlib import Path

from decide import MEDICATION_TOKENS, normalize

SEED_PATH = Path(__file__).resolve().parent / "seed.json"
CASES_PATH = Path(__file__).resolve().parent / "tests" / "ask_cases.json"

INTENTS = ("how", "saying", "where")
MODEL_NAME = "qwen2.5:3b"
MODEL_TIMEOUT_S = 4

INTENT_PROMPT = """You pick the intent of a family member's question about Lola for Sino, an offline home hub for her family. You run locally (qwen2.5 via Ollama). You are not a cloud service.

The keyword rules already missed, so you only pick one intent. Reply with JSON only. No prose, no markdown, no code fences. Use exactly these keys:
{"intent": "..."}

intent is one of: how, saying, where.
- how: asks how Lola is doing.
- saying: asks what Lola has been saying or asking.
- where: asks where Lola is.
You never answer, never diagnose, never name a mood. You only pick the intent.

Question:
"""

NO_ANSWER = "Wala akong sagot mula sa log. Itanong sa pamilya."
NO_CAMERA_ANSWER = "Walang camera sagot; hindi ko hulaan ang kwarto."

_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)


def _entries(log):
    if isinstance(log, dict) and isinstance(log.get("entries"), list):
        return [entry for entry in log["entries"] if isinstance(entry, dict)]
    return []


def _question_labels():
    try:
        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if isinstance(data, dict):
        data = data.get("questions", [])
    if not isinstance(data, list):
        return {}
    return {
        entry.get("id", ""): entry.get("question", "")
        for entry in data
        if isinstance(entry, dict)
    }


def _counts(entries):
    labels = _question_labels()
    groups = {}
    for entry in entries:
        if entry.get("action") in ("urgent", "silent"):
            continue
        reply_id = entry.get("reply_id", "")
        transcript = entry.get("transcript", "")
        key = reply_id or transcript
        group = groups.setdefault(key, {"label": labels.get(reply_id, transcript), "count": 0})
        group["count"] += 1
    return groups


def _how_answer(log):
    entries = _entries(log)
    parts = [
        f"Asked about {group['label']} {group['count']}x"
        for group in _counts(entries).values()
    ]
    urgent = [entry for entry in entries if entry.get("action") == "urgent"]
    if len(urgent) == 1:
        parts.append(f"1 urgent alert at {urgent[0].get('at', '')}")
    elif urgent:
        parts.append(f"{len(urgent)} urgent alerts, last at {urgent[-1].get('at', '')}")
    if not parts:
        return "Walang naitala sa log. Not a diagnosis."
    return ". ".join(parts) + ". Not a diagnosis."


def _saying_answer(log):
    counts = {}
    for entry in _entries(log):
        if entry.get("action") == "silent":
            continue
        transcript = entry.get("transcript", "")
        counts[transcript] = counts.get(transcript, 0) + 1
    if not counts:
        return "Walang naitala sa log. Not a diagnosis."
    parts = [
        f"'{transcript}'" + (f" {count}x" if count > 1 else "")
        for transcript, count in counts.items()
    ]
    return "Her words: " + "; ".join(parts) + ". Not a diagnosis."


def _where_answer(log):
    last_seen = log.get("last_seen") if isinstance(log, dict) else None
    if not isinstance(last_seen, dict) or not last_seen.get("room"):
        return NO_CAMERA_ANSWER
    return f"Nasa {last_seen.get('room')}, {last_seen.get('minutes_ago', 0)} minuto na."


def _rule_intent(normalized):
    tokens = normalized.split()
    if any(token in MEDICATION_TOKENS for token in tokens):
        return "unknown"
    if "kamusta" in tokens and "lola" in tokens:
        return "how"
    if "tanong" in tokens and "niya" in tokens:
        return "saying"
    if ("nasaan" in tokens or "asan" in tokens) and "lola" in tokens:
        return "where"
    return None


def _parse_intent(raw):
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip()
    fenced = _FENCE.match(cleaned)
    if fenced:
        cleaned = fenced.group(1)
    try:
        data = json.loads(cleaned)
    except ValueError:
        return None
    intent = data.get("intent") if isinstance(data, dict) else None
    return intent if intent in INTENTS else None


def _model_intent(question):
    if os.environ.get("SINO_MODEL") != "ollama":
        return None
    hub = os.environ.get("HUB_URL", "http://localhost:11434").rstrip("/")
    payload = {
        "model": MODEL_NAME,
        "prompt": f"{INTENT_PROMPT}{question}\n\nJSON:",
        "stream": False,
        "format": "json",
    }
    request = urllib.request.Request(
        f"{hub}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=MODEL_TIMEOUT_S) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    return _parse_intent(body.get("response", ""))


def answer_about_lola(question: str, log) -> dict:
    """Return {"intent", "answer", "source", "latency_ms"} for a caregiver question about Lola.

    Intent is how, saying, or where (docs/sino/mvp-plan.md, T7); "unknown"
    is the non-answer fallback. The answer is built by code from the log,
    never a diagnosis or a mood.
    """
    started = time.monotonic()
    intent = _rule_intent(normalize(question))
    source = "rule" if intent else "model"
    if intent is None:
        intent = _model_intent(question)
        source = "model" if intent else "fallback"
        if intent is None:
            intent = "unknown"
    builders = {"how": _how_answer, "saying": _saying_answer, "where": _where_answer}
    answer = builders[intent](log) if intent in builders else NO_ANSWER
    return {
        "intent": intent,
        "answer": answer,
        "source": source,
        "latency_ms": int((time.monotonic() - started) * 1000),
    }


def run_cases(path=CASES_PATH):
    data = json.loads(path.read_text(encoding="utf-8"))
    fixture = data.get("log", {})
    entries = fixture.get("entries", [])
    last_seen = fixture.get("last_seen")
    cases = data.get("cases", [])
    passed = 0
    for case in cases:
        log = {"entries": entries, "last_seen": last_seen if case.get("camera") else None}
        result = answer_about_lola(case["question"], log)
        answer = result["answer"]
        ok = result["intent"] == case.get("expect_intent")
        for needle in case.get("expect_contains", []):
            ok = ok and needle in answer
        for banned in case.get("expect_not_contains", []):
            ok = ok and banned not in answer
        passed += 1 if ok else 0
        status = "PASS" if ok else "FAIL"
        print(f"{case.get('id')}: {status} intent={result['intent']} answer={answer}")
    print(f"PASS {passed}/{len(cases)}")
    return passed == len(cases)


if __name__ == "__main__":
    raise SystemExit(0 if run_cases() else 1)