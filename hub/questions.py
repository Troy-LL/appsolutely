"""Hub copy of the questions list (D5): add or re-record one question and store its files.

brain/seed.json is never changed. The hub works on hub/data/questions.json (copied from
the seed the first time) and keeps uploaded replies and photos in hub/data/media/,
served at /media/<file>. HUB_DATA overrides the data folder (tests use a temp folder).
"""

import json
import os
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "brain" / "seed.json"
ID_PATTERN = re.compile(r"[a-z0-9-]{1,64}")
AUDIO_EXTS = (".webm", ".m4a", ".mp4", ".wav", ".mp3", ".ogg", ".aac")
PHOTO_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".heic")
MAX_BYTES = 10 * 1024 * 1024
MAX_TEXT = 300
MAX_PHRASINGS = 10
MAX_SPEAKER = 60
MAX_QUESTIONS = 50


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


def ensure_working_copy():
    """Create the data folders and copy brain/seed.json the first time. Returns the list path."""
    media_dir().mkdir(parents=True, exist_ok=True)
    path = questions_path()
    if not path.is_file():
        _write_atomic(path, SEED.read_bytes())
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
