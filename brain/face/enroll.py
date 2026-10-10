"""Save enrollment JPEGs under one person's gallery folder."""

import os
import sys
from pathlib import Path

from . import (
    FACE_DIR,
    MAX_PHOTOS,
    PHOTO_SUFFIXES,
    _detected_rows,
    _largest,
    _load_cv,
    crop_face,
    load_gallery,
)

PEOPLE = ("troy", "joy", "donita")
MAX_FRAME = 2 * 1024 * 1024


def gallery_path():
    raw = os.environ.get("FACE_GALLERY", "").strip()
    if raw:
        return Path(raw)
    return FACE_DIR / "gallery"


def _folder(person):
    if person not in PEOPLE:
        raise ValueError("unknown person")
    root = gallery_path().resolve()
    folder = (root / person).resolve()
    if folder.parent != root:
        raise ValueError("unknown person")
    return folder


def _count(person):
    try:
        folder = _folder(person)
        if not folder.is_dir():
            return 0
        return sum(
            1
            for path in folder.iterdir()
            if path.is_file() and path.suffix.lower() in PHOTO_SUFFIXES
        )
    except (OSError, ValueError):
        return 0


def _missing(gallery):
    if gallery is None or gallery.__class__.__name__ == "NullGallery":
        return True
    try:
        result = gallery.identify(None)
    except Exception:
        return False
    return isinstance(result, dict) and result.get("reason") == "face disabled"


def _clear(person):
    folder = _folder(person)
    if not folder.is_dir():
        return False
    removed = False
    for path in list(folder.iterdir()):
        if path.name == "README.md" or not path.is_file():
            continue
        if path.suffix.lower() not in PHOTO_SUFFIXES:
            continue
        path.unlink()
        removed = True
    return removed


def _slot(folder):
    existing = []
    if folder.is_dir():
        existing = [
            path
            for path in folder.iterdir()
            if path.is_file() and path.suffix.lower() in PHOTO_SUFFIXES
        ]
    if len(existing) >= MAX_PHOTOS:
        return None
    used = {int(path.stem) for path in existing if path.stem.isdigit()}
    for number in range(1, MAX_PHOTOS + 1):
        if number in used:
            continue
        dest = folder / f"{number}.jpg"
        if not dest.exists():
            return dest
    return None


def _one(gallery, person, blob):
    fail = {"ok": False, "reason": "no_face"}
    if not isinstance(blob, (bytes, bytearray)) or len(blob) > MAX_FRAME:
        return fail, None
    try:
        cv = _load_cv()
        np = sys.modules[__package__].np
        if cv is None or np is None:
            return fail, None
        image = cv.imdecode(np.frombuffer(bytes(blob), dtype=np.uint8).copy(), cv.IMREAD_COLOR)
        if image is None:
            return fail, None
        row = _largest(_detected_rows(gallery._detector, image))
        if row is None:
            return fail, None
        recognizer = gallery._recognizer
        recognizer.feature(recognizer.alignCrop(image, row))
        crop = crop_face(image, row)
        if crop is None:
            return fail, None
        good, encoded = cv.imencode(".jpg", crop)
        if not good:
            return fail, None
        folder = _folder(person)
        dest = _slot(folder)
        if dest is None or gallery_path().resolve() not in dest.resolve().parents:
            return fail, None
        folder.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".tmp")
        tmp.write_bytes(encoded.tobytes())
        os.replace(tmp, dest)
        return {"ok": True}, bytes(blob)
    except Exception:
        return fail, None


def enroll_request(person, blobs, replace):
    if person not in PEOPLE:
        raise ValueError("unknown person")
    try:
        gallery = load_gallery(str(gallery_path()))
    except Exception:
        gallery = None
    if _missing(gallery):
        return {
            "person": person,
            "engine": "missing",
            "frames": [{"ok": False, "reason": "engine_missing"} for _blob in blobs],
            "count": _count(person),
        }, None, False
    changed = _clear(person) if replace else False
    frames = []
    first = None
    saved = False
    for blob in blobs:
        row, good = _one(gallery, person, blob)
        frames.append(row)
        if row.get("ok"):
            saved = True
            if first is None:
                first = good
    return {
        "person": person,
        "engine": "ok",
        "frames": frames,
        "count": _count(person),
    }, first, changed or saved


def gallery_body():
    try:
        gallery = load_gallery(str(gallery_path()))
    except Exception:
        gallery = None
    return {
        "engine": "missing" if _missing(gallery) else "ok",
        "people": {name: _count(name) for name in PEOPLE},
    }
