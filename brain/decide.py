import json
import re
import time
from difflib import SequenceMatcher
from pathlib import Path

from model import classify

SEED_PATH = Path(__file__).resolve().parent / "seed.json"

URGENT_STEMS = (
    "natumba", "nadulas", "nadapa", "nahulog", "bumagsak",
    "masakit", "sumasakit", "ang sakit ng dibdib", "masakit dibdib",
    "di makahinga", "hindi makahinga", "hirap huminga", "nahihirapan huminga",
    "tulungan", "tulong", "saklolo",
)
LOOB_IDIOMS = ("masakit ang loob", "sakit ng loob")
MEDICATION_TOKENS = ("gamot", "dosis", "reseta", "tableta")
TV_PHRASES = ("thank you for watching", "salamat sa panonood")
TV_TOKENS = ("abangan", "kabanata", "palabas", "teleserye", "dula", "bes")
MATCH_FILLER = {"po", "opo", "lola", "ma", "na", "ba"}
MATCH_ALIASES = {"asan": "nasaan"}
MATCH_THRESHOLD = 0.85
ACTIONS = ("comfort", "caregiver", "urgent", "silent")

_PUNCTUATION = re.compile(r"[^\w\s]|_")
_WHERES = re.compile(r"\bwhere['’]s\b")


def _spacing_insensitive(phrase, suffix=""):
    letters = phrase.replace(" ", "")
    return re.compile(r"\b" + r"\s*".join(re.escape(ch) for ch in letters) + suffix)


_URGENT_PATTERNS = [(stem, _spacing_insensitive(stem)) for stem in URGENT_STEMS]
_LOOB_PATTERNS = [(idiom, _spacing_insensitive(idiom, r"(?!\s*ng\b)")) for idiom in LOOB_IDIOMS]
_BREATHING_NEGATIONS = ("hindi", "di")


def normalize(text):
    return " ".join(_PUNCTUATION.sub(" ", str(text).lower()).split())


def _match_key(text):
    lowered = _WHERES.sub("where is", str(text).lower())
    tokens = normalize(lowered).split()
    return " ".join(MATCH_ALIASES.get(t, t) for t in tokens if t not in MATCH_FILLER)


def load_seed(path=SEED_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("questions")
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a list of questions")
    entries = [entry for entry in data if isinstance(entry, dict)]
    if not entries:
        raise ValueError(f"{path}: no questions")
    return entries


load_seed()


def _match_known_question(text):
    key = _match_key(text)
    if not key:
        return None, 0.0
    best_id, best_ratio = None, 0.0
    for entry in load_seed():
        for candidate in [entry.get("question", "")] + list(entry.get("phrasings", [])):
            phrase = _match_key(candidate)
            if not phrase:
                continue
            ratio = 1.0 if phrase == key else SequenceMatcher(None, phrase, key).ratio()
            if ratio > best_ratio:
                best_id, best_ratio = entry.get("id", ""), ratio
    if best_ratio >= MATCH_THRESHOLD:
        return best_id, best_ratio
    return None, best_ratio


def _result(action, reason, trigger_words, confidence, started, reply_id="", source="rule", ignored=""):
    return {
        "action": action,
        "reply_id": reply_id,
        "reason": reason,
        "trigger_words": trigger_words,
        "confidence": confidence,
        "latency_ms": int((time.monotonic() - started) * 1000),
        "source": source,
        "ignored": ignored,
    }


def _from_model(output, started):
    if not isinstance(output, dict) or output.get("action") not in ACTIONS:
        return _result("caregiver", "model unavailable", [], 0.0, started, source="model")

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

    return _result(action, reason, trigger_words, float(confidence), started, source="model")


def _urgent_hits(normalized):
    hits = [stem for stem, pattern in _URGENT_PATTERNS if pattern.search(normalized)]
    tokens = normalized.split()
    if "makahinga" in tokens and any(neg in tokens for neg in _BREATHING_NEGATIONS):
        hits.append("hindi makahinga")
    return hits


def decide(text: str) -> dict:
    started = time.monotonic()
    normalized = normalize(text)

    without_loob = normalized
    loob_hits = []
    for idiom, pattern in _LOOB_PATTERNS:
        without_loob, count = pattern.subn(" | ", without_loob)
        if count:
            loob_hits.append(idiom)

    urgent_hits = _urgent_hits(without_loob)
    if urgent_hits:
        return _result("urgent", "urgent word", urgent_hits, 1.0, started)

    if loob_hits:
        return _result("caregiver", "sakit ng loob idiom", loob_hits, 1.0, started)

    tokens = normalized.split()
    medication_hits = [token for token in tokens if token in MEDICATION_TOKENS]
    if medication_hits:
        return _result("caregiver", "medication", medication_hits, 1.0, started)

    tv_hits = [phrase for phrase in TV_PHRASES if phrase in normalized]
    tv_hits += [token for token in tokens if token in TV_TOKENS]
    if tv_hits:
        return _result("silent", "television line", tv_hits, 1.0, started, ignored="tv")

    reply_id, ratio = _match_known_question(text)
    if reply_id is not None:
        return _result("comfort", "known question", [], round(ratio, 3), started, reply_id=reply_id)

    return _from_model(classify(text), started)
