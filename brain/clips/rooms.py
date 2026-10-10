"""The three recorded rooms. The id is the clip filename (hagdan.mp4)."""

ROOMS = (
    {"id": "hagdan", "tl": "Hagdan", "en": "Stairs"},
    {"id": "sala", "tl": "Sala", "en": "Living room"},
    {"id": "balkonahe", "tl": "Balkonahe", "en": "Balcony"},
)


def room_ids():
    return tuple(item["id"] for item in ROOMS)


def room_label(room):
    """Tagalog name used in 'Nasaan si Lola?'. An unknown id is returned as given."""
    if not isinstance(room, str):
        return ""
    for item in ROOMS:
        if item["id"] == room:
            return item["tl"]
    return room
