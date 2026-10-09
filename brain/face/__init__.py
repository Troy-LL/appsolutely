"""Offline face match: YuNet finds a face, SFace scores it against the gallery."""

import os
import threading
import time
from pathlib import Path

# cv2 is imported on first use. A top-level import can stall on this Mac.
_MISSING = object()
cv2 = _MISSING
np = None

FACE_DIR = Path(__file__).resolve().parent
MODEL_DIR = FACE_DIR / "models"
YUNET_NAME = "face_detection_yunet_2023mar.onnx"
SFACE_NAME = "face_recognition_sface_2021dec.onnx"
YUNET = MODEL_DIR / YUNET_NAME
SFACE = MODEL_DIR / SFACE_NAME
DEFAULT_GALLERY = "brain/face/gallery"
PHOTO_SUFFIXES = {".jpg", ".jpeg", ".png"}
MAX_PHOTOS = 5
DISABLED = {"who": None, "score": 0, "faces": 0, "ms": 0, "reason": "face disabled"}


def _env_float(name, default):
    raw = os.environ.get(name, default)
    try:
        return float(raw)
    except ValueError:
        return float(default)


def _threshold():
    return _env_float("FACE_THRESHOLD", "0.40")


def _high_threshold():
    base = _threshold()
    high = _env_float("FACE_THRESHOLD_HIGH", "0.55")
    if high < base:
        return base
    return high


def _load_cv():
    global cv2, np
    if cv2 is None:
        return None
    if cv2 is not _MISSING:
        return cv2
    try:
        import cv2 as loaded_cv
        import numpy as loaded_np
    except ImportError:
        cv2 = None
        np = None
        return None
    cv2 = loaded_cv
    np = loaded_np
    return cv2


def _models_present():
    return YUNET.is_file() and SFACE.is_file()


def _ms(started):
    return int((time.perf_counter() - started) * 1000)


def _miss(started, faces=0, score=0.0):
    return {"who": None, "score": float(score), "faces": int(faces), "ms": _ms(started)}


def _rows_from(found):
    if isinstance(found, tuple):
        found = found[1] if len(found) > 1 else None
    if found is None:
        return []
    if hasattr(found, "ndim") and found.ndim == 1:
        return [found]
    try:
        if len(found) == 0:
            return []
    except TypeError:
        return []
    return list(found)


def _largest(rows):
    if not rows:
        return None

    def area(row):
        return float(row[2]) * float(row[3])

    return max(rows, key=area)


def _detected_rows(detector, image):
    height, width = image.shape[:2]
    if width == 0 or height == 0:
        raise ValueError("empty frame")
    if hasattr(detector, "setInputSize"):
        detector.setInputSize((width, height))
    return _rows_from(detector.detect(image))


def _score(recognizer, probe, stored):
    kind = 0
    if cv2 is not None and cv2 is not _MISSING:
        kind = getattr(cv2, "FaceRecognizerSF_FR_COSINE", 0)
    return float(recognizer.match(probe, stored, kind))


class NullGallery:
    @property
    def people(self):
        return []

    def identify(self, image_bgr):
        return dict(DISABLED)


class Gallery:
    def __init__(self, entries, detector, recognizer):
        self._entries = list(entries)
        self._detector = detector
        self._recognizer = recognizer

    @property
    def people(self):
        return sorted({name for name, _stored in self._entries})

    def identify(self, image_bgr):
        started = time.perf_counter()
        try:
            return self._identify(image_bgr, started)
        except Exception:
            return _miss(started)

    def _identify(self, image_bgr, started):
        if image_bgr is None or not hasattr(image_bgr, "shape"):
            raise ValueError("bad frame")
        rows = _detected_rows(self._detector, image_bgr)
        if not rows:
            return _miss(started)
        probe = self._recognizer.feature(self._recognizer.alignCrop(image_bgr, _largest(rows)))
        best_who = None
        best_score = None
        for name, stored in self._entries:
            score = _score(self._recognizer, probe, stored)
            if best_score is None or score > best_score:
                best_score = score
                best_who = name
        if best_score is None or best_score < _threshold():
            shown = 0.0 if best_score is None else best_score
            return _miss(started, faces=len(rows), score=shown)
        return {
            "who": best_who,
            "score": float(best_score),
            "faces": len(rows),
            "ms": _ms(started),
        }


def _resolve_gallery(path):
    given = Path(path)
    if given.is_dir():
        return given
    beside = FACE_DIR / "gallery"
    if path == DEFAULT_GALLERY and beside.is_dir():
        return beside
    return given


def _photo_paths(folder):
    photos = [
        path
        for path in sorted(folder.iterdir())
        if path.is_file() and path.suffix.lower() in PHOTO_SUFFIXES
    ]
    return photos[:MAX_PHOTOS]


def _open_models():
    detector = cv2.FaceDetectorYN.create(str(YUNET), "", (320, 320), 0.9, 0.3, 5000)
    recognizer = cv2.FaceRecognizerSF.create(str(SFACE), "")
    return detector, recognizer


def _embed_folder(folder, detector, recognizer):
    entries = []
    for photo in _photo_paths(folder):
        try:
            image = cv2.imread(str(photo))
            if image is None:
                continue
            face = _largest(_detected_rows(detector, image))
            if face is None:
                continue
            entries.append((folder.name, recognizer.feature(recognizer.alignCrop(image, face))))
        except Exception:
            continue
    return entries


def load_gallery(path=DEFAULT_GALLERY):
    if not _models_present() or _load_cv() is None:
        return NullGallery()
    try:
        detector, recognizer = _open_models()
        root = _resolve_gallery(path)
        entries = []
        if root.is_dir():
            for folder in sorted(path for path in root.iterdir() if path.is_dir()):
                entries.extend(_embed_folder(folder, detector, recognizer))
        return Gallery(entries, detector, recognizer)
    except Exception:
        return NullGallery()


def identify_jpeg(gallery, jpeg_bytes):
    image = None
    loaded = _load_cv()
    if loaded is not None and np is not None and jpeg_bytes:
        try:
            buffer = np.frombuffer(jpeg_bytes, dtype=np.uint8)
            image = loaded.imdecode(buffer, loaded.IMREAD_COLOR)
        except Exception:
            image = None
    return gallery.identify(image)


def line_who(result):
    who = result.get("who") if result else None
    try:
        score = float(result.get("score") or 0)
    except (AttributeError, TypeError, ValueError):
        return None
    if not who or score < _high_threshold():
        return None
    return who


def capture_frame(timeout_s=1.5):
    loaded = _load_cv()
    if loaded is None:
        return None
    held = {"cap": None, "frame": None}

    def grab():
        cap = None
        try:
            cap = loaded.VideoCapture(0)
            held["cap"] = cap
            if not cap.isOpened():
                return
            ok, image = cap.read()
            if ok and image is not None:
                held["frame"] = image
        except Exception:
            return
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass

    worker = threading.Thread(target=grab, daemon=True)
    worker.start()
    worker.join(timeout_s)
    return held["frame"]


def crop_face(image, face, margin=0.2):
    height, width = image.shape[:2]
    x, y, box_w, box_h = (float(face[0]), float(face[1]), float(face[2]), float(face[3]))
    pad = margin * max(box_w, box_h)
    x0 = max(0, int(x - pad))
    y0 = max(0, int(y - pad))
    x1 = min(width, int(x + box_w + pad))
    y1 = min(height, int(y + box_h + pad))
    if x1 <= x0 or y1 <= y0:
        return None
    return image[y0:y1, x0:x1]
