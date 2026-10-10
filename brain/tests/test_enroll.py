"""Hub face enrollment and the caregiver monitor socket.

Run from the repo root:

    SINO_MODEL=stub python3 brain/tests/test_enroll.py
"""

import asyncio
import base64
import json
import os
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

_TMP = Path(tempfile.mkdtemp(prefix="sino-enroll-"))
os.environ["SINO_MODEL"] = "stub"
os.environ["SINO_LOG"] = str(_TMP / "decisions.jsonl")
os.environ["FACE_GALLERY"] = str(_TMP / "gallery")
os.environ["HUB_DATA"] = str(_TMP / "hub")
os.environ["OFFLINE_PROBE"] = "http://127.0.0.1:9"
os.environ["HUB_URL"] = "http://127.0.0.1:9"
os.environ.pop("CERT", None)
os.environ.pop("KEY", None)

import uvicorn  # noqa: E402
import websockets  # noqa: E402

import server  # noqa: E402
import questions  # noqa: E402

TINY_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0a"
    "HBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIy"
    "MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEB"
    "AxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9"
    "AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6"
    "Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ip"
    "qrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEB"
    "AQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJB"
    "UQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RV"
    "VldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6"
    "wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3+iiigD//2Q=="
)
TV_LINE = "Abangan ang susunod na kabanata"
PEOPLE = ("troy", "joy", "donita")


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _multipart(fields, files):
    boundary = uuid.uuid4().hex
    body = b""
    for name, value in fields:
        body += (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        ).encode("utf-8")
    for name, filename, data in files:
        body += (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
            f'filename="{filename}"\r\nContent-Type: image/jpeg\r\n\r\n'
        ).encode("utf-8") + data + b"\r\n"
    body += f"--{boundary}--\r\n".encode("utf-8")
    return body, f"multipart/form-data; boundary={boundary}"


def _request(port, path, data=None, content_type=None, method=None):
    if method is None:
        method = "POST" if data is not None else "GET"
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        method=method,
    )
    if content_type:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            raw = res.read()
            return res.status, json.loads(raw.decode("utf-8") or "null")
    except urllib.error.HTTPError as err:
        raw = err.read()
        return err.code, json.loads(raw.decode("utf-8") or "null")


def _files(root):
    if not root.exists():
        return []
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    )


async def _recv(ws, timeout=3):
    return json.loads(await asyncio.wait_for(ws.recv(), timeout))


async def _quiet(ws, timeout=0.3):
    try:
        msg = await asyncio.wait_for(ws.recv(), timeout)
    except asyncio.TimeoutError:
        return
    raise AssertionError(f"unexpected {msg}")


async def _wait_up(port):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.3) as res:
                if res.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            await asyncio.sleep(0.05)
    raise RuntimeError("server did not start")


def _check_gallery(port):
    status, body = _request(port, "/face/gallery")
    if status != 200:
        raise AssertionError(status)
    if body.get("engine") not in ("ok", "missing"):
        raise AssertionError(body.get("engine"))
    people = body.get("people")
    if not isinstance(people, dict) or set(people) != set(PEOPLE):
        raise AssertionError(people)
    if not all(isinstance(people[name], int) for name in PEOPLE):
        raise AssertionError(people)


def _check_visitor(port):
    status, body = _request(
        port,
        "/face/enroll/visitor",
        *_multipart([], [("frames", "a.jpg", TINY_JPEG)]),
    )
    if status != 400 or body != {"error": "unknown person"}:
        raise AssertionError((status, body))


def _check_enroll(port):
    gallery = Path(os.environ["FACE_GALLERY"])
    before = _files(gallery)
    status, body = _request(
        port,
        "/face/enroll/troy",
        *_multipart([], [("frames", "a.jpg", TINY_JPEG)]),
    )
    if status != 200:
        raise AssertionError(status)
    frames = body.get("frames")
    if body.get("person") != "troy" or not isinstance(frames, list) or len(frames) != 1:
        raise AssertionError(body)
    frame = frames[0]
    if frame.get("ok") is True:
        pass
    elif frame.get("reason") not in ("no_face", "engine_missing"):
        raise AssertionError(frame)
    if body.get("engine") == "missing":
        if frame != {"ok": False, "reason": "engine_missing"}:
            raise AssertionError(frame)
        if _files(gallery) != before:
            raise AssertionError(_files(gallery))
    elif body.get("engine") == "ok":
        if frame != {"ok": False, "reason": "no_face"} or body.get("count") != 0:
            raise AssertionError(body)
    else:
        raise AssertionError(body.get("engine"))
    if not isinstance(body.get("count"), int):
        raise AssertionError(body.get("count"))


def _check_frame(port):
    status, body = _request(
        port,
        "/face/frame",
        TINY_JPEG,
        "image/jpeg",
    )
    if status != 200 or set(body) != {"who", "score", "faces", "ms"}:
        raise AssertionError((status, body))
    if body["who"] is not None and not isinstance(body["who"], str):
        raise AssertionError(body["who"])


def _check_photo():
    seed = questions.SEED
    before = seed.read_bytes()
    media = questions.set_by_person_photo_if_empty("troy", TINY_JPEG)
    if media != "/media/sino-ka-troy-photo.jpg":
        raise AssertionError(media)
    if seed.read_bytes() != before:
        raise AssertionError("seed changed")
    stored = Path(os.environ["HUB_DATA"]) / "media" / "sino-ka-troy-photo.jpg"
    if stored.read_bytes() != TINY_JPEG:
        raise AssertionError(stored)
    listed = json.loads(questions.questions_path().read_text(encoding="utf-8"))
    sino = next(entry for entry in listed if entry.get("id") == "sino-ka")
    if sino["by_person"]["troy"]["photo"] != media:
        raise AssertionError(sino["by_person"]["troy"])
    again = questions.set_by_person_photo_if_empty("troy", b"next")
    if again is not None or stored.read_bytes() != TINY_JPEG:
        raise AssertionError(again)
    if seed.read_bytes() != before:
        raise AssertionError("seed changed")
    hub = os.environ["HUB_DATA"]
    link_dir = _TMP / "seed-link"
    link_dir.mkdir()
    os.symlink(seed, link_dir / "questions.json")
    os.environ["HUB_DATA"] = str(link_dir)
    try:
        skipped = questions.set_by_person_photo_if_empty("joy", TINY_JPEG)
        if skipped is not None or seed.read_bytes() != before:
            raise AssertionError(skipped)
    finally:
        os.environ["HUB_DATA"] = hub


async def _check_monitor(port):
    text = TV_LINE
    monitor_url = f"ws://127.0.0.1:{port}/ws?screen=caregiver&monitor=1"
    plain_url = f"ws://127.0.0.1:{port}/ws?screen=caregiver"
    async with websockets.connect(monitor_url) as monitor, websockets.connect(plain_url) as plain:
        health_m = await _recv(monitor)
        health_p = await _recv(plain)
        if health_m.get("event") != "health" or health_p.get("event") != "health":
            raise AssertionError((health_m, health_p))
        status, _body = _request(
            port,
            "/listen",
            json.dumps({"mode": "typed", "text": text}).encode("utf-8"),
            "application/json",
        )
        if status != 202:
            raise AssertionError(status)
        heard = await _recv(monitor)
        decided = await _recv(monitor)
        if heard.get("event") != "heard" or heard.get("transcript") != text:
            raise AssertionError(heard)
        if (
            decided.get("event") != "decided"
            or decided.get("action") != "silent"
            or decided.get("ignored") != "tv"
            or decided.get("transcript") != text
        ):
            raise AssertionError(decided)
        await _quiet(plain)
        await _quiet(monitor)


async def _run():
    port = _free_port()
    config = uvicorn.Config(server.app, host="127.0.0.1", port=port, log_level="error")
    runner = uvicorn.Server(config)
    thread = threading.Thread(target=runner.run, daemon=True)
    thread.start()
    passed = 0
    total = 0
    try:
        await _wait_up(port)
        checks = (
            ("gallery", lambda: _check_gallery(port)),
            ("unknown person", lambda: _check_visitor(port)),
            ("enroll troy", lambda: _check_enroll(port)),
            ("face frame", lambda: _check_frame(port)),
            ("empty photo", _check_photo),
            ("monitor", lambda: _check_monitor(port)),
        )
        for name, check in checks:
            total += 1
            try:
                result = check()
                if asyncio.iscoroutine(result):
                    await result
                passed += 1
                print(f"{name}: PASS")
            except Exception as exc:
                print(f"{name}: FAIL {exc}")
    finally:
        runner.should_exit = True
        thread.join(timeout=5)
    return passed == total and total == 6


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(_run()) else 1)
