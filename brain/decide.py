import json
import os
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
TV_TOKENS = (
    "abangan", "kabanata", "palabas", "teleserye", "dula", "bes",
    "balita", "commercial",
)
_SILENT_MIN_CONFIDENCE = 0.9
_BODY_WORDS = ("breathe", "breath", "chest", "fell", "pain", "hurts")
_ENGLISH_URGENT = (
    (re.compile(r"\b(?:cannot|cant|can t) breathe\b"), "cannot breathe"),
    (re.compile(r"\bhelp\b"), "help"),
    (re.compile(r"\bi fell\b"), "i fell"),
    (re.compile(r"\bfell down\b"), "fell down"),
    (re.compile(r"\bchest pain\b"), "chest pain"),
    (re.compile(r"\bmy chest hurts\b"), "my chest hurts"),
    # Whisper small writes "Tulong!" as "Too long" once VAD padding keeps the word (Donita's real
    # clip, docs/NOTES.md Sat ~6:55 AM). Safer to over-alert than miss a cry for help, so the
    # two-word phrase ("too long", "toolong", "too-long") is urgent; "too" or "long" alone is not.
    (re.compile(r"\btoo\s*long\b"), "too long"),
)
MATCH_FILLER = {"po", "opo", "lola", "ma", "na", "ba"}
MATCH_ALIASES = {"asan": "nasaan"}
MATCH_THRESHOLD = 0.85
URGENT_TYPOS = {"masaket": "masakit", "didip": "dibdib", "dibdip": "dibdib"}
FUZZY_SOLO = (
    "natumba", "nadulas", "nadapa", "nahulog", "bumagsak",
    "masakit", "sumasakit", "dibdib",
    "tulungan", "tulong", "saklolo",
)
GLUE_WORDS = ("ang", "ng", "ako", "ko", "si", "na", "sa", "po", "mo")
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
    # The hub's working copy (SINO_SEED, set by brain/server.py) wins when that file exists.
    override = os.environ.get("SINO_SEED", "")
    if path == SEED_PATH and override and Path(override).is_file():
        path = override
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


def _best_seed_match(key):
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


def _seed_words():
    words = set()
    for entry in load_seed():
        for candidate in [entry.get("question", "")] + list(entry.get("phrasings", [])):
            words.update(word for word in _match_key(candidate).split() if word)
    return words


def _closest_seed_word(combo, seed_words):
    best = None
    best_key = None
    for word in seed_words:
        if len(word) < 4:
            continue
        limit = 2 if len(word) >= 5 else 1
        if abs(len(combo) - len(word)) > limit:
            continue
        distance = _levenshtein(combo, word, limit)
        if distance <= limit:
            key = (distance, -len(word))
            if best_key is None or key < best_key:
                best, best_key = word, key
    return best


def _split_stuck_seed(token, seed_words):
    if token in seed_words or len(token) < 6:
        return None
    found = []
    for index in range(1, len(token)):
        left, right = token[:index], token[index:]
        left_anchor = left in seed_words and len(left) >= 4
        right_anchor = right in seed_words and len(right) >= 4
        left_word = _seed_part(left, seed_words, allow_near=right_anchor)
        right_word = _seed_part(right, seed_words, allow_near=left_anchor)
        if left_word and right_word:
            found.append((left_word, right_word))
    unique = list(dict.fromkeys(found))
    if len(unique) == 1:
        return list(unique[0])
    return None


def _seed_part(part, seed_words, allow_near):
    if part in seed_words:
        return part
    if not allow_near or len(part) < 2:
        return None
    best = None
    best_key = None
    for word in seed_words:
        if abs(len(part) - len(word)) > 1:
            continue
        if _levenshtein(part, word, 1) != 1:
            continue
        key = (abs(len(part) - len(word)), -len(word))
        if best_key is None or key < best_key:
            best, best_key = word, key
    return best


def _join_seed_fragments(tokens, seed_words):
    joined = []
    index = 0
    while index < len(tokens):
        if index + 1 < len(tokens) and tokens[index] not in seed_words and tokens[index + 1] not in seed_words:
            word = _closest_seed_word(tokens[index] + tokens[index + 1], seed_words)
            if word is not None:
                joined.append(word)
                index += 2
                continue
        joined.append(tokens[index])
        index += 1
    return joined


def _fuzzy_seed_key(text):
    lowered = _WHERES.sub("where is", str(text).lower())
    tokens = normalize(lowered).split()
    seed_words = _seed_words()
    parts = []
    for token in tokens:
        split = _split_stuck_seed(token, seed_words)
        parts.extend(split if split else [token])
    parts = _join_seed_fragments(parts, seed_words)
    return " ".join(MATCH_ALIASES.get(token, token) for token in parts if token not in MATCH_FILLER)


def _match_known_question(text):
    reply_id, ratio = _best_seed_match(_match_key(text))
    if reply_id is not None:
        return reply_id, ratio
    fuzzy_id, fuzzy_ratio = _best_seed_match(_fuzzy_seed_key(text))
    if fuzzy_id is not None:
        return fuzzy_id, fuzzy_ratio
    return None, ratio


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


def _has_body_word(text):
    tokens = normalize(text).split()
    if _mentions_urgent(tokens, FUZZY_SOLO + ("hirap", "huminga", "hinga", "makahinga")):
        return True
    return any(word in tokens for word in _BODY_WORDS)


# QA D-02/D-03: Qwen was sure ("silent", confidence >= 0.9) about misheard lines that were Lola,
# e.g. "A Thunkah Joy." (Asan ka, Joy?) and "Na hula ko" (Nahulog ako). These seed words are too
# common to mean "this is Lola"; every other word from her questions does, plus these extras.
_COMMON_SEED_WORDS = {"am", "are", "did", "go", "have", "is", "ka", "kayo", "ku", "main", "nang",
                      "si", "take", "to", "want", "you"}
_LOLA_EXTRA_WORDS = {"akin", "lola", "lolo"}
_NEAR_QUESTION = 0.75  # TV and chatter lines in the QA run scored 0.56 or less


def _sounds_like_lola(text):
    """True if the line may be Lola: ako/ko/I/me/my, a word from her questions, or close to one."""
    words = (_seed_words() - _COMMON_SEED_WORDS) | _LOLA_EXTRA_WORDS
    if any(token in words for token in normalize(text).split()):
        return True
    near = max(_best_seed_match(_match_key(text))[1], _best_seed_match(_fuzzy_seed_key(text))[1])
    return near >= _NEAR_QUESTION


def urgent_words(text):
    """The urgent words decide() would alarm on. Rules only, never the model, so it is instant.
    brain/server.py uses it so the throttle never drops an emergency (QA D-01)."""
    without_loob = normalize(text)
    for _idiom, pattern in _LOOB_PATTERNS:
        without_loob = pattern.sub(" | ", without_loob)
    return _urgent_hits(without_loob)


def _from_model(output, started, text=""):
    if not isinstance(output, dict) or output.get("action") not in ACTIONS:
        return _result("caregiver", "model unavailable", [], 0.0, started, source="model")

    action = output["action"]
    if action in ("comfort", "urgent"):
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
    confidence = float(confidence)

    # The model may keep Sino silent only when it is sure AND the line doesn't sound like Lola.
    if action == "silent" and (
        confidence < _SILENT_MIN_CONFIDENCE or _has_body_word(text) or _sounds_like_lola(text)
    ):
        action = "caregiver"

    return _result(action, reason, trigger_words, confidence, started, source="model")


def _levenshtein(left, right, limit):
    if left == right:
        return 0
    if abs(len(left) - len(right)) > limit:
        return limit + 1
    if len(left) > len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for char in left:
        current = [previous[0] + 1]
        smallest = current[0]
        for index, other in enumerate(right, 1):
            value = min(current[-1] + 1, previous[index] + 1, previous[index - 1] + (char != other))
            current.append(value)
            smallest = min(smallest, value)
        if smallest > limit:
            return limit + 1
        previous = current
    return previous[-1]


def _urgent_limit(left, right):
    short = min(len(left), len(right))
    if short < 4:
        return 0
    if short <= 6:
        return 1
    return 2


def _unglued(token):
    pieces = []
    for glue in GLUE_WORDS:
        if len(token) - len(glue) < 4:
            continue
        if token.endswith(glue):
            pieces.append(token[: -len(glue)])
        if token.startswith(glue):
            pieces.append(token[len(glue) :])
    return pieces


def _solo_hits(piece):
    if piece in URGENT_TYPOS:
        return [URGENT_TYPOS[piece]]
    if piece in FUZZY_SOLO:
        return [piece]
    if len(piece) < 4:
        return []
    ranked = []
    for canon in FUZZY_SOLO:
        if piece[0] != canon[0]:
            continue
        limit = _urgent_limit(piece, canon)
        if not limit:
            continue
        distance = _levenshtein(piece, canon, limit)
        if distance <= limit:
            ranked.append((distance, abs(len(piece) - len(canon)), canon))
    if not ranked:
        return []
    ranked.sort()
    best = ranked[0][:2]
    return [canon for distance, difference, canon in ranked if (distance, difference) == best]


def _near_canon(piece, canon):
    if piece == canon or URGENT_TYPOS.get(piece) == canon:
        return True
    if len(piece) < 4 or piece[0] != canon[0]:
        return False
    limit = _urgent_limit(piece, canon)
    return bool(limit) and _levenshtein(piece, canon, limit) <= limit


def _mentions_urgent(tokens, canons):
    for token in tokens:
        for piece in (token, *_unglued(token)):
            if any(_near_canon(piece, canon) for canon in canons):
                return True
    return False


def _fuzzy_urgent_hits(tokens):
    hits = []
    for token in tokens:
        stems = _solo_hits(token)
        if not stems:
            for piece in _unglued(token):
                for stem in _solo_hits(piece):
                    if stem not in stems:
                        stems.append(stem)
        for stem in stems:
            if stem not in hits:
                hits.append(stem)
    if _mentions_urgent(tokens, ("makahinga",)) and (
        _mentions_urgent(tokens, ("hindi",)) or "di" in tokens
    ):
        hits.append("hindi makahinga")
    if _mentions_urgent(tokens, ("hirap",)) and _mentions_urgent(tokens, ("huminga", "hinga")):
        hits.append("hirap huminga")
    if _mentions_urgent(tokens, ("huminga", "hinga")) and (
        _mentions_urgent(tokens, ("hindi",)) or "di" in tokens
    ):
        hits.append("di makahinga")
    return hits


def _urgent_hits(normalized):
    hits = [stem for stem, pattern in _URGENT_PATTERNS if pattern.search(normalized)]
    for pattern, stem in _ENGLISH_URGENT:
        if pattern.search(normalized):
            hits.append(stem)
    tokens = normalized.split()
    if "makahinga" in tokens and any(neg in tokens for neg in _BREATHING_NEGATIONS):
        hits.append("hindi makahinga")
    for stem in _fuzzy_urgent_hits(normalize(normalized).split()):
        if stem not in hits:
            hits.append(stem)
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
    for token in tokens:
        for tv in TV_TOKENS:
            if tv in tv_hits:
                continue
            if token == tv or (len(tv) >= 5 and tv in token):
                tv_hits.append(tv)
    if tv_hits:
        return _result("silent", "television line", tv_hits, 1.0, started, ignored="tv")

    reply_id, ratio = _match_known_question(text)
    if reply_id is not None:
        return _result("comfort", "known question", [], round(ratio, 3), started, reply_id=reply_id)

    return _from_model(classify(text), started, text)
