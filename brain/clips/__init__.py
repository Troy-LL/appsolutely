"""Recorded clips for Nasaan si Lola (docs/sino/features.md)."""

import asyncio
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path

from ask import NO_CAMERA_ANSWER
from clips.rooms import ROOMS, file_stems, room_id_for_stem, room_ids

# cv2 is imported on first use. A top-level import can stall on this Mac.
_MISSING = object()
_cv2 = _MISSING
_hog = None

SUFFIXES = {".mp4", ".mov", ".webm"}
FFMPEG_FIX = "ffmpeg -i in.mov -c:v libx264 -an out.mp4"
LABEL = "RECORDED CLIP · DEMO"
UNSURE_TEXT = "Hindi ko sigurado kung nasaan si Lola. Pakitingnan."
WIDTH = 640

_log = logging.getLogger("sino.clips")
_scan_lock = threading.Lock()
_rooms = {}
_winner = None


def media_dir():
    raw = os.environ.get("CLIP_MEDIA", "")
    if raw:
        return Path(raw)
    return Path(__file__).resolve().parent / "media"


def hog_min():
    raw = os.environ.get("CLIP_HOG_MIN", "0.5")
    try:
        value = float(raw)
    except ValueError:
        return 0.5
    return value


def _load_cv():
    global _cv2
    if _cv2 is None:
        return None
    if _cv2 is not _MISSING:
        return _cv2
    try:
        import cv2 as loaded
    except ImportError:
        _cv2 = None
        return None
    _cv2 = loaded
    return _cv2


def _skip(path, reason):
    _log.warning("skip %s: %s", path.name, reason)
    print(FFMPEG_FIX)


def _clip_files(folder):
    if not folder.is_dir():
        return []
    files = []
    for path in folder.iterdir():
        if path.is_file() and path.suffix.lower() in SUFFIXES:
            files.append(path)
    return sorted(files, key=lambda path: path.name)


def has_clips(folder=None):
    return bool(_clip_files(Path(folder) if folder else media_dir()))


def detect_people(frame):
    global _hog
    cv = _load_cv()
    if cv is None or frame is None:
        return []
    if _hog is None:
        detector = cv.HOGDescriptor()
        detector.setSVMDetector(cv.HOGDescriptor_getDefaultPeopleDetector())
        _hog = detector
    try:
        found = _hog.detectMultiScale(frame, winStride=(8, 8), padding=(8, 8), scale=1.05)
    except Exception:
        return []
    weights = found[1] if isinstance(found, tuple) and len(found) > 1 else None
    if weights is None:
        return []
    scores = []
    for weight in weights:
        try:
            scores.append(float(weight))
        except (TypeError, ValueError):
            scores.append(float(weight.ravel()[0]))
    return scores


def _resize(cv, frame):
    height, width = frame.shape[:2]
    if width <= 0 or height <= 0:
        return None
    if width == WIDTH:
        return frame
    new_height = max(1, int(round(height * (WIDTH / float(width)))))
    return cv.resize(frame, (WIDTH, new_height))


def _jpeg(cv, frame):
    ok, buf = cv.imencode(".jpg", frame)
    if not ok:
        return None
    return buf.tobytes()


def _fps(cv, cap):
    fps = cap.get(cv.CAP_PROP_FPS)
    if not fps or fps != fps or fps < 1:
        return 30.0
    return float(fps)


def _scan_file(cv, path):
    cap = cv.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            _skip(path, "could not open")
            return None
        fps = _fps(cv, cap)
        step = max(1, int(round(fps / 2.0)))
        index = 0
        frames = 0
        detections = 0
        prev = False
        hit = None
        saw_frame = False
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            saw_frame = True
            resized = _resize(cv, frame)
            scores = detect_people(resized) if resized is not None else []
            found = any(score >= hog_min() for score in scores)
            frames += 1
            if found:
                detections += 1
            if found and prev:
                jpeg = _jpeg(cv, resized) if resized is not None else None
                if jpeg:
                    hit = {
                        "room": room_id_for_stem(path.stem),
                        "clip_offset_s": index / fps,
                        "jpeg_bytes": jpeg,
                    }
            prev = found
            index += step
            grabbed = 0
            while grabbed < step - 1:
                if not cap.grab():
                    break
                grabbed += 1
            if step > 1 and grabbed < step - 1:
                break
        if not saw_frame:
            _skip(path, "no frames decoded")
            return None
        return {
            "room": room_id_for_stem(path.stem),
            "frames": frames,
            "detections": detections,
            "hit": hit,
        }
    finally:
        cap.release()


def _now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def scan(folder=None):
    global _rooms, _winner
    with _scan_lock:
        started = time.perf_counter()
        folder = Path(folder) if folder else media_dir()
        files = _clip_files(folder)
        cv = _load_cv() if files else None
        decoded = []
        frames = 0
        detections = 0
        rooms = {}
        if cv is None:
            if files:
                _log.warning("OpenCV is missing; no clip was scanned")
        else:
            for path in files:
                try:
                    outcome = _scan_file(cv, path)
                except Exception as exc:
                    _skip(path, str(exc) or "could not decode")
                    continue
                if outcome is None:
                    continue
                frames += outcome["frames"]
                detections += outcome["detections"]
                decoded.append(outcome["room"])
                hit = outcome["hit"]
                if not hit:
                    continue
                when = path.stat().st_mtime + hit["clip_offset_s"]
                record = {
                    "room": hit["room"],
                    "clip_offset_s": hit["clip_offset_s"],
                    "jpeg_bytes": hit["jpeg_bytes"],
                    "scanned_at": _now(),
                    "when": when,
                }
                previous = rooms.get(hit["room"])
                if previous is None or when >= previous["when"]:
                    rooms[hit["room"]] = record
        winner = None
        for record in rooms.values():
            if winner is None or record["when"] > winner["when"]:
                winner = record
        _rooms = rooms
        _winner = winner
        return {
            "rooms": sorted(set(decoded)),
            "frames": frames,
            "detections": detections,
            "ms": int((time.perf_counter() - started) * 1000),
        }


def scan_event(summary):
    return {
        "event": "clip_scan",
        "rooms": list(summary["rooms"]),
        "frames": summary["frames"],
        "detections": summary["detections"],
        "ms": summary["ms"],
    }


def scan_and_emit(loop, hub):
    try:
        summary = scan()
    except Exception as exc:
        _log.warning("scan failed: %s", exc)
        summary = {"rooms": [], "frames": 0, "detections": 0, "ms": 0}
    asyncio.run_coroutine_threadsafe(hub.send_to("backstage", scan_event(summary)), loop)


def last_seen_for_log():
    with _scan_lock:
        if not _winner:
            return None
        return {
            "room": _winner["room"],
            "clip_offset_s": _winner["clip_offset_s"],
            "source": "recording",
        }


def snapshot_jpeg(room=None):
    with _scan_lock:
        if room:
            record = _rooms.get(room)
            if not record:
                return None
            return record["jpeg_bytes"]
        if not _winner:
            return None
        return _winner["jpeg_bytes"]


def room_catalog(folder=None):
    """The three rooms, whether a file is on disk, and the last detected frame."""
    folder = Path(folder) if folder else media_dir()
    present = {room_id_for_stem(path.stem) for path in _clip_files(folder)}
    with _scan_lock:
        rows = []
        for spec in ROOMS:
            record = _rooms.get(spec["id"])
            rows.append({
                "id": spec["id"],
                "tl": spec["tl"],
                "en": spec["en"],
                "file": spec["id"] in present,
                "detected": record is not None,
                "clip_offset_s": None if record is None else record["clip_offset_s"],
                "scanned_at": "" if record is None else record["scanned_at"],
            })
        return rows


def clip_path(room, folder=None):
    if room not in room_ids():
        return None
    wanted = {stem.lower() for stem in file_stems(room)}
    folder = Path(folder) if folder else media_dir()
    for path in _clip_files(folder):
        if path.stem.lower() in wanted:
            return path
    return None


def room_rows():
    with _scan_lock:
        rows = []
        for record in _rooms.values():
            rows.append({
                "room": record["room"],
                "clip_offset_s": record["clip_offset_s"],
                "scanned_at": record["scanned_at"],
            })
        return rows


def followup(result, log):
    if not isinstance(result, dict) or result.get("intent") != "where":
        return {}, None
    last = log.get("last_seen") if isinstance(log, dict) else None
    if isinstance(last, dict) and last.get("source") == "recording" and last.get("room"):
        return {"snapshot": "/clips/snapshot", "label": LABEL}, None
    if result.get("answer") == NO_CAMERA_ANSWER:
        return {}, {"event": "clip_card", "text": UNSURE_TEXT}
    return {}, None
