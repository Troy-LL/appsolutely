"""T7 Ask Sino about Lola: answer_about_lola(question, log) (docs/sino/mvp-plan.md).

The caregiver asks about Lola. Rules pick the intent. Code answers from the
local log after dropping noise: how many questions today, the last urgent and
whether someone answered, the last logged meal, or the questions she repeated.
Qwen only picks a missed intent. When SINO_MODEL=ollama it may rephrase those
filtered facts, and a timeout or a garbage reply falls back to the rule text.
Stub mode is the rule text only. Never a diagnosis, a mood, or a claim that
she has not eaten.

Sino replies like a friendly companion, in the asker's language (English,
Tagalog, or Taglish, picked by counting words, not by a model). Small talk
gets a short hello; medicine, health and off-topic questions are politely
declined. Anything else points at the question chips.
"""

import json
import os
import re
import time
import urllib.request
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

from clips.rooms import room_label
from decide import MEDICATION_TOKENS, normalize, urgent_words

CASES_PATH = Path(__file__).resolve().parent / "tests" / "ask_cases.json"

INTENTS = ("how", "saying", "where", "ate")
MODEL_NAME = "qwen2.5:3b"
MODEL_TIMEOUT_S = 4
ANSWER_MAX_CHARS = 320
LOW_CONFIDENCE = 0.5
NEAR_DUP = 0.88

INTENT_PROMPT = """You pick the intent of a family member's question about Lola for Sino, an offline home hub for her family. You run locally (qwen2.5 via Ollama). You are not a cloud service.

The keyword rules already missed, so you only pick one intent. Reply with JSON only. No prose, no markdown, no code fences. Use exactly these keys:
{"intent": "..."}

intent is one of: how, saying, where, ate, other.
- how: asks how Lola is doing.
- saying: asks what Lola has been saying or asking.
- where: asks where Lola is.
- ate: asks whether Lola has eaten, or when her last meal was.
- other: anything else (medicine, health advice, weather, jokes, general questions).
You never answer, never diagnose, never name a mood. You only pick the intent.

Question:
"""

PHRASE_PROMPT = """You are Sino, a friendly companion on an offline home hub. You run locally (qwen2.5 via Ollama). You are not a cloud service.

Rewrite the facts as the reply. Use only these facts. Do not add events, names, rooms, moods, or a diagnosis. Do not say Lola has not eaten. Do not paste a log or start lines with "Asked about". 1 to 3 short sentences, same language as the question. A bullet list only if the facts already list her questions. Under 280 characters.

Question:
{question}

Facts:
{facts}

Reply:
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
MEAL_VERBS = {
    "kumain", "nakakain", "kumaen", "kumayn", "kain", "kinain", "kumakain", "kakain",
    "eaten", "eat", "ate", "eating",
}
MEAL_NOUNS = {
    "meal", "meals", "breakfast", "lunch", "dinner", "almusal", "tanghalian",
    "hapunan", "meryenda",
}
PROFANITY = {
    "shit", "fuck", "fucking", "fucked", "bitch", "bullshit", "asshole",
    "motherfucker", "puta", "putang", "putangina", "gago", "tangina", "tarantado",
}
_NOT_EATEN = (
    "hasn't eaten", "has not eaten", "hasnt eaten", "not yet",
    "hindi pa kumain", "hindi pa siya kumain", "hindi siya kumain",
    "she didn't eat", "she did not eat", "di pa kumain", "didn't eat",
)

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
        "help": "Try How is Lola?, What has she been asking?, or Where is Lola?.",
        "hello": "Hi, I'm Sino!",
        "how_are_you": "I'm doing well, thanks for asking!",
        "thanks": "You're welcome!",
        "medical": "I can't help with medicine, health advice, or a diagnosis. Please ask Lola's doctor or her caregiver.",
        "off_topic": "Sorry, I can only answer questions about Lola.",
        "unknown": "Sorry, I can't answer that from what I've heard.",
        "how_count": "Today Lola asked {n} questions.",
        "how_none": "Lola hasn't asked anything today.",
        "urgent_none": "There was no urgent alert",
        "urgent_one": "There was 1 urgent alert at {at}",
        "urgent_one_bare": "There was 1 urgent alert",
        "urgent_many": "There were {n} urgent alerts, the last at {at}",
        "urgent_many_bare": "There were {n} urgent alerts",
        "waiting": "nobody has answered it yet",
        "answered": "someone answered it",
        "meal_none": "no meal is logged",
        "meal_at": "a meal was logged at {clock}",
        "food_bit": "she asked about food {times}",
        "ate_none": "No meal is logged.",
        "ate_at": "A meal was logged at {clock}.",
        "saying_intro": "What Lola keeps asking:",
        "saying_none": "Lola hasn't repeated a question.",
        "note": "This isn't a diagnosis.",
        "and": "and",
        "once": "once",
        "times": "{n} times",
        "seen_recording": "The recording last showed Lola in the {room} (clip {clock}). I can't see where she is right now.",
        "seen_live": "Lola was last seen in the {room}, {n} min ago.",
        "no_camera": "I don't have a camera on Lola, so I won't guess where she is. Please check on her.",
    },
    "tl": {
        "help": "Subukan ang Kamusta si Lola?, Ano mga tanong niya?, o Nasaan si Lola?.",
        "hello": "Kumusta! Ako si Sino.",
        "how_are_you": "Mabuti naman ako, salamat sa pagtanong!",
        "thanks": "Walang anuman!",
        "medical": "Hindi ko masasagot ang tungkol sa gamot, kalusugan, o diagnosis. Pakitanong sa doktor o sa nag-aalaga kay Lola.",
        "off_topic": "Pasensya na, mga tanong lang tungkol kay Lola ang kaya kong sagutin.",
        "unknown": "Pasensya na, hindi ko iyan masasagot mula sa mga narinig ko.",
        "how_count": "Ngayong araw, {n} tanong si Lola.",
        "how_none": "Wala pang tanong si Lola ngayong araw.",
        "urgent_none": "Walang agarang alerto",
        "urgent_one": "May 1 agarang alerto noong {at}",
        "urgent_one_bare": "May 1 agarang alerto",
        "urgent_many": "May {n} agarang alerto, ang huli noong {at}",
        "urgent_many_bare": "May {n} agarang alerto",
        "waiting": "wala pang sumasagot",
        "answered": "may sumagot na",
        "meal_none": "walang naitalang kain",
        "meal_at": "huling naitala ang kain noong {clock}",
        "food_bit": "nagtanong siya tungkol sa pagkain {times}",
        "ate_none": "Walang naitalang kain.",
        "ate_at": "Huling naitala ang kain ni Lola noong {clock}.",
        "saying_intro": "Ito ang madalas na tanong ni Lola:",
        "saying_none": "Wala pang tanong na inulit ni Lola.",
        "note": "Hindi ito diagnosis.",
        "and": "at",
        "once": "isang beses",
        "times": "{n} beses",
        # The two "seen" lines are pinned by brain/tests/test_clips.py; keep them as they are.
        "seen_recording": "Huling nakita sa recording: {room} (clip {clock}).",
        "seen_live": "Nasa {room}, {n} minuto na.",
        "no_camera": "Wala akong camera, kaya hindi ko huhulaan kung nasaan si Lola. Pakitingnan na lang siya.",
    },
    "taglish": {
        "help": "Try Kamusta si Lola?, Ano mga tanong niya?, o Nasaan si Lola?.",
        "hello": "Hi! Ako si Sino.",
        "how_are_you": "Okay naman ako, thanks for asking!",
        "thanks": "Walang anuman, happy to help!",
        "medical": "Sorry, hindi ako pwedeng sumagot about gamot, health, o diagnosis. Pakitanong sa doctor ni Lola o sa caregiver niya.",
        "off_topic": "Sorry, mga tanong lang about Lola ang kaya kong sagutin.",
        "unknown": "Sorry, hindi ko yan masagot based sa narinig ko.",
        "how_count": "Today, {n} tanong si Lola.",
        "how_none": "Wala pang tanong si Lola today.",
        "urgent_none": "Walang urgent alert",
        "urgent_one": "May 1 urgent alert noong {at}",
        "urgent_one_bare": "May 1 urgent alert",
        "urgent_many": "May {n} urgent alerts, yung huli noong {at}",
        "urgent_many_bare": "May {n} urgent alerts",
        "waiting": "wala pang sumasagot",
        "answered": "may sumagot na",
        "meal_none": "walang naitalang kain",
        "meal_at": "huling naitala ang kain noong {clock}",
        "food_bit": "nagtanong siya about food {times}",
        "ate_none": "Walang naitalang kain.",
        "ate_at": "May naitalang kain noong {clock}.",
        "saying_intro": "Madalas niyang tanong:",
        "saying_none": "Wala pang inulit na tanong si Lola.",
        "note": "Hindi ito diagnosis, ha.",
        "and": "at",
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


def _times(count, t):
    """ "once" / "4 times" (or "isang beses" / "4 beses") in the asker's language."""
    return t["once"] if count == 1 else t["times"].format(n=count)


def _parse_when(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return parsed


def _is_today(entry):
    parsed = _parse_when(entry.get("ts"))
    if parsed is None:
        return True
    return parsed.astimezone().date() == datetime.now().astimezone().date()


def _clock(ts):
    if not isinstance(ts, str) or not ts.strip():
        return ""
    text = ts.strip()
    parsed = _parse_when(text)
    if parsed is None:
        return text
    return parsed.strftime("%I:%M %p").lstrip("0")


def _when(entry):
    at = entry.get("at")
    if isinstance(at, str) and at.strip():
        return at.strip()
    return _clock(entry.get("ts"))


def _typed_test(entry):
    for key in ("mode", "input", "via", "origin", "source"):
        if entry.get(key) == "typed":
            return True
    if entry.get("session") in ("test", "typed"):
        return True
    return entry.get("test") is True


def _low_confidence(entry):
    confidence = entry.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return False
    if confidence <= 0:
        return False
    return float(confidence) < LOW_CONFIDENCE


def _profanity(text):
    return bool(set(normalize(text).split()) & PROFANITY)


def _too_short(entry, text):
    words = normalize(text).split()
    if len(words) > 2 or entry.get("reply_id"):
        return False
    return not urgent_words(text)


def _english_chatter(entry, text):
    if entry.get("reply_id") or entry.get("action") == "urgent":
        return False
    if urgent_words(text) or "sino" in normalize(text).split():
        return False
    tokens = [token for token in normalize(text).split() if token.isalpha()]
    if len(tokens) < 3:
        return False
    tagalog = sum(1 for token in tokens if token in TAGALOG_WORDS)
    if tagalog >= 2:
        return False
    englishish = sum(
        1 for token in tokens if token in ENGLISH_WORDS or (token.isascii() and token not in TAGALOG_WORDS)
    )
    return englishish / len(tokens) >= 0.6


def _keep_utterance(entry):
    if entry.get("action") not in ("comfort", "caregiver", "urgent"):
        return False
    if entry.get("ignored") == "tv":
        return False
    reason = entry.get("reason")
    if isinstance(reason, str) and "television" in reason.lower():
        return False
    text = entry.get("transcript")
    if not isinstance(text, str) or not text.strip():
        return False
    if not _is_today(entry) or _typed_test(entry) or _low_confidence(entry):
        return False
    if _profanity(text) or _too_short(entry, text) or _english_chatter(entry, text):
        return False
    return True


def _kept(entries):
    return [entry for entry in entries if _keep_utterance(entry)]


def _latest_meal(entries):
    found = None
    for index, entry in enumerate(entries):
        if entry.get("event") != "meal_logged":
            continue
        parsed = _parse_when(entry.get("ts"))
        if parsed is None:
            continue
        if found is None or parsed >= found[0]:
            found = (parsed, entry.get("ts"), index)
    return found


def _food_since_meal(entries):
    found = _latest_meal(entries)
    meal_at = found[2] if found else -1
    count = 0
    for index, entry in enumerate(entries):
        if entry.get("reply_id") != "meal-check" or entry.get("action") != "comfort":
            continue
        if meal_at >= 0 and index <= meal_at:
            continue
        if _keep_utterance(entry):
            count += 1
    return count


def _someone_answered(entries, urgent):
    replies = [entry for entry in entries if entry.get("event") == "urgent_reply"]
    if not urgent or not replies:
        return False
    last_ts = urgent[-1].get("ts") if isinstance(urgent[-1].get("ts"), str) else ""
    for reply in replies:
        reply_ts = reply.get("ts") if isinstance(reply.get("ts"), str) else ""
        if not last_ts or not reply_ts or reply_ts >= last_ts:
            return True
    return False


def _how_answer(log, t):
    entries = _entries(log)
    kept = _kept(entries)
    questions = sum(1 for entry in kept if entry.get("action") in ("comfort", "caregiver"))
    urgent = [entry for entry in kept if entry.get("action") == "urgent"]
    first = t["how_count"].format(n=questions) if questions else t["how_none"]
    if not urgent:
        urgent_bit = t["urgent_none"]
    else:
        at = _when(urgent[-1])
        if len(urgent) == 1:
            urgent_bit = t["urgent_one"].format(at=at) if at else t["urgent_one_bare"]
        else:
            urgent_bit = t["urgent_many"].format(n=len(urgent), at=at) if at else t["urgent_many_bare"].format(n=len(urgent))
    if urgent:
        state = t["answered"] if _someone_answered(entries, urgent) else t["waiting"]
        urgent_bit = f"{urgent_bit} {t['and']} {state}"
    found = _latest_meal(entries)
    meal_bit = t["meal_at"].format(clock=_clock(found[1])) if found else t["meal_none"]
    food = _food_since_meal(entries)
    if food:
        meal_bit = f"{meal_bit}, {t['and']} {t['food_bit'].format(times=_times(food, t))}"
    return f"{first} {urgent_bit}, {t['and']} {meal_bit}. {t['note']}"


def _near(left, right):
    if left == right:
        return True
    if not left or not right:
        return False
    if min(len(left), len(right)) >= 12 and (left in right or right in left):
        return True
    return SequenceMatcher(None, left, right).ratio() >= NEAR_DUP


def _same_question(group, entry, norm):
    reply_id = entry.get("reply_id") or ""
    if reply_id and group["reply_id"] == reply_id:
        return True
    if reply_id and group["reply_id"]:
        return False
    return _near(norm, group["norm"])


def _repeated_questions(entries):
    groups = []
    for entry in _kept(entries):
        if entry.get("action") not in ("comfort", "caregiver"):
            continue
        transcript = entry.get("transcript", "")
        if not isinstance(transcript, str) or not transcript.strip():
            continue
        norm = normalize(transcript)
        group = next((item for item in groups if _same_question(item, entry, norm)), None)
        if group is None:
            groups.append({
                "reply_id": entry.get("reply_id") or "",
                "norm": norm,
                "count": 1,
                "forms": {transcript.strip(): 1},
            })
            continue
        group["count"] += 1
        label = transcript.strip()
        group["forms"][label] = group["forms"].get(label, 0) + 1
    repeated = [group for group in groups if group["count"] >= 2]
    repeated.sort(key=lambda group: -group["count"])
    return repeated[:5]


def _common_line(group):
    best, best_n = "", -1
    for text, count in group["forms"].items():
        if count > best_n:
            best, best_n = text, count
    return best


def _saying_answer(log, t):
    groups = _repeated_questions(_entries(log))
    if not groups:
        return f"{t['saying_none']} {t['note']}"
    lines = [t["saying_intro"]]
    for group in groups:
        lines.append(f"• {_common_line(group)} — {_times(group['count'], t)}")
    lines.append(t["note"])
    return "\n".join(lines)


def _ate_answer(log, t):
    found = _latest_meal(_entries(log))
    if found is None:
        return t["ate_none"]
    return t["ate_at"].format(clock=_clock(found[1]))


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
    if words & MEAL_VERBS or (words & MEAL_NOUNS and words & LOLA_WORDS):
        return "ate"
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


def _ollama(prompt, predict, json_mode=False):
    if os.environ.get("SINO_MODEL") != "ollama":
        return None
    hub = os.environ.get("HUB_URL", "http://localhost:11434").rstrip("/")
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0, "num_predict": predict},
    }
    if json_mode:
        payload["format"] = "json"
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
    raw = body.get("response") if isinstance(body, dict) else None
    return raw if isinstance(raw, str) else None


def _model_intent(question):
    return _parse_intent(_ollama(f"{INTENT_PROMPT}{question}\n\nJSON:", 40, json_mode=True))


def _junk_snippets(log):
    snippets = []
    for entry in _entries(log):
        if _keep_utterance(entry):
            continue
        text = entry.get("transcript")
        if not isinstance(text, str):
            continue
        cleaned = " ".join(text.lower().split())
        if len(cleaned) >= 8:
            snippets.append(cleaned[:48])
    return snippets


def _usable_phrase(text, junk):
    if not isinstance(text, str):
        return False
    cleaned = text.strip()
    if not cleaned or len(cleaned) > ANSWER_MAX_CHARS or cleaned.count("\n") > 8:
        return False
    lowered = cleaned.lower()
    if lowered.count("asked about") >= 2:
        return False
    if any(bad in lowered for bad in _NOT_EATEN):
        return False
    return not any(snippet and snippet in lowered for snippet in junk)


def _model_phrase(question, facts, junk):
    prompt = PHRASE_PROMPT.replace("{question}", question).replace("{facts}", facts)
    raw = _ollama(prompt, 80)
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    fenced = _FENCE.match(text)
    if fenced:
        text = fenced.group(1).strip()
    if not _usable_phrase(text, junk):
        return None
    return text


def _phrase_checks():
    junk = ["weird shit", "dakat pala"]
    dump = "Asked about Nasaan si Nanay? 2x. Asked about Weird shit. 1x."
    return (
        not _usable_phrase(dump, junk)
        and not _usable_phrase("She hasn't eaten.", [])
        and not _usable_phrase("x" * (ANSWER_MAX_CHARS + 1), [])
        and _usable_phrase("Ngayong araw, 3 tanong si Lola. Walang naitalang kain.", junk)
    )


def answer_about_lola(question: str, log) -> dict:
    """Return {"intent", "answer", "source", "latency_ms"} for a caregiver question about Lola.

    Intent is how, saying, where, or ate. "unknown" covers small talk, declines,
    and anything else. The answer is the rule text from the filtered log, in the
    asker's language. Ollama may rephrase how, saying, and ate; stub mode does not.
    """
    started = time.monotonic()
    tokens = normalize(question).split()
    t = TEXT[_language(tokens)]
    kind, source = _rule_kind(tokens), "rule"
    if kind is None:
        kind, source = _model_intent(question), "model"
    if kind is None:
        kind, source = "unknown", "fallback"
    builders = {
        "how": _how_answer,
        "saying": _saying_answer,
        "where": _where_answer,
        "ate": _ate_answer,
    }
    if kind in builders:
        answer = builders[kind](log, t)
        if kind in ("how", "saying", "ate"):
            phrased = _model_phrase(question, answer, _junk_snippets(log))
            if phrased:
                answer = phrased
    else:
        answer = t[kind] + " " + t["help"]
    return {
        "intent": kind if kind in INTENTS else "unknown",
        "answer": answer,
        "source": source,
        "latency_ms": int((time.monotonic() - started) * 1000),
    }


def run_cases(path=CASES_PATH):
    if not _phrase_checks():
        print("phrase guard: FAIL")
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    fixture = data.get("log", {})
    default_entries = fixture.get("entries", [])
    default_seen = fixture.get("last_seen")
    cases = data.get("cases", [])
    passed = 0
    for case in cases:
        entries = case["entries"] if isinstance(case.get("entries"), list) else default_entries
        if "last_seen" in case:
            seen = case.get("last_seen")
        elif case.get("camera"):
            seen = default_seen
        else:
            seen = None
        result = answer_about_lola(case["question"], {"entries": entries, "last_seen": seen})
        answer = result["answer"]
        ok = result["intent"] == case.get("expect_intent")
        if "expect_source" in case:
            ok = ok and result["source"] == case["expect_source"]
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