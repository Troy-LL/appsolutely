"""Recorded clips for Nasaan si Lola (docs/sino/features.md)."""

import asyncio
import base64
import json
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
PERSON = 15  # VOC person class
DETECTOR_SSD = "mobilenet-ssd"
DETECTOR_HOG = "hog"
SSD_SCALE = 0.007843
SSD_SIZE = (300, 300)
SSD_MEAN = 127.5
BOX_COLOR = (40, 180, 40)

_log = logging.getLogger("sino.clips")
_scan_lock = threading.Lock()
_rooms = {}
_winner = None
_net = _MISSING
_boxes = []
_peak = None
_stats = {}
detect_calls = 0


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


def _model_paths():
    root = Path(__file__).resolve().parent / "models"
    return root / "deploy.prototxt", root / "mobilenet_iter_73000.caffemodel"


def detector_name():
    cv = _load_cv()
    if cv is not None and _ssd_net(cv) is not None:
        return DETECTOR_SSD
    return DETECTOR_HOG


def _ssd_net(cv):
    global _net
    if _net is None:
        return None
    if _net is not _MISSING:
        return _net
    proto, weights = _model_paths()
    if not proto.is_file() or not weights.is_file():
        _net = None
        return None
    try:
        _net = cv.dnn.readNetFromCaffe(str(proto), str(weights))
    except Exception:
        _net = None
        return None
    return _net


def _hog_hits(cv, frame):
    global _hog
    if _hog is None:
        detector = cv.HOGDescriptor()
        detector.setSVMDetector(cv.HOGDescriptor_getDefaultPeopleDetector())
        _hog = detector
    try:
        found = _hog.detectMultiScale(frame, winStride=(8, 8), padding=(8, 8), scale=1.05)
    except Exception:
        return []
    weights = found[1] if isinstance(found, tuple) and len(found) > 1 else None
    rects = found[0] if isinstance(found, tuple) else []
    if weights is None:
        return []
    hits = []
    for rect, weight in zip(rects, weights):
        try:
            score = float(weight)
        except (TypeError, ValueError):
            score = float(weight.ravel()[0])
        x, y, w, h = [int(v) for v in rect]
        if w <= 0 or h <= 0:
            continue
        hits.append({"score": score, "box": [x, y, x + w, y + h]})
    return hits


def _ssd_hits(cv, frame):
    net = _ssd_net(cv)
    if net is None:
        return _hog_hits(cv, frame)
    blob = cv.dnn.blobFromImage(frame, SSD_SCALE, SSD_SIZE, SSD_MEAN)
    net.setInput(blob)
    det = net.forward()
    height, width = frame.shape[:2]
    hits = []
    count = int(det.shape[2]) if len(det.shape) > 2 else 0
    for i in range(count):
        score = float(det[0, 0, i, 2])
        if int(det[0, 0, i, 1]) != PERSON:
            continue
        x1 = int(float(det[0, 0, i, 3]) * width)
        y1 = int(float(det[0, 0, i, 4]) * height)
        x2 = int(float(det[0, 0, i, 5]) * width)
        y2 = int(float(det[0, 0, i, 6]) * height)
        if x2 <= x1 or y2 <= y1:
            continue
        hits.append({"score": score, "box": [x1, y1, x2, y2]})
    return hits


def detect_people(frame):
    """Person scores for this frame. Passing boxes land in `_boxes`."""
    global _boxes, _peak, detect_calls
    detect_calls += 1
    _boxes = []
    _peak = None
    cv = _load_cv()
    if cv is None or frame is None:
        return []
    try:
        hits = _ssd_hits(cv, frame) if _ssd_net(cv) is not None else _hog_hits(cv, frame)
    except Exception:
        return []
    if hits:
        _peak = max(hit["score"] for hit in hits)
    passing = [hit for hit in hits if hit["score"] >= hog_min()]
    _boxes = passing
    return [hit["score"] for hit in passing]


def box_label(score):
    return f"Tao · {float(score):.2f}"


def _burn(cv, frame, box, score):
    image = frame.copy()
    height, width = image.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in box]
    x1 = max(0, min(width - 1, x1))
    y1 = max(0, min(height - 1, y1))
    x2 = max(x1 + 1, min(width, x2))
    y2 = max(y1 + 1, min(height, y2))
    cv.rectangle(image, (x1, y1), (x2, y2), BOX_COLOR, 2)
    font = cv.FONT_HERSHEY_SIMPLEX
    scale = 0.55
    thick = 1
    left = "Tao"
    right = f"{float(score):.2f}"
    (text_w, text_h), _ = cv.getTextSize(left, font, scale, thick)
    y = y1 - 8
    if y < text_h + 4:
        y = min(height - 4, y1 + text_h + 8)
    cv.putText(image, left, (x1, y), font, scale, BOX_COLOR, thick, cv.LINE_AA)
    dot_x = x1 + text_w + 7
    cv.circle(image, (dot_x, y - max(1, text_h // 3)), 2, BOX_COLOR, -1, cv.LINE_AA)
    cv.putText(image, right, (dot_x + 7, y), font, scale, BOX_COLOR, thick, cv.LINE_AA)
    return image


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
        global _boxes, _peak
        prev = False
        hit = None
        saw_frame = False
        peak = None
        peak_at = None
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            saw_frame = True
            resized = _resize(cv, frame)
            _boxes = []
            _peak = None
            scores = detect_people(resized) if resized is not None else []
            boxes = [dict(item) for item in _boxes]
            if _peak is not None and (peak is None or _peak > peak):
                peak = _peak
                peak_at = index / fps
            found = any(score >= hog_min() for score in scores)
            frames += 1
            if found:
                detections += 1
            if found and prev:
                image = resized
                best = max(boxes, key=lambda item: item["score"]) if boxes else None
                if best is not None and image is not None:
                    image = _burn(cv, image, best["box"], best["score"])
                jpeg = _jpeg(cv, image) if image is not None else None
                if jpeg:
                    hit = {
                        "room": room_id_for_stem(path.stem),
                        "clip_offset_s": index / fps,
                        "jpeg_bytes": jpeg,
                        "score": None if best is None else best["score"],
                        "box": None if best is None else list(best["box"]),
                        "file": path.name,
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
            "peak": peak,
            "peak_at": peak_at,
        }
    finally:
        cap.release()


def _now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def cache_path(folder=None):
    folder = Path(folder) if folder else media_dir()
    root = Path(__file__).resolve().parent
    try:
        if folder.resolve() == (root / "media").resolve():
            return root / "cache" / "scan.json"
    except OSError:
        pass
    return folder / "scan.json"


def _use_cache():
    return getattr(detect_people, "__module__", None) == __name__


def _stamp(folder):
    rows = []
    for path in _clip_files(folder):
        st = path.stat()
        rows.append({"name": path.name, "mtime_ns": st.st_mtime_ns, "size": st.st_size})
    return rows


def _read_cache(folder):
    path = cache_path(folder)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    if not isinstance(data, dict) or data.get("detector") != detector_name():
        return None
    if data.get("files") != _stamp(folder):
        return None
    return data


def _write_cache(folder, payload):
    path = cache_path(folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _finish(rooms):
    winner = None
    for record in rooms.values():
        if winner is None or record["when"] > winner["when"]:
            winner = record
    return winner


def _record_from_hit(path, hit):
    when = path.stat().st_mtime + hit["clip_offset_s"]
    return {
        "room": hit["room"],
        "clip_offset_s": hit["clip_offset_s"],
        "jpeg_bytes": hit["jpeg_bytes"],
        "scanned_at": _now(),
        "when": when,
        "score": hit.get("score"),
        "box": hit.get("box"),
        "detector": detector_name() if hit.get("box") is not None else "",
        "file": hit.get("file") or path.name,
    }


def _apply_cache(folder, cached, started):
    global _rooms, _winner, _stats
    hits = cached.get("hits")
    if not isinstance(hits, list):
        return None
    files = {path.name: path for path in _clip_files(folder)}
    rooms = {}
    for hit in hits:
        if not isinstance(hit, dict):
            return None
        path = files.get(hit.get("file"))
        box = hit.get("box")
        raw = hit.get("jpeg_b64")
        if path is None or not isinstance(raw, str) or not isinstance(box, list) or len(box) != 4:
            return None
        try:
            jpeg = base64.b64decode(raw)
            score = float(hit["score"])
            offset = float(hit["clip_offset_s"])
            box = [int(v) for v in box]
        except (TypeError, ValueError):
            return None
        if not jpeg.startswith(b"\xff\xd8"):
            return None
        record = _record_from_hit(path, {
            "room": hit.get("room"),
            "clip_offset_s": offset,
            "jpeg_bytes": jpeg,
            "score": score,
            "box": box,
            "file": path.name,
        })
        record["detector"] = hit.get("detector") or cached.get("detector") or ""
        previous = rooms.get(record["room"])
        if previous is None or record["when"] >= previous["when"]:
            rooms[record["room"]] = record
    _rooms = rooms
    _winner = _finish(rooms)
    _stats = {
        "detector": cached.get("detector"),
        "files": cached.get("file_stats") if isinstance(cached.get("file_stats"), dict) else {},
    }
    return {
        "rooms": list(cached.get("rooms") or []),
        "frames": int(cached.get("frames") or 0),
        "detections": int(cached.get("detections") or 0),
        "ms": int((time.perf_counter() - started) * 1000),
    }


def scan(folder=None):
    global _rooms, _winner, _stats
    with _scan_lock:
        started = time.perf_counter()
        folder = Path(folder) if folder else media_dir()
        files = _clip_files(folder)
        if files and _use_cache():
            cached = _read_cache(folder)
            if cached is not None:
                loaded = _apply_cache(folder, cached, started)
                if loaded is not None:
                    return loaded
        cv = _load_cv() if files else None
        decoded = []
        frames = 0
        detections = 0
        rooms = {}
        file_stats = {}
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
                file_stats[path.name] = {
                    "room": outcome["room"],
                    "frames": outcome["frames"],
                    "detections": outcome["detections"],
                    "peak": outcome["peak"],
                    "peak_s": outcome["peak_at"],
                }
                hit = outcome["hit"]
                if not hit:
                    continue
                record = _record_from_hit(path, hit)
                previous = rooms.get(hit["room"])
                if previous is None or record["when"] >= previous["when"]:
                    rooms[hit["room"]] = record
        _rooms = rooms
        _winner = _finish(rooms)
        _stats = {"detector": detector_name() if cv is not None else "", "files": file_stats}
        summary = {
            "rooms": sorted(set(decoded)),
            "frames": frames,
            "detections": detections,
            "ms": int((time.perf_counter() - started) * 1000),
        }
        if cv is not None and files and _use_cache() and _cache_ready(rooms):
            _write_cache(folder, _cache_payload(folder, summary, rooms, file_stats))
        return summary


def _cache_ready(rooms):
    for record in rooms.values():
        if record.get("box") is None or not record.get("jpeg_bytes"):
            return False
    return True


def _cache_payload(folder, summary, rooms, file_stats):
    hits = []
    for record in rooms.values():
        hits.append({
            "room": record["room"],
            "clip_offset_s": record["clip_offset_s"],
            "score": record["score"],
            "box": list(record["box"]),
            "detector": record.get("detector") or detector_name(),
            "file": record["file"],
            "jpeg_b64": base64.b64encode(record["jpeg_bytes"]).decode("ascii"),
        })
    return {
        "detector": detector_name(),
        "files": _stamp(folder),
        "rooms": summary["rooms"],
        "frames": summary["frames"],
        "detections": summary["detections"],
        "file_stats": file_stats,
        "hits": hits,
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


def room_sighting(room):
    with _scan_lock:
        record = _rooms.get(room)
        if not record or record.get("box") is None:
            return None
        return {
            "room": record["room"],
            "clip_offset_s": record["clip_offset_s"],
            "score": record["score"],
            "box": list(record["box"]),
            "detector": record.get("detector") or detector_name(),
        }


def last_stats():
    with _scan_lock:
        files = _stats.get("files") if isinstance(_stats.get("files"), dict) else {}
        copied = {}
        for name, row in files.items():
            copied[name] = dict(row) if isinstance(row, dict) else row
        return {"detector": _stats.get("detector"), "files": copied}


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
    matches = [path for path in _clip_files(folder) if path.stem.lower() in wanted]
    matches.sort(key=lambda path: (path.suffix.lower() != ".mp4", path.name))
    return matches[0] if matches else None


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
