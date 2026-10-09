"""enroll, watch, and offline tests for the face gallery."""

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

import brain.face as face


def _safe_name(name):
    cleaned = name.strip()
    if not cleaned or cleaned in {".", ".."} or "/" in cleaned or "\\" in cleaned:
        print("name must be one folder name", file=sys.stderr)
        return None
    return cleaned


def _person_dir(name):
    cleaned = _safe_name(name)
    if cleaned is None:
        return None
    folder = face.FACE_DIR / "gallery" / cleaned
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _ready_gallery():
    gallery = face.load_gallery()
    if isinstance(gallery, face.NullGallery):
        print(
            "face match is disabled: pip install -r brain/requirements.txt && sh brain/face/get_models.sh",
            file=sys.stderr,
        )
        return None
    return gallery


def enroll_photo(name, photo):
    source = Path(photo)
    if source.suffix.lower() not in face.PHOTO_SUFFIXES or not source.is_file():
        print("photo must be an existing jpg or png", file=sys.stderr)
        return 1
    folder = _person_dir(name)
    if folder is None:
        return 1
    dest = folder / source.name
    shutil.copyfile(source, dest)
    print(f"saved {name}")
    return 0


def enroll_webcam(name):
    if _safe_name(name) is None:
        return 1
    gallery = _ready_gallery()
    if gallery is None:
        return 1
    folder = _person_dir(name)
    saved = 0
    for index in range(3):
        if index:
            time.sleep(1)
        frame = face.capture_frame()
        if frame is None:
            print(f"{name} frame {index + 1}: no frame")
            continue
        try:
            found = face._largest(face._detected_rows(gallery._detector, frame))
            crop = None if found is None else face.crop_face(frame, found)
        except Exception:
            crop = None
        if crop is None or not face.cv2.imwrite(str(folder / f"{index + 1}.jpg"), crop):
            print(f"{name} frame {index + 1}: no face")
            continue
        saved += 1
        print(f"saved {name}")
    if saved == 0:
        print("no face enrolled", file=sys.stderr)
        return 1
    return 0


def watch_webcam():
    gallery = _ready_gallery()
    if gallery is None:
        return 1
    frame = face.capture_frame()
    if frame is None:
        print("no camera reachable", file=sys.stderr)
    result = gallery.identify(frame)
    who = "None" if result["who"] is None else result["who"]
    print(f"{who} {result['score']:.3f} {result['ms']}", flush=True)
    return 0 if frame is not None else 1


class _Blank:
    shape = (48, 64, 3)

    def max(self):
        return 0


def _blank():
    return _Blank()


def _cosine(left, right):
    def flat(value):
        if hasattr(value, "tolist"):
            value = value.tolist()
        if isinstance(value, list) and value and isinstance(value[0], list):
            return [float(item) for row in value for item in row]
        return [float(item) for item in value]

    a = flat(left)
    b = flat(right)
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class _OneFace:
    def detect(self, image):
        return [[0, 0, 30, 40, 0.99]]


class _Quiet:
    def detect(self, image):
        if float(image.max()) == 0:
            return None
        return [[0, 0, 30, 40, 0.99]]


class _Boom:
    def detect(self, image):
        raise RuntimeError("bad frame")


class _Cosine:
    def __init__(self, probe):
        self.probe = probe

    def alignCrop(self, image, found):
        return image

    def feature(self, aligned):
        return self.probe

    def match(self, probe, stored, dis_type):
        return _cosine(probe, stored)


class _Fixed:
    def __init__(self, score):
        self.score = score

    def alignCrop(self, image, found):
        return image

    def feature(self, aligned):
        return (1.0, 0.0)

    def match(self, probe, stored, dis_type):
        return self.score


def _set_threshold(value):
    previous = os.environ.get("FACE_THRESHOLD")
    os.environ["FACE_THRESHOLD"] = value
    return previous


def _restore_threshold(previous):
    if previous is None:
        os.environ.pop("FACE_THRESHOLD", None)
    else:
        os.environ["FACE_THRESHOLD"] = previous


class _FakeNp:
    uint8 = 0

    def frombuffer(self, data, dtype=None):
        return data


class _FakeCv:
    FaceRecognizerSF_FR_COSINE = 0
    IMREAD_COLOR = 1

    def imdecode(self, buffer, flag):
        return None


def test_null_gallery():
    gallery = face.NullGallery()
    assert gallery.people == []
    assert gallery.identify(object()) == {
        "who": None,
        "score": 0,
        "faces": 0,
        "ms": 0,
        "reason": "face disabled",
    }
    saved_yunet, saved_sface, saved_cv = face.YUNET, face.SFACE, face.cv2
    face.YUNET = face.MODEL_DIR / "missing-yunet.onnx"
    face.SFACE = face.MODEL_DIR / "missing-sface.onnx"
    try:
        loaded = face.load_gallery()
    finally:
        face.YUNET = saved_yunet
        face.SFACE = saved_sface
        face.cv2 = saved_cv
    assert isinstance(loaded, face.NullGallery)
    assert loaded.identify(None)["reason"] == "face disabled"
    present = face.FACE_DIR / "gallery" / "README.md"
    face.YUNET = present
    face.SFACE = present
    face.cv2 = None
    try:
        disabled = face.load_gallery()
    finally:
        face.YUNET = saved_yunet
        face.SFACE = saved_sface
        face.cv2 = saved_cv
    assert isinstance(disabled, face.NullGallery)
    assert face.line_who(disabled.identify(None)) is None


def test_bad_frame():
    gallery = face.Gallery([], _Boom(), None)
    for frame in (None, b"not-a-frame", object()):
        result = gallery.identify(frame)
        assert result["who"] is None, result
        assert "reason" not in result
    jpeg = face.identify_jpeg(gallery, b"not-a-jpeg")
    assert jpeg["who"] is None


def test_blank_frame():
    gallery = face.Gallery([], _Quiet(), None)
    result = gallery.identify(_blank())
    assert result["who"] is None and result["faces"] == 0, result
    assert face.line_who(result) is None


def test_threshold():
    previous = _set_threshold("0.40")
    try:
        entries = [("troy", (1.0, 0.0)), ("joy", (0.0, 1.0)), ("troy", (0.9, 0.1))]
        troy = face.Gallery(entries, _OneFace(), _Cosine((1.0, 0.0)))
        hit = troy.identify(_blank())
        assert hit["who"] == "troy" and hit["score"] == 1.0 and hit["faces"] == 1, hit
        joy = face.Gallery(entries, _OneFace(), _Cosine((0.0, 1.0)))
        other = joy.identify(_blank())
        assert other["who"] == "joy" and other["faces"] == 1, other
        below = face.Gallery([("troy", (1.0, 0.0))], _OneFace(), _Fixed(0.39))
        missed = below.identify(_blank())
        assert missed["who"] is None and missed["score"] == 0.39, missed
        edge = face.Gallery([("troy", (1.0, 0.0))], _OneFace(), _Fixed(0.40))
        matched = edge.identify(_blank())
        assert matched["who"] == "troy" and matched["score"] == 0.40, matched
        assert face.line_who(matched) is None
        weak = face.Gallery([("joy", (0.0, 1.0))], _OneFace(), _Fixed(0.54))
        named = weak.identify(_blank())
        assert named["who"] == "joy" and face.line_who(named) is None, named
        strong = face.Gallery([("joy", (0.0, 1.0))], _OneFace(), _Fixed(0.55))
        play = strong.identify(_blank())
        assert play["who"] == "joy" and face.line_who(play) == "joy", play
        empty = face.Gallery([], _OneFace(), _Cosine((1.0, 0.0)))
        nobody = empty.identify(_blank())
        assert nobody["who"] is None and nobody["faces"] == 1 and nobody["score"] == 0.0
        assert face.Gallery(entries, _OneFace(), _Fixed(1)).people == ["joy", "troy"]
    finally:
        _restore_threshold(previous)


def test_one_frame():
    released = []

    class Closed:
        def isOpened(self):
            return False

        def release(self):
            released.append("closed")

    class Slow:
        def isOpened(self):
            return True

        def read(self):
            time.sleep(0.4)
            return True, _blank()

        def release(self):
            released.append("slow")

    class Opened:
        def isOpened(self):
            return True

        def read(self):
            return True, _blank()

        def release(self):
            released.append("opened")

    class Cv:
        def __init__(self, cap):
            self.cap = cap

        def VideoCapture(self, index):
            return self.cap

    saved = face.cv2
    try:
        face.cv2 = Cv(Closed())
        assert face.capture_frame(timeout_s=0.5) is None
        face.cv2 = Cv(Slow())
        started = time.perf_counter()
        missed = face.capture_frame(timeout_s=0.05)
        elapsed = time.perf_counter() - started
        assert missed is None and elapsed < 0.3, elapsed
        assert "slow" in released, "timed-out capture must release the camera"
        face.cv2 = Cv(Opened())
        got = face.capture_frame(timeout_s=0.5)
        assert got is not None
    finally:
        face.cv2 = saved
    assert released == ["closed", "slow", "opened"]


def run_tests():
    import builtins

    real_import = builtins.__import__

    def guarded(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "cv2" or name.startswith("cv2."):
            raise AssertionError("test imported cv2")
        return real_import(name, globals, locals, fromlist, level)

    builtins.__import__ = guarded
    saved_cv, saved_np = face.cv2, face.np
    face.cv2 = _FakeCv()
    face.np = _FakeNp()
    tests = (
        test_null_gallery,
        test_bad_frame,
        test_blank_frame,
        test_threshold,
        test_one_frame,
    )
    failed = 0
    try:
        for test in tests:
            try:
                test()
            except Exception as exc:
                failed += 1
                print(f"fail {test.__name__}: {exc}")
            else:
                print(f"pass {test.__name__}")
    finally:
        builtins.__import__ = real_import
        face.cv2 = saved_cv
        face.np = saved_np
    if failed:
        raise SystemExit(1)
    print(f"ok {len(tests)}")


def main(argv):
    parser = argparse.ArgumentParser(prog="python3 -m brain.face")
    commands = parser.add_subparsers(dest="cmd", required=True)

    enroll = commands.add_parser("enroll")
    enroll.add_argument("name")
    source = enroll.add_mutually_exclusive_group(required=True)
    source.add_argument("--webcam", action="store_true")
    source.add_argument("--photo")

    watch = commands.add_parser("watch")
    watch.add_argument("--webcam", action="store_true", required=True)

    commands.add_parser("test")
    args = parser.parse_args(argv)
    if args.cmd == "test":
        run_tests()
        return 0
    if args.cmd == "enroll":
        if args.webcam:
            return enroll_webcam(args.name)
        return enroll_photo(args.name, args.photo)
    if args.cmd == "watch":
        return watch_webcam()
    print(f"unknown command {args.cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
