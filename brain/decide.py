import json
import os
import re
import threading
import time
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

from model import classify
from scope import current_root

try:
    from rapidfuzz.fuzz import ratio as _rapidfuzz_ratio
except ImportError:
    _rapidfuzz_ratio = None

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
REPEAT_HIGH = 0.90
REPEAT_BORDER = 0.80
REPEAT_OVERLAP = 0.50
UNKNOWN_SHARE = 0.40
WHISPER_LOGPROB = -1.0
WHISPER_NO_SPEECH = 0.6
_TIE_GAP = 0.06
_PHRASE_CAP = 24
_GLUE_TAILS = ("na", "ka", "ko", "mo", "ba", "po")
# Seed phrasings supply the content words. These are the small function-word list.
_FUNCTION_WORDS = {
    "a", "am", "an", "and", "ang", "ano", "are", "at", "ay", "ba", "dahil", "daw",
    "din", "do", "eh", "for", "have", "he", "her", "his", "ho", "how", "i", "in",
    "is", "it", "ito", "iyan", "ka", "kanina", "kapag", "kasi", "kay", "kayo", "ko",
    "kung", "lang", "may", "me", "mga", "mo", "my", "na", "naman", "nang", "ng",
    "nga", "ngayon", "ni", "niya", "noong", "nung", "nya", "of", "on", "opo", "or",
    "pa", "pag", "pala", "para", "pero", "po", "raw", "rin", "sa", "she", "si",
    "siya", "sya", "that", "the", "this", "to", "we", "what", "where", "who", "yan",
    "you", "yun", "yung",
}
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


_SAFETY_LOCK = threading.Lock()
_CUSTOM_MIN_LETTERS = 4
_CUSTOM_MAX_LEN = 40


class SafetyWordError(ValueError):
    """The caregiver's word was empty, too short, too long, or already listed."""


def safety_words_path():
    root = current_root()
    if root is not None:
        return root / "safety-words.json"
    override = os.environ.get("SINO_SAFETY_WORDS", "")
    if override:
        return Path(override)
    hub = os.environ.get("HUB_DATA", "")
    folder = Path(hub) if hub else Path(__file__).resolve().parent.parent / "hub" / "data"
    return folder / "safety-words.json"


def load_custom_safety_words():
    path = safety_words_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    raw = data.get("words") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return []
    words = []
    for item in raw:
        if not isinstance(item, str):
            continue
        word = normalize(item)
        if word and word not in words:
            words.append(word)
    return words


def _builtin_safety_words():
    return set(URGENT_STEMS) | set(FUZZY_SOLO) | {stem for _pattern, stem in _ENGLISH_URGENT}


def safety_words_payload():
    return {"builtin": list(URGENT_STEMS), "custom": load_custom_safety_words()}


def add_custom_safety_word(raw):
    word = normalize(raw)
    if not word:
        raise SafetyWordError("empty")
    letters = sum(1 for ch in word if ch.isalpha())
    if letters < _CUSTOM_MIN_LETTERS:
        raise SafetyWordError("short")
    if len(word) > _CUSTOM_MAX_LEN:
        raise SafetyWordError("long")
    with _SAFETY_LOCK:
        custom = load_custom_safety_words()
        if word in _builtin_safety_words() or word in custom:
            raise SafetyWordError("duplicate")
        custom.append(word)
        path = safety_words_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps({"words": custom}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    return word


def _match_key(text):
    lowered = _WHERES.sub("where is", str(text).lower())
    tokens = normalize(lowered).split()
    return " ".join(MATCH_ALIASES.get(t, t) for t in tokens if t not in MATCH_FILLER)


def load_seed(path=SEED_PATH):
    # The hub's working copy (SINO_SEED, set by brain/server.py) wins when that file exists.
    if path == SEED_PATH:
        root = current_root()
        if root is not None:
            session_copy = root / "questions.json"
            if session_copy.is_file():
                path = session_copy
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


_EXTRA_PHRASINGS = {}
_PHRASE_LOCK = threading.Lock()


def _candidates(entry):
    phrases = [entry.get("question", "")] + list(entry.get("phrasings") or [])
    phrases.extend(_EXTRA_PHRASINGS.get(entry.get("id"), []))
    return phrases


def _best_seed_match(key):
    if not key:
        return None, 0.0
    best_id, best_ratio = None, 0.0
    for entry in load_seed():
        for candidate in _candidates(entry):
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
        for candidate in _candidates(entry):
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


def _result(action, reason, trigger_words, confidence, started, reply_id="", source="rule", ignored="", alternate=""):
    result = {
        "action": action,
        "reply_id": reply_id,
        "reason": reason,
        "trigger_words": trigger_words,
        "confidence": confidence,
        "latency_ms": int((time.monotonic() - started) * 1000),
        "source": source,
        "ignored": ignored,
    }
    if alternate:
        result["alternate"] = alternate
    return result


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


def _custom_urgent_hits(normalized):
    words = load_custom_safety_words()
    if not words:
        return []
    hits = []
    solos = tuple(word for word in words if " " not in word)
    for word in words:
        if _spacing_insensitive(word, r"\b").search(normalized):
            if word not in hits:
                hits.append(word)
    if solos:
        for token in normalize(normalized).split():
            for piece in (token, *_unglued(token)):
                for stem in _solo_hits(piece, solos):
                    if stem not in hits:
                        hits.append(stem)
    return hits


def _tv_hits(normalized):
    tokens = normalized.split()
    tv_hits = [phrase for phrase in TV_PHRASES if phrase in normalized]
    for token in tokens:
        for tv in TV_TOKENS:
            if tv in tv_hits:
                continue
            if token == tv or (len(tv) >= 5 and tv in token):
                tv_hits.append(tv)
    return tv_hits


def urgent_words(text):
    """The urgent words decide() would alarm on. Rules only, never the model, so it is instant.
    brain/server.py uses it so the throttle never drops an emergency (QA D-01)."""
    without_loob = normalize(text)
    for _idiom, pattern in _LOOB_PATTERNS:
        without_loob = pattern.sub(" | ", without_loob)
    hits = _urgent_hits(without_loob)
    for word in _custom_urgent_hits(without_loob):
        if word not in hits:
            hits.append(word)
    return hits


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


def _solo_hits(piece, canons=None):
    solos = FUZZY_SOLO if canons is None else canons
    if canons is None and piece in URGENT_TYPOS:
        return [URGENT_TYPOS[piece]]
    if piece in solos:
        return [piece]
    if len(piece) < 4:
        return []
    ranked = []
    for canon in solos:
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


def _ratio(left, right):
    if left == right:
        return 1.0
    if not left or not right:
        return 0.0
    if _rapidfuzz_ratio is not None:
        return _rapidfuzz_ratio(left, right) / 100.0
    return SequenceMatcher(None, left, right).ratio()


def _yi_same(left, right):
    if len(left) != len(right):
        return False
    for a, b in zip(left, right):
        if a != b and {a, b} != {"y", "i"}:
            return False
    return True


def _split_heard(token):
    if token == "san":
        return ["saan"]
    if token in _seed_words() or token in _FUNCTION_WORDS or token in MATCH_FILLER:
        return [token]
    for word in sorted((w for w in _seed_words() if len(w) >= 2), key=len, reverse=True):
        for tail in _GLUE_TAILS:
            if _yi_same(token, word + tail):
                return [word, tail]
    return [token]


def _heard_key(text):
    parts = []
    for token in normalize(text).split():
        parts.extend(_split_heard(token))
    joined = []
    index = 0
    while index < len(parts):
        if index + 1 < len(parts) and parts[index] == "na" and parts[index + 1] == "saan":
            joined.append("nasaan")
            index += 2
            continue
        joined.append(parts[index])
        index += 1
    seen = []
    for token in joined:
        if token in MATCH_FILLER or token in seen:
            continue
        seen.append(token)
    return " ".join(seen)


def _pair_score(left, right):
    if not left or not right:
        return 0.0, 0.0
    seq = _ratio(left, right)
    sort = _ratio(" ".join(sorted(left.split())), " ".join(sorted(right.split())))
    lt, rt = set(left.split()), set(right.split())
    overlap = (len(lt & rt) / len(lt | rt)) if lt and rt else 0.0
    return max(seq, sort), overlap


def _repeat_scores(text):
    keys = []
    for key in (_heard_key(text), _match_key(text), _fuzzy_seed_key(text)):
        if key and key not in keys:
            keys.append(key)
    ranked = []
    for entry in load_seed():
        qid = entry.get("id", "")
        best = 0.0
        best_overlap = 0.0
        for candidate in _candidates(entry):
            phrase = _match_key(candidate) or _heard_key(candidate)
            if not phrase:
                continue
            for key in keys:
                score, overlap = _pair_score(key, phrase)
                if score > best:
                    best, best_overlap = score, overlap
        ranked.append((best, best_overlap, qid))
    ranked.sort(reverse=True)
    return ranked


def _qwen_id(text, left, right):
    if os.environ.get("SINO_MODEL", "stub") != "ollama":
        return None
    prompt = (
        "Pick which known question this transcript repeats. Reply with JSON only: "
        "{\"id\":\"...\"}. id is \"" + left + "\" or \"" + right + "\" or \"none\".\n"
        "Transcript:\n" + text + "\nJSON:"
    )
    hub = os.environ.get("HUB_URL", "http://localhost:11434").rstrip("/")
    payload = json.dumps({
        "model": "qwen2.5:3b",
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_predict": 16},
    }).encode("utf-8")
    request = urllib.request.Request(
        hub + "/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=1.5) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    raw = body.get("response") if isinstance(body, dict) else ""
    if not isinstance(raw, str):
        return None
    try:
        picked = json.loads(raw.strip()).get("id")
    except (ValueError, AttributeError):
        return None
    if picked in (left, right):
        return picked
    return None


def _repeat_match(text):
    ranked = _repeat_scores(text)
    if not ranked:
        return None
    score, overlap, qid = ranked[0]
    second_score, _second_overlap, second_id = ranked[1] if len(ranked) > 1 else (0.0, 0.0, "")
    if overlap < REPEAT_OVERLAP or score < REPEAT_BORDER:
        return None
    tied = bool(second_id) and second_score >= REPEAT_BORDER and score - second_score < _TIE_GAP
    if tied:
        picked = _qwen_id(text, qid, second_id)
        if picked and picked != qid:
            second_id, qid = qid, picked
    if score >= REPEAT_HIGH and not tied:
        return qid, score, "", False
    return qid, min(score, 0.89), second_id, True


def _known_words():
    return _seed_words() | _FUNCTION_WORDS | set(MATCH_ALIASES) | set(URGENT_STEMS) | set(FUZZY_SOLO)


def _unknown_share(tokens):
    if not tokens:
        return 1.0
    known = _known_words()
    unknown = [token for token in tokens if token not in known and MATCH_ALIASES.get(token, token) not in known]
    return len(unknown) / len(tokens), len(unknown)


def _whisper_low(audio):
    if not isinstance(audio, dict):
        return False
    logprob = audio.get("avg_logprob")
    if isinstance(logprob, (int, float)) and not isinstance(logprob, bool) and float(logprob) < WHISPER_LOGPROB:
        return True
    no_speech = audio.get("no_speech")
    if no_speech is None:
        no_speech = audio.get("no_speech_prob")
    if isinstance(no_speech, (int, float)) and not isinstance(no_speech, bool) and float(no_speech) > WHISPER_NO_SPEECH:
        return True
    return False


def _is_noise(text, audio):
    if _whisper_low(audio):
        return True
    tokens = normalize(text).split()
    if len(tokens) <= 2:
        return True
    share, count = _unknown_share(tokens)
    if count >= 2 and share >= UNKNOWN_SHARE:
        best = _repeat_scores(text)
        near = best[0][0] if best else 0.0
        if near < REPEAT_BORDER:
            return True
    return False


def _phrasing_saved(qid, heard):
    key = _match_key(heard)
    for entry in load_seed():
        if entry.get("id") != qid:
            continue
        for phrase in _candidates(entry):
            other = _match_key(phrase)
            if other and (other == key or _ratio(other, key) >= 0.92):
                return True
    return False


def remember_phrasing(qid, text):
    heard = " ".join(str(text).split())
    if not qid or not heard or _phrasing_saved(qid, heard):
        return
    if current_root() is not None:
        _persist_phrasing(qid, heard)
        return
    with _PHRASE_LOCK:
        if _phrasing_saved(qid, heard):
            return
        bucket = _EXTRA_PHRASINGS.setdefault(qid, [])
        if len(bucket) >= _PHRASE_CAP:
            return
        bucket.append(heard)
        _persist_phrasing(qid, heard)


def _persist_phrasing(qid, heard):
    root = current_root()
    if root is not None:
        path = root / "questions.json"
    else:
        raw = os.environ.get("SINO_SEED", "")
        if not raw:
            return
        path = Path(raw)
    try:
        if not path.is_file() or path.resolve() == SEED_PATH.resolve():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    entries = data.get("questions") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        return
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("id") != qid:
            continue
        phrasings = entry.get("phrasings")
        if not isinstance(phrasings, list):
            phrasings = []
            entry["phrasings"] = phrasings
        if heard in phrasings or len(phrasings) >= _PHRASE_CAP:
            return
        phrasings.append(heard)
        break
    else:
        return
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        return


def decide(text: str, audio=None) -> dict:
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

    # Custom words use the same fuzzy rules, but a TV line stays silent.
    tv_hits = _tv_hits(normalized)
    custom_hits = [word for word in _custom_urgent_hits(without_loob) if word not in urgent_hits]
    if custom_hits and not tv_hits:
        return _result("urgent", "urgent word", custom_hits, 1.0, started)

    if loob_hits:
        return _result("caregiver", "sakit ng loob idiom", loob_hits, 1.0, started)

    tokens = normalized.split()
    medication_hits = [token for token in tokens if token in MEDICATION_TOKENS]
    if medication_hits:
        return _result("caregiver", "medication", medication_hits, 1.0, started)

    if tv_hits:
        return _result("silent", "television line", tv_hits, 1.0, started, ignored="tv")

    reply_id, ratio = _match_known_question(text)
    if reply_id is not None:
        return _result("comfort", "known question", [], round(ratio, 3), started, reply_id=reply_id)

    repeat = _repeat_match(text)
    if repeat is not None:
        qid, score, alternate, low = repeat
        if low:
            return _result(
                "comfort", "repeat", [], round(min(score, 0.49), 3), started,
                reply_id=qid, alternate=alternate,
            )
        return _result("comfort", "known question", [], round(score, 3), started, reply_id=qid)

    if _is_noise(text, audio):
        return _result("silent", "unclear", [], 1.0, started)

    return _from_model(classify(text), started, text)
