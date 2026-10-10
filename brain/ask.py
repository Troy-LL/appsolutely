"""T7 Ask Sino about Lola: answer_about_lola(question, log) (docs/sino/mvp-plan.md).

The caregiver asks about Lola; the answer is built by code from the local
log: counts, her exact words, and the last urgent. Qwen only picks the
intent when the rules miss, and only when SINO_MODEL=ollama. Never a
diagnosis or a mood.

Sino replies like a friendly companion, in the asker's language (English,
Tagalog, or Taglish, picked by counting words, not by a model). Small talk
gets a short hello; medicine, health and off-topic questions are politely
declined. The wording is fixed text in TEXT below; the model never writes it.
"""

import json
import os
import re
import time
import urllib.request
from pathlib import Path

from clips.rooms import room_label
from decide import MEDICATION_TOKENS, normalize

SEED_PATH = Path(__file__).resolve().parent / "seed.json"
CASES_PATH = Path(__file__).resolve().parent / "tests" / "ask_cases.json"

INTENTS = ("how", "saying", "where")
MODEL_NAME = "qwen2.5:3b"
MODEL_TIMEOUT_S = 4

INTENT_PROMPT = """You pick the intent of a family member's question about Lola for Sino, an offline home hub for her family. You run locally (qwen2.5 via Ollama). You are not a cloud service.

The keyword rules already missed, so you only pick one intent. Reply with JSON only. No prose, no markdown, no code fences. Use exactly these keys:
{"intent": "..."}

intent is one of: how, saying, where, other.
- how: asks how Lola is doing.
- saying: asks what Lola has been saying or asking.
- where: asks where Lola is.
- other: anything else (medicine, health advice, weather, jokes, general questions).
You never answer, never diagnose, never name a mood. You only pick the intent.

Question:
"""

# Words that mark a question as Tagalog or as English. Names (Lola) and words
# both languages use (hi, hello, okay) are in neither list.
TAGALOG_WORDS = {
    "si", "ni", "kay", "ang", "ng", "mga", "ba", "na", "pa", "po", "opo", "ano",
    "anong", "kamusta", "kumusta", "musta", "nasaan", "nasan", "asan", "saan",
    "niya", "nya", "siya", "sya", "sinabi", "sinasabi", "sabi", "tanong",
    "tinanong", "tinatanong", "ka", "kayo", "ko", "ako", "mo", "salamat",
    "ngayon", "kanina", "lagay", "lang", "naman", "yung", "ito", "yan", "may",
    "wala", "gamot", "sakit", "paano", "bakit", "magandang", "ginagawa",
}
ENGLISH_WORDS = {
    "how", "hows", "is", "are", "was", "what", "whats", "where", "wheres", "who",
    "has", "have", "been", "does", "did", "do", "can", "should", "she", "her",
    "you", "your", "i", "me", "my", "the", "a", "about", "and", "or", "with",
    "today", "now", "doing", "saying", "said", "say", "asking", "asked",
    "questions", "thanks", "thank", "please", "tell", "s", "so", "good",
    "morning", "weather", "joke", "medicine", "meds", "sick", "doctor",
}

# Questions that refer to Lola. "Nasaan si Nanay?" is Lola's own line, not a question about her.
LOLA_WORDS = {"lola", "she", "her", "siya", "sya", "niya", "nya"}
SAYING_WORDS = {
    "tanong", "tinanong", "tinatanong", "sinabi", "sinasabi", "sabi",
    "saying", "said", "say", "asking", "asked", "questions", "words",
}
WHERE_WORDS = {"nasaan", "nasan", "asan", "saan", "where", "wheres"}
HOW_WORDS = {"kamusta", "kumusta", "musta", "how", "hows", "lagay", "okay", "ok"}

# Never answered: medicine, health advice, diagnosis. Point them to the doctor.
MEDICAL_WORDS = set(MEDICATION_TOKENS) | {
    "medicine", "medicines", "medication", "medications", "meds", "pill",
    "pills", "tablet", "tablets", "dose", "dosage", "prescription", "vitamins",
    "diagnosis", "diagnose", "dementia", "alzheimer", "alzheimers", "sakit",
    "sick", "illness", "disease", "symptoms", "sintomas", "doctor", "doktor",
    "hospital", "ospital", "treatment", "therapy",
}
# Not about Lola at all.
OFF_TOPIC_WORDS = {
    "weather", "panahon", "ulan", "rain", "raining", "bagyo", "typhoon", "joke",
    "jokes", "biro", "president", "presidente", "capital", "recipe", "song",
    "kanta", "math", "basketball", "movie", "pelikula",
}
THANKS_WORDS = {"salamat", "thanks", "thank", "ty"}
HELLO_WORDS = {
    "hi", "hello", "hey", "kumusta", "kamusta", "musta", "morning", "afternoon",
    "evening", "umaga", "hapon", "gabi",
}

# Fixed wording per language. Code fills the {blanks} from the log; the model
# never writes any of it. Answers about her state end with the "note".
TEXT = {
    "en": {
        "help": "You can ask me how Lola is doing, what she's been saying, or where she was last seen.",
        "hello": "Hi, I'm Sino!",
        "how_are_you": "I'm doing well, thanks for asking!",
        "thanks": "You're welcome!",
        "medical": "I can't help with medicine, health advice, or a diagnosis. Please ask Lola's doctor or her caregiver.",
        "off_topic": "Sorry, I can only answer questions about Lola.",
        "unknown": "Sorry, I can't answer that from what I've heard.",
        "nothing": "I haven't heard anything from Lola yet.",
        "how": "From what I've heard, Lola asked about {items}.",
        "urgent_one": "There was 1 urgent alert, at {at}.",
        "urgent_many": "There were {n} urgent alerts, the last at {at}.",
        "saying": "Here's what Lola has been saying: {items}",
        "note": "This isn't a diagnosis.",
        "food": "food",
        "once": "once",
        "times": "{n} times",
        "seen_recording": "The recording last showed Lola in the {room} (clip {clock}). I can't see where she is right now.",
        "seen_live": "Lola was last seen in the {room}, {n} min ago.",
        "no_camera": "I don't have a camera on Lola, so I won't guess where she is. Please check on her.",
    },
    "tl": {
        "help": "Pwede mo akong tanungin kung kumusta si Lola, ano ang mga sinasabi niya, o saan siya huling nakita.",
        "hello": "Kumusta! Ako si Sino.",
        "how_are_you": "Mabuti naman ako, salamat sa pagtanong!",
        "thanks": "Walang anuman!",
        "medical": "Hindi ko masasagot ang tungkol sa gamot, kalusugan, o diagnosis. Pakitanong sa doktor o sa nag-aalaga kay Lola.",
        "off_topic": "Pasensya na, mga tanong lang tungkol kay Lola ang kaya kong sagutin.",
        "unknown": "Pasensya na, hindi ko iyan masasagot mula sa mga narinig ko.",
        "nothing": "Wala pa akong narinig mula kay Lola.",
        "how": "Sa mga narinig ko, nagtanong si Lola tungkol sa {items}.",
        "urgent_one": "May 1 agarang alerto noong {at}.",
        "urgent_many": "May {n} agarang alerto, ang huli ay noong {at}.",
        "saying": "Ito ang mga sinabi ni Lola: {items}",
        "note": "Hindi ito diagnosis.",
        "food": "pagkain",
        "once": "isang beses",
        "times": "{n} beses",
        # The two "seen" lines are pinned by brain/tests/test_clips.py; keep them as they are.
        "seen_recording": "Huling nakita sa recording: {room} (clip {clock}).",
        "seen_live": "Nasa {room}, {n} minuto na.",
        "no_camera": "Wala akong camera, kaya hindi ko huhulaan kung nasaan si Lola. Pakitingnan na lang siya.",
    },
    "taglish": {
        "help": "You can ask me kung kumusta si Lola, ano yung mga sinasabi niya, o saan siya last nakita.",
        "hello": "Hi! Ako si Sino.",
        "how_are_you": "Okay naman ako, thanks for asking!",
        "thanks": "Walang anuman, happy to help!",
        "medical": "Sorry, hindi ako pwedeng sumagot about gamot, health, o diagnosis. Pakitanong sa doctor ni Lola o sa caregiver niya.",
        "off_topic": "Sorry, mga tanong lang about Lola ang kaya kong sagutin.",
        "unknown": "Sorry, hindi ko yan masagot based sa narinig ko.",
        "nothing": "Wala pa akong narinig from Lola.",
        "how": "Based sa narinig ko, nagtanong si Lola about {items}.",
        "urgent_one": "May 1 urgent alert noong {at}.",
        "urgent_many": "May {n} urgent alerts, yung huli noong {at}.",
        "saying": "So far, ito yung mga sinabi ni Lola: {items}",
        "note": "Hindi ito diagnosis, ha.",
        "food": "food",
        "once": "once",
        "times": "{n} times",
        "seen_recording": "Sa recording, huling nakita si Lola sa {room} (clip {clock}). Hindi ko alam kung nasaan siya right now.",
        "seen_live": "Last seen si Lola sa {room}, {n} min ago.",
        "no_camera": "Wala akong camera kay Lola, so hindi ko huhulaan kung nasaan siya. Pakicheck na lang siya.",
    },
}

# brain/clips compares the answer with this to send the caregiver's "not sure" card.
NO_CAMERA_ANSWER = TEXT["tl"]["no_camera"]

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
    meal_at = -1
    latest_ts = ""
    for index, entry in enumerate(entries):
        ts = entry.get("ts")
        if entry.get("event") == "meal_logged" and isinstance(ts, str) and ts >= latest_ts:
            latest_ts = ts
            meal_at = index
    groups = {}
    for index, entry in enumerate(entries):
        if entry.get("action") in ("urgent", "silent") or entry.get("event") == "meal_logged":
            continue
        reply_id = entry.get("reply_id", "")
        if reply_id == "meal-check" and meal_at >= 0 and index <= meal_at:
            continue
        transcript = entry.get("transcript", "")
        key = reply_id or transcript
        label = "food" if reply_id == "meal-check" else labels.get(reply_id, transcript)
        group = groups.setdefault(key, {"label": label, "count": 0})
        group["count"] += 1
    return groups


def _times(count, t):
    """ "once" / "4 times" (or "isang beses" / "4 beses") in the asker's language."""
    return t["once"] if count == 1 else t["times"].format(n=count)


def _how_answer(log, t):
    entries = _entries(log)
    items = []
    for key, group in _counts(entries).items():
        topic = t["food"] if key == "meal-check" else f"'{group['label']}'"
        items.append(f"{topic} {_times(group['count'], t)}")
    parts = [t["how"].format(items=", ".join(items))] if items else []
    urgent = [entry for entry in entries if entry.get("action") == "urgent"]
    if len(urgent) == 1:
        parts.append(t["urgent_one"].format(at=urgent[0].get("at", "")))
    elif urgent:
        parts.append(t["urgent_many"].format(n=len(urgent), at=urgent[-1].get("at", "")))
    if not parts:
        return t["nothing"]
    return " ".join(parts + [t["note"]])


def _saying_answer(log, t):
    counts = {}
    for entry in _entries(log):
        if entry.get("action") == "silent":
            continue
        transcript = entry.get("transcript", "")
        counts[transcript] = counts.get(transcript, 0) + 1
    if not counts:
        return t["nothing"]
    items = [
        f"'{transcript}'" + (f" {_times(count, t)}" if count > 1 else "")
        for transcript, count in counts.items()
    ]
    sentence = t["saying"].format(items=", ".join(items))
    # Her words often end in "?" or "." already; add a period only when they don't.
    if not sentence.endswith(("?'", ".'", "!'")):
        sentence += "."
    return sentence + " " + t["note"]


def _clip_clock(offset):
    if isinstance(offset, bool) or not isinstance(offset, (int, float)):
        offset = 0
    total = int(round(float(offset)))
    if total < 0:
        total = 0
    return f"{total // 60}:{total % 60:02d}"


def _where_answer(log, t):
    last_seen = log.get("last_seen") if isinstance(log, dict) else None
    if not isinstance(last_seen, dict) or not last_seen.get("room"):
        return t["no_camera"]
    room = room_label(last_seen.get("room"))
    if last_seen.get("source") == "recording":
        clock = _clip_clock(last_seen.get("clip_offset_s", 0))
        return t["seen_recording"].format(room=room, clock=clock)
    return t["seen_live"].format(room=room, n=last_seen.get("minutes_ago", 0))


def _language(tokens):
    """Return "en", "tl" or "taglish" by counting marker words in the question."""
    tagalog = sum(1 for token in tokens if token in TAGALOG_WORDS)
    english = sum(1 for token in tokens if token in ENGLISH_WORDS)
    if tagalog and english:
        return "taglish"
    if tagalog:
        return "tl"
    return "en"  # English words only, or no marker words at all ("Hi", "Lola?")


def _rule_kind(tokens):
    """Pick the kind of question from keywords, or None when no rule fits.

    Order matters: medicine is checked first so it is never answered, and
    questions that name Lola come before small talk ("Kumusta si Lola?" is
    how; "Kumusta ka?" is small talk).
    """
    words = set(tokens)
    if words & MEDICAL_WORDS:
        return "medical"
    if words & OFF_TOPIC_WORDS:
        return "off_topic"
    if words & LOLA_WORDS:
        if words & SAYING_WORDS:
            return "saying"
        if words & WHERE_WORDS:
            return "where"
        if words & HOW_WORDS:
            return "how"
    if words & THANKS_WORDS:
        return "thanks"
    if words & {"how", "kumusta", "kamusta", "musta"} and words & {"you", "ka", "kayo"}:
        return "how_are_you"
    if words & HELLO_WORDS:
        return "hello"
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
    if intent == "other":
        return "unknown"
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
    covers everything else (small talk, declines, not understood). The answer
    is built by code from the log, in the asker's language, never a diagnosis
    or a mood.
    """
    started = time.monotonic()
    tokens = normalize(question).split()
    t = TEXT[_language(tokens)]
    kind, source = _rule_kind(tokens), "rule"
    if kind is None:
        kind, source = _model_intent(question), "model"
    if kind is None:
        kind, source = "unknown", "fallback"
    builders = {"how": _how_answer, "saying": _saying_answer, "where": _where_answer}
    if kind in builders:
        answer = builders[kind](log, t)
    else:
        # Small talk, a decline, or not understood: one friendly line, then what Sino can help with.
        answer = t[kind] + " " + t["help"]
    return {
        # Small talk and declines go out as "unknown", so the wire contract stays the same.
        "intent": kind if kind in INTENTS else "unknown",
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