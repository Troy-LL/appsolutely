"""Family members the caregiver hangs on the wall.

Stored in hub/data/family.json. A photo is a file in hub/data/media/, served at /media/<file>.
brain/seed.json is never written. HUB_DATA overrides the data folder, same as questions.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from questions import PHOTO_EXTS, BadInput, _check_file, _store_media, _write_atomic, data_dir, media_dir

COLORS = ("green", "amber", "red")
MAX_NAME = 60
MAX_MEMBERS = 24
ID_PATTERN = re.compile(r"[a-z0-9-]{1,64}")


def family_path():
    return data_dir() / "family.json"


def read_family():
    path = family_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = data.get("members") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return []
    members = []
    for row in rows:
        member = _member(row)
        if member:
            members.append(member)
    return members


def _member(row):
    if not isinstance(row, dict):
        return None
    name = row.get("name")
    mid = row.get("id")
    if not isinstance(name, str) or not name.strip():
        return None
    if not isinstance(mid, str) or not ID_PATTERN.fullmatch(mid):
        return None
    color = row.get("color")
    photo = row.get("photo")
    return {
        "id": mid,
        "name": name.strip(),
        "color": color if color in COLORS else "green",
        "photo": photo if isinstance(photo, str) else "",
    }


def _save(members):
    path = family_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps({"members": members}, ensure_ascii=False, indent=2) + "\n"
    _write_atomic(path, text.encode("utf-8"))


def _slug(name, taken):
    ascii_text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")[:48].strip("-") or "family"
    new_id, n = base, 2
    while new_id in taken:
        new_id, n = f"{base}-{n}", n + 1
    return new_id


def add_member(name, color, photo=None):
    """Add a member, or update the colour and photo when the name is already on the wall."""
    if not isinstance(name, str):
        raise BadInput("name must be text")
    name = name.strip()
    if not name:
        raise BadInput("name is required")
    if len(name) > MAX_NAME:
        raise BadInput(f"name is longer than {MAX_NAME} characters")
    if color is None or color == "":
        color = "green"
    if not isinstance(color, str) or color not in COLORS:
        raise BadInput("color must be green, amber, or red")
    checked = _check_file("photo", photo, PHOTO_EXTS)
    members = read_family()
    existing = next((m for m in members if m["name"].casefold() == name.casefold()), None)
    if existing is None and len(members) >= MAX_MEMBERS:
        raise BadInput(f"at most {MAX_MEMBERS} family members")
    if existing is None:
        existing = {
            "id": _slug(name, {m["id"] for m in members}),
            "name": name,
            "color": color,
            "photo": "",
        }
        members.append(existing)
    else:
        existing["name"] = name
        existing["color"] = color
    if checked:
        media_dir().mkdir(parents=True, exist_ok=True)
        existing["photo"] = _store_media(f"family-{existing['id']}-photo{checked[0]}", checked[1])
    _save(members)
    return dict(existing)


def remove_member(mid):
    if not isinstance(mid, str) or not ID_PATTERN.fullmatch(mid):
        raise BadInput("id must be 1-64 of a-z, 0-9, -")
    members = read_family()
    removed = next((m for m in members if m["id"] == mid), None)
    if removed is None:
        raise KeyError(mid)
    photo = removed.get("photo") or ""
    if isinstance(photo, str) and photo.startswith("/media/"):
        filename = Path(photo).name
        if filename.startswith(f"family-{mid}-photo"):
            (media_dir() / filename).unlink(missing_ok=True)
    _save([m for m in members if m["id"] != mid])
    return removed
