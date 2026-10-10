"""Hub copy of the questions list (D5): add, re-record, or remove one question.

brain/seed.json is never changed. The hub works on hub/data/questions.json (copied from
the seed the first time) and keeps uploaded replies and photos in hub/data/media/,
served at /media/<file>. HUB_DATA overrides the data folder (tests use a temp folder).
Default recordings ship in brain/media/ and are copied into hub/data/media/ when missing;
empty reply_audio/photo fields in an existing working copy are filled from the seed.
A question whose id is in the seed stays. delete_question only removes one the family added.
"""

import copy
import json
import os
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "brain" / "seed.json"
SEED_MEDIA = ROOT / "brain" / "media"
MEDIA_FIELDS = ("reply_audio", "photo")
NESTED_GROUPS = ("replies", "by_person")
ID_PATTERN = re.compile(r"[a-z0-9-]{1,64}")
AUDIO_EXTS = (".webm", ".m4a", ".mp4", ".wav", ".mp3", ".ogg", ".aac")
PHOTO_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".heic")
MAX_BYTES = 10 * 1024 * 1024
MAX_TEXT = 300
MAX_PHRASINGS = 10
MAX_SPEAKER = 60
MAX_QUESTIONS = 50
BUILT_IN = "built-in questions stay"


class BadInput(ValueError):
    """Input we refuse. The server sends it back as HTTP 400 with this message."""


def data_dir():
    return Path(os.environ.get("HUB_DATA") or ROOT / "hub" / "data")


def questions_path():
    return data_dir() / "questions.json"


def media_dir():
    return data_dir() / "media"


def _write_atomic(path, data):
    # Write a temp file next to the target, then swap it in, so a reader never sees half a file.
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def install_seed_media():
    """Copy each default recording in brain/media/ into the media folder when it is missing."""
    media_dir().mkdir(parents=True, exist_ok=True)
    for src in sorted(SEED_MEDIA.glob("*")):
        dest = media_dir() / src.name
        if src.suffix.lower() in AUDIO_EXTS + PHOTO_EXTS and not dest.exists():
            _write_atomic(dest, src.read_bytes())


def _fill_empty(entry, seed_entry):
    # Only empty fields take the seed's value, so a caregiver's own recording always wins.
    changed = False
    for key in MEDIA_FIELDS:
        if not entry.get(key) and isinstance(seed_entry.get(key), str) and seed_entry[key]:
            entry[key] = seed_entry[key]
            changed = True
    for group in NESTED_GROUPS:
        seed_group = seed_entry.get(group)
        if not isinstance(seed_group, dict):
            continue
        if not isinstance(entry.get(group), dict):
            entry[group] = copy.deepcopy(seed_group)
            changed = True
            continue
        for name, seed_sub in seed_group.items():
            if not isinstance(seed_sub, dict):
                continue
            sub = entry[group].get(name)
            if not isinstance(sub, dict):
                entry[group][name] = dict(seed_sub)
                changed = True
            elif _fill_empty(sub, seed_sub):
                changed = True
    return changed


def _fill_from_seed(path):
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
        seed = json.loads(SEED.read_text(encoding="utf-8"))
    except ValueError:
        return
    if not isinstance(entries, list) or not isinstance(seed, list):
        return
    by_id = {e.get("id"): e for e in seed if isinstance(e, dict)}
    changed = False
    for entry in entries:
        if isinstance(entry, dict) and isinstance(by_id.get(entry.get("id")), dict):
            changed = _fill_empty(entry, by_id[entry["id"]]) or changed
    if changed:
        text = json.dumps(entries, ensure_ascii=False, indent=2) + "\n"
        _write_atomic(path, text.encode("utf-8"))


def ensure_working_copy():
    """Copy brain/seed.json the first time, fill empty media fields from it, install default media.

    Returns the list path.
    """
    install_seed_media()
    path = questions_path()
    if not path.is_file():
        _write_atomic(path, SEED.read_bytes())
    else:
        _fill_from_seed(path)
    return path


def read_questions():
    data = json.loads(ensure_working_copy().read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{questions_path()}: expected a list of questions")
    return [entry for entry in data if isinstance(entry, dict)]


def _text(value, name, limit, required):
    # Form values are untrusted: must be text, trimmed, and within the length limit.
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise BadInput(f"{name} must be text")
    value = value.strip()
    if required and not value:
        raise BadInput(f"{name} is required")
    if len(value) > limit:
        raise BadInput(f"{name} is longer than {limit} characters")
    return value


def _check_file(name, upload, exts):
    # upload is (filename, bytes) or None. Only the extension of the client's name is used.
    if upload is None:
        return None
    filename, data = upload
    ext = Path(filename).suffix.lower()
    if ext not in exts:
        raise BadInput(f"{name} must be one of {' '.join(exts)}")
    if not data:
        raise BadInput(f"{name} is empty")
    if len(data) > MAX_BYTES:
        raise BadInput(f"{name} is over 10 MB")
    return ext, data


def _new_id(question, taken):
    # "Nasaan yung aso?" -> "nasaan-yung-aso"; "-2", "-3", ... if that id is already used.
    ascii_text = unicodedata.normalize("NFKD", question).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")[:48].strip("-") or "question"
    new_id, n = base, 2
    while new_id in taken:
        new_id, n = f"{base}-{n}", n + 1
    return new_id


def _store_media(filename, data):
    # The hub picks the file name (id + reply/photo + allowed extension), never the client.
    _write_atomic(media_dir() / filename, data)
    return f"/media/{filename}"


def _is_seed(path):
    try:
        return path.resolve() == SEED.resolve()
    except OSError:
        return True


def set_by_person_photo_if_empty(person, jpeg_bytes) -> str | None:
    """Set sino-ka by_person[person].photo when it is empty. Never writes brain/seed.json."""
    if person not in ("troy", "joy", "donita"):
        return None
    if not isinstance(jpeg_bytes, (bytes, bytearray)) or not jpeg_bytes:
        return None
    path = questions_path()
    if _is_seed(path):
        return None
    try:
        if not path.is_file():
            ensure_working_copy()
            path = questions_path()
            if _is_seed(path):
                return None
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(entries, list):
        return None
    entry = next(
        (item for item in entries if isinstance(item, dict) and item.get("id") == "sino-ka"),
        None,
    )
    if entry is None:
        return None
    people = entry.get("by_person")
    if people is None:
        people = {}
        entry["by_person"] = people
    if not isinstance(people, dict):
        return None
    row = people.get(person)
    if row is None:
        row = {}
        people[person] = row
    if not isinstance(row, dict):
        return None
    current = row.get("photo", "")
    if current is None:
        current = ""
    if not isinstance(current, str) or current != "":
        return None
    try:
        if _is_seed(path):
            return None
        media_dir().mkdir(parents=True, exist_ok=True)
        media = _store_media(f"sino-ka-{person}-photo.jpg", bytes(jpeg_bytes))
        row["photo"] = media
        text = json.dumps(entries, ensure_ascii=False, indent=2) + "\n"
        if _is_seed(path):
            return None
        _write_atomic(path, text.encode("utf-8"))
    except OSError:
        return None
    return media


def save_question(fields, audio=None, photo=None):
    """Add a new question, or re-record an existing id. Returns the stored object.

    fields: id, question, speaker (strings) and phrasings (list) from the form.
    audio, photo: (filename, bytes) or None. Everything is checked before anything is written.
    """
    qid = fields.get("id") or ""
    if qid and not (isinstance(qid, str) and ID_PATTERN.fullmatch(qid)):
        raise BadInput("id must be 1-64 of a-z, 0-9, -")
    question = _text(fields.get("question"), "question", MAX_TEXT, False)
    phrasings = fields.get("phrasings") or []
    if not isinstance(phrasings, list) or len(phrasings) > MAX_PHRASINGS:
        raise BadInput(f"at most {MAX_PHRASINGS} phrasings")
    phrasings = [_text(p, "phrasing", MAX_TEXT, True) for p in phrasings]
    speaker = _text(fields.get("speaker"), "speaker", MAX_SPEAKER, False)
    audio = _check_file("reply_audio", audio, AUDIO_EXTS)
    photo = _check_file("photo", photo, PHOTO_EXTS)

    entries = read_questions()
    entry = next((e for e in entries if e.get("id") == qid), None) if qid else None
    if entry is None:
        if not question:
            raise BadInput("question is required for a new question")
        if audio is None:
            raise BadInput("reply_audio is required for a new question")
        if len(entries) >= MAX_QUESTIONS:
            raise BadInput(f"at most {MAX_QUESTIONS} questions")
        qid = qid or _new_id(question, {e.get("id") for e in entries})
        entry = {"id": qid, "question": question, "phrasings": phrasings,
                 "reply_audio": "", "photo": "", "speaker": speaker}
        entries.append(entry)
    elif speaker:
        # Existing id: keep the question and phrasings; the new recording may be someone else.
        entry["speaker"] = speaker
    if audio:
        entry["reply_audio"] = _store_media(f"{qid}-reply{audio[0]}", audio[1])
    if photo:
        entry["photo"] = _store_media(f"{qid}-photo{photo[0]}", photo[1])
    text = json.dumps(entries, ensure_ascii=False, indent=2) + "\n"
    _write_atomic(questions_path(), text.encode("utf-8"))
    return entry


def seed_ids():
    """Ids that shipped in brain/seed.json. Missing or unreadable seed refuses a delete."""
    try:
        data = json.loads(SEED.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BadInput("could not read the built-in questions") from exc
    if isinstance(data, dict):
        data = data.get("questions")
    if not isinstance(data, list):
        raise BadInput("could not read the built-in questions")
    return {entry.get("id") for entry in data if isinstance(entry, dict)}


def _owned_media(qid, value):
    # Only this question's own reply or photo, never a path that leaves media/.
    if not isinstance(value, str) or not value.startswith("/media/"):
        return ""
    name = Path(value).name
    if name.startswith(f"{qid}-reply") or name.startswith(f"{qid}-photo"):
        return name
    return ""


def delete_question(qid):
    """Remove one family-added question from the working copy. Returns the removed object.

    An id from brain/seed.json raises BadInput and writes nothing. An unknown id raises KeyError.
    """
    if not (isinstance(qid, str) and ID_PATTERN.fullmatch(qid)):
        raise BadInput("id must be 1-64 of a-z, 0-9, -")
    if qid in seed_ids():
        raise BadInput(BUILT_IN)
    entries = read_questions()
    removed = next((entry for entry in entries if entry.get("id") == qid), None)
    if removed is None:
        raise KeyError(qid)
    kept = [entry for entry in entries if entry.get("id") != qid]
    text = json.dumps(kept, ensure_ascii=False, indent=2) + "\n"
    _write_atomic(questions_path(), text.encode("utf-8"))
    for key in MEDIA_FIELDS:
        name = _owned_media(qid, removed.get(key))
        if not name:
            continue
        path = media_dir() / name
        if path.is_file():
            path.unlink()
    return removed
