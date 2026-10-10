"""Recorded-clip where: room, clip time, snapshot, and the unsure card.

Run from the worktree root:

    SINO_MODEL=stub .venv/bin/python brain/tests/test_clips.py
"""

import asyncio
import json
import logging
import os
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRAIN = HERE.parent
sys.path.insert(0, str(BRAIN))

os.environ["SINO_MODEL"] = "stub"
os.environ["OFFLINE_PROBE"] = "http://127.0.0.1:9"
os.environ.pop("CERT", None)
os.environ.pop("KEY", None)

import clips  # noqa: E402
from ask import NO_CAMERA_ANSWER, answer_about_lola  # noqa: E402

REAL_DETECT = clips.detect_people


def _write_clip(path, frames, fps=2):
    import cv2
    import numpy as np

    size = (160, 120)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    if not writer.isOpened():
        raise RuntimeError(f"could not write {path}")
    for index in range(frames):
        image = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        image[:, :] = (index, 40, 80)
        writer.write(image)
    writer.release()


def _hits(scores):
    plan = list(scores)

    def detect(_frame):
        if not plan:
            return [0.0]
        return [plan.pop(0)]

    return detect


def _where(log):
    return answer_about_lola("Nasaan si Lola?", log)


def _recording_log():
    seen = clips.last_seen_for_log()
    return {"entries": [], "last_seen": seen}


def test_person_room_time_snapshot():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        _write_clip(folder / "sala.mp4", 5)
        clips.detect_people = _hits([0.9, 0.9, 0.9, 0.9, 0.9])
        summary = clips.scan(folder)
        seen = clips.last_seen_for_log()
        if seen != {"room": "sala", "clip_offset_s": 2.0, "source": "recording"}:
            raise AssertionError(seen)
        if summary["rooms"] != ["sala"] or summary["frames"] != 5 or summary["detections"] != 5:
            raise AssertionError(summary)
        result = _where(_recording_log())
        if result["answer"] != "Huling nakita sa recording: Sala (clip 0:02).":
            raise AssertionError(result["answer"])
        extra, card = clips.followup(result, _recording_log())
        if extra != {"snapshot": "/clips/snapshot", "label": clips.LABEL}:
            raise AssertionError(extra)
        if card is not None:
            raise AssertionError(card)
        jpeg = clips.snapshot_jpeg()
        if not isinstance(jpeg, bytes) or not jpeg.startswith(b"\xff\xd8"):
            raise AssertionError(jpeg[:4] if isinstance(jpeg, bytes) else jpeg)
        if "ngayon" in result["answer"].lower() or "minuto na" in result["answer"].lower():
            raise AssertionError(result["answer"])


def test_empty_clip_card():
    clips.detect_people = REAL_DETECT
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        _write_clip(folder / "sala.mp4", 2)
        summary = clips.scan(folder)
        if clips.last_seen_for_log() is not None:
            raise AssertionError(clips.last_seen_for_log())
        if summary["detections"] != 0:
            raise AssertionError(summary)
        result = _where({"entries": [], "last_seen": None})
        if result["answer"] != NO_CAMERA_ANSWER:
            raise AssertionError(result["answer"])
        extra, card = clips.followup(result, {"entries": []})
        if extra or card != {"event": "clip_card", "text": clips.UNSURE_TEXT}:
            raise AssertionError((extra, card))
        if "Hindi ko sigurado" not in card["text"]:
            raise AssertionError(card)


def test_later_sighting_wins():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        sala = folder / "sala.mp4"
        kusina = folder / "kusina.mp4"
        _write_clip(sala, 25)
        _write_clip(kusina, 3)
        os.utime(sala, (9990, 9990))
        os.utime(kusina, (10000, 10000))
        clips.detect_people = lambda _frame: [0.8]
        clips.scan(folder)
        seen = clips.last_seen_for_log()
        if seen["room"] != "sala" or seen["clip_offset_s"] != 12.0:
            raise AssertionError(seen)
        answer = _where(_recording_log())["answer"]
        if answer != "Huling nakita sa recording: Sala (clip 0:12).":
            raise AssertionError(answer)


def test_unreadable_skipped():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        fake = folder / "sala.mov"
        fake.write_bytes(b"\x00\x00\x00\x18ftyphevcnot-a-real-file")
        handler = logging.Handler()
        notes = []
        handler.emit = lambda record: notes.append(record.getMessage())
        log = logging.getLogger("sino.clips")
        log.addHandler(handler)
        log.setLevel(logging.WARNING)
        printed = []
        real_print = __builtins__["print"] if isinstance(__builtins__, dict) else __builtins__.print

        def capture(*args, **kwargs):
            printed.append(" ".join(str(arg) for arg in args))
            real_print(*args, **kwargs)

        try:
            import builtins
            builtins.print = capture
            summary = clips.scan(folder)
        finally:
            import builtins
            builtins.print = real_print
            log.removeHandler(handler)
        if clips.last_seen_for_log() is not None:
            raise AssertionError(clips.last_seen_for_log())
        if summary["rooms"] or summary["frames"]:
            raise AssertionError(summary)
        if not any("sala.mov" in note for note in notes):
            raise AssertionError(notes)
        if clips.FFMPEG_FIX not in printed:
            raise AssertionError(printed)


def test_no_clips_card():
    with tempfile.TemporaryDirectory() as tmp:
        summary = clips.scan(Path(tmp))
        if summary["rooms"] or summary["frames"] or summary["detections"]:
            raise AssertionError(summary)
        if clips.last_seen_for_log() is not None:
            raise AssertionError(clips.last_seen_for_log())
        result = _where({"entries": []})
        extra, card = clips.followup(result, {"entries": []})
        if result["answer"] != NO_CAMERA_ANSWER:
            raise AssertionError(result["answer"])
        if "Hindi ko sigurado" not in card["text"]:
            raise AssertionError(card)
        if extra:
            raise AssertionError(extra)


def test_one_detection_does_not_count():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        _write_clip(folder / "sala.mp4", 5)
        clips.detect_people = _hits([0.9, 0.1, 0.1, 0.1, 0.1])
        summary = clips.scan(folder)
        if clips.last_seen_for_log() is not None:
            raise AssertionError(clips.last_seen_for_log())
        if summary["detections"] != 1:
            raise AssertionError(summary)
        clips.detect_people = lambda _frame: [0.49]
        clips.scan(folder)
        if clips.last_seen_for_log() is not None:
            raise AssertionError("score under CLIP_HOG_MIN counted")


def test_room_names():
    from clips.rooms import ROOMS, room_label

    ids = [item["id"] for item in ROOMS]
    if ids != ["hagdan", "sala", "balkonahe"]:
        raise AssertionError(ids)
    if room_label("hagdan") != "Hagdan" or room_label("balkonahe") != "Balkonahe":
        raise AssertionError(room_label("hagdan"))
    if room_label("sala") != "Sala" or room_label("kusina") != "kusina":
        raise AssertionError(room_label("kusina"))
    names = [row["id"] for row in clips.room_catalog(Path("/tmp/sino-no-such-clips"))]
    if names != ["hagdan", "sala", "balkonahe"]:
        raise AssertionError(names)
    if any(row["file"] for row in clips.room_catalog(Path("/tmp/sino-no-such-clips"))):
        raise AssertionError("missing folder looked like footage")


def test_recording_wording():
    log = {
        "entries": [],
        "last_seen": {"room": "sala", "clip_offset_s": 42, "source": "recording"},
    }
    answer = _where(log)["answer"]
    if answer != "Huling nakita sa recording: Sala (clip 0:42).":
        raise AssertionError(answer)
    if "ngayon" in answer.lower() or "minuto na" in answer.lower():
        raise AssertionError(answer)
    kept = _where({"entries": [], "last_seen": {"room": "kusina", "minutes_ago": 1}})
    if kept["answer"] != "Nasa kusina, 1 minuto na.":
        raise AssertionError(kept["answer"])


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _multipart(filename, payload):
    boundary = "----clipboundary"
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="clip"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    tail = f"\r\n--{boundary}--\r\n".encode()
    return boundary, head + payload + tail


async def _recv(ws, timeout=3):
    import websockets

    del websockets
    return json.loads(await asyncio.wait_for(ws.recv(), timeout))


async def _quiet(ws):
    try:
        msg = await asyncio.wait_for(ws.recv(), 0.2)
    except asyncio.TimeoutError:
        return
    raise AssertionError(f"unexpected {msg}")


async def test_server_paths():
    import uvicorn
    import websockets

    import server

    media = tempfile.TemporaryDirectory()
    log_path = Path(media.name) / "decisions.jsonl"
    os.environ["CLIP_MEDIA"] = media.name
    os.environ["SINO_LOG"] = str(log_path)
    port = _free_port()
    config = uvicorn.Config(server.app, host="127.0.0.1", port=port, log_level="error")
    runner = uvicorn.Server(config)
    thread = threading.Thread(target=runner.run, daemon=True)
    thread.start()
    real_detect = REAL_DETECT
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.3) as res:
                    if res.status == 200:
                        break
            except OSError:
                await asyncio.sleep(0.05)
        else:
            raise AssertionError("server did not start")
        async with websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=backstage") as backstage, \
                websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=lola") as lola, \
                websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=caregiver") as caregiver:
            for ws in (backstage, lola, caregiver):
                health = await _recv(ws)
                if health.get("event") != "health":
                    raise AssertionError(health)
            await _quiet(backstage)

            clip_path = Path(media.name) / "sala.mp4"
            _write_clip(clip_path, 5)
            clips.detect_people = _hits([0.9, 0.9, 0.9, 0.9, 0.9])
            boundary, body = _multipart("sala.mp4", clip_path.read_bytes())
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/clips",
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as res:
                posted = json.loads(res.read().decode("utf-8"))
            if posted["rooms"] != ["sala"] or posted["detections"] != 5:
                raise AssertionError(posted)
            scan = await _recv(backstage)
            if scan.get("event") != "clip_scan" or scan.get("rooms") != ["sala"]:
                raise AssertionError(scan)
            if not isinstance(scan.get("ms"), int):
                raise AssertionError(scan)
            await caregiver.send(json.dumps({"event": "ask_about_lola", "question": "Nasaan si Lola?"}))
            reply = await _recv(caregiver)
            if reply.get("answer") != "Huling nakita sa recording: Sala (clip 0:02).":
                raise AssertionError(reply)
            if reply.get("snapshot") != "/clips/snapshot" or reply.get("label") != clips.LABEL:
                raise AssertionError(reply)
            if "ngayon" in reply["answer"].lower() or "minuto na" in reply["answer"].lower():
                raise AssertionError(reply["answer"])
            await _quiet(caregiver)
            await _quiet(lola)
            await _quiet(backstage)
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/clips/snapshot", timeout=2) as res:
                shot = res.read()
                if res.status != 200 or res.headers.get("Content-Type") != "image/jpeg":
                    raise AssertionError(res.status)
            if not shot.startswith(b"\xff\xd8"):
                raise AssertionError(shot[:4])
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/clips/snapshot?room=sala", timeout=2) as res:
                if res.status != 200 or not res.read().startswith(b"\xff\xd8"):
                    raise AssertionError("room snapshot")
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/clips/rooms", timeout=2) as res:
                catalog = json.loads(res.read().decode("utf-8"))
            ids = [row["id"] for row in catalog["rooms"]]
            if ids != ["hagdan", "sala", "balkonahe"]:
                raise AssertionError(ids)
            sala = next(row for row in catalog["rooms"] if row["id"] == "sala")
            if not sala["file"] or not sala["detected"] or sala["tl"] != "Sala":
                raise AssertionError(sala)
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/clips/file/sala", timeout=2) as res:
                if res.status != 200 or res.headers.get("Content-Type") != "video/mp4":
                    raise AssertionError(res.headers.get("Content-Type"))
            missing = urllib.request.Request(f"http://127.0.0.1:{port}/clips/file/kusina")
            try:
                urllib.request.urlopen(missing, timeout=2)
            except urllib.error.HTTPError as exc:
                if exc.code != 404:
                    raise AssertionError(exc.code) from exc
            else:
                raise AssertionError("unknown room was served")

            for path in Path(media.name).glob("*.mp4"):
                path.unlink()
            (Path(media.name) / "gone.mov").write_bytes(b"\x00\x00\x00\x18ftyphevcnot-a-real-file")
            clips.detect_people = real_detect
            empty = urllib.request.Request(f"http://127.0.0.1:{port}/clips", data=b"", method="POST")
            with urllib.request.urlopen(empty, timeout=5) as res:
                again = json.loads(res.read().decode("utf-8"))
            if again["rooms"] or again["detections"]:
                raise AssertionError(again)
            await _recv(backstage)
            await caregiver.send(json.dumps({"event": "ask_about_lola", "question": "Nasaan si Lola?"}))
            reply = await _recv(caregiver)
            if reply.get("answer") != NO_CAMERA_ANSWER or "snapshot" in reply or "label" in reply:
                raise AssertionError(reply)
            card = await _recv(caregiver)
            if card != {"event": "clip_card", "text": clips.UNSURE_TEXT}:
                raise AssertionError(card)
            if "Hindi ko sigurado" not in card["text"]:
                raise AssertionError(card)
            await _quiet(lola)
            await _quiet(backstage)
    finally:
        clips.detect_people = real_detect
        runner.should_exit = True
        thread.join(timeout=5)
        media.cleanup()


def main():
    tests = [
        test_person_room_time_snapshot,
        test_empty_clip_card,
        test_later_sighting_wins,
        test_unreadable_skipped,
        test_no_clips_card,
        test_one_detection_does_not_count,
        test_room_names,
        test_recording_wording,
    ]
    passed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"{test.__name__}: PASS")
        except Exception as exc:
            print(f"{test.__name__}: FAIL {exc}")
    try:
        asyncio.run(test_server_paths())
        passed += 1
        print("test_server_paths: PASS")
    except Exception as exc:
        print(f"test_server_paths: FAIL {exc}")
    total = len(tests) + 1
    print(f"PASS {passed}/{total}")
    return passed == total


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
