"""The three recorded rooms. The clip file stem is English; the id is Tagalog."""

ROOMS = (
    {"id": "hagdan", "tl": "Hagdan", "en": "Stairs", "file": "stairs"},
    {"id": "kainan", "tl": "Kainan", "en": "Dining", "file": "dining"},
    {"id": "balkonahe", "tl": "Balkonahe", "en": "Balcony", "file": "balcony"},
)


def room_ids():
    return tuple(item["id"] for item in ROOMS)


def room_id_for_stem(stem):
    """Map stairs/dining/balcony (or the Tagalog id) onto the room id."""
    key = stem.lower() if isinstance(stem, str) else ""
    for item in ROOMS:
        if key == item["id"] or key == item["file"]:
            return item["id"]
    return stem if isinstance(stem, str) else ""


def file_stems(room):
    for item in ROOMS:
        if item["id"] == room:
            return (item["file"], item["id"])
    return ()


def room_label(room):
    """Tagalog name used in 'Nasaan si Lola?'. An unknown id is returned as given."""
    if not isinstance(room, str):
        return ""
    for item in ROOMS:
        if item["id"] == room:
            return item["tl"]
    return room
