"""Hub writes survive a restart, and a client that connects later sees them.

Stub mode. No camera and no model. Run from the repo root:

    SINO_MODEL=stub python3 brain/tests/test_persist.py
"""

import asyncio
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

ROOT = Path(__file__).resolve().parent.parent.parent
TMP = Path(tempfile.mkdtemp(prefix="sino-persist-"))
os.environ["HUB_DATA"] = str(TMP / "data")
os.environ["SINO_SEED"] = str(TMP / "data" / "questions.json")
os.environ["SINO_MODEL"] = "stub"
os.environ["SINO_LOG"] = str(TMP / "decisions.jsonl")
os.environ["FACE_GALLERY"] = str(TMP / "data" / "faces")
os.environ["OFFLINE_PROBE"] = "http://127.0.0.1:9"
os.environ["HUB_URL"] = "http://127.0.0.1:9"
os.environ.pop("CERT", None)
os.environ.pop("KEY", None)
sys.path.insert(0, str(ROOT / "brain"))

import uvicorn  # noqa: E402
import websockets  # noqa: E402

import server  # noqa: E402
import questions  # noqa: E402

TINY_JPEG = b"\xff\xd8\xff\xd9"
SEED_BEFORE = (ROOT / "brain" / "seed.json").read_bytes()


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
    for name, filename, data, kind in files:
        body += (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
            f'filename="{filename}"\r\nContent-Type: {kind}\r\n\r\n'
        ).encode("utf-8") + data + b"\r\n"
    body += f"--{boundary}--\r\n".encode("utf-8")
    return body, f"multipart/form-data; boundary={boundary}"


def _request(port, path, data=None, content_type=None, method=None):
    if method is None:
        method = "POST" if data is not None else "GET"
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method)
    if content_type:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=8) as res:
            return res.status, res.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


def _json(port, path, data=None, content_type=None, method=None):
    status, body = _request(port, path, data, content_type, method)
    return status, json.loads(body.decode("utf-8") or "null")


def _start():
    port = _free_port()
    runner = uvicorn.Server(uvicorn.Config(server.app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=runner.run, daemon=True)
    thread.start()
    return port, runner, thread


def _stop(runner, thread):
    runner.should_exit = True
    thread.join(timeout=5)


async def _wait_up(port):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            status, _body = _request(port, "/health")
            if status == 200:
                return
        except OSError:
            await asyncio.sleep(0.05)
    raise RuntimeError("server did not start")


def _fake_enroll(person, blobs, _replace):
    folder = Path(os.environ["FACE_GALLERY"]) / person
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "1.jpg").write_bytes(blobs[0])
    return {"person": person, "engine": "ok", "frames": [{"ok": True}], "count": 1}, blobs[0], True


def _sino_photo(port):
    status, body = _json(port, "/questions")
    if status != 200 or not isinstance(body, list):
        raise AssertionError((status, body))
    sino = next(entry for entry in body if entry.get("id") == "sino-ka")
    return sino["by_person"]["troy"]["photo"]


async def _recv_event(ws, name, timeout=5):
    deadline = time.monotonic() + timeout
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), deadline - time.monotonic()))
        if msg.get("event") == name:
            return msg


async def _run():
    real_enroll = server.enroll_request
    server.enroll_request = _fake_enroll
    port, runner, thread = _start()
    try:
        await _wait_up(port)
        status, enrolled = _json(
            port,
            "/face/enroll/troy",
            *_multipart([], [("frames", "a.jpg", TINY_JPEG, "image/jpeg")]),
        )
        if status != 200 or enrolled.get("photo") != "/media/sino-ka-troy-photo.jpg":
            raise AssertionError((status, enrolled))
        if _sino_photo(port) != "/media/sino-ka-troy-photo.jpg":
            raise AssertionError("photo missing before restart")
        if _request(port, "/media/sino-ka-troy-photo.jpg") != (200, TINY_JPEG):
            raise AssertionError("media missing before restart")
        status, gallery = _json(port, "/face/gallery")
        if status != 200 or gallery.get("people", {}).get("troy") != 1:
            raise AssertionError(gallery)

        status, saved = _json(
            port,
            "/safety-words",
            json.dumps({"word": "Hilo"}).encode("utf-8"),
            "application/json",
        )
        if status != 200 or saved.get("word") != "hilo":
            raise AssertionError((status, saved))

        status, question = _json(
            port,
            "/questions",
            *_multipart(
                [
                    ("id", "nasaan-yung-aso"),
                    ("question", "Nasaan yung aso?"),
                    ("speaker", "Joy"),
                    ("phrasings", "Nasaan yung aso?"),
                ],
                [("reply_audio", "clip.webm", b"fake-webm", "audio/webm")],
            ),
        )
        if status != 200 or question.get("id") != "nasaan-yung-aso":
            raise AssertionError((status, question))
        questions.ensure_working_copy()
        listed = json.loads(questions.questions_path().read_text(encoding="utf-8"))
        if not any(entry.get("id") == "nasaan-yung-aso" for entry in listed):
            raise AssertionError("startup fill removed the question")
        if (ROOT / "brain" / "seed.json").read_bytes() != SEED_BEFORE:
            raise AssertionError("seed changed")

        async with websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=caregiver") as care:
            await _recv_event(care, "health")
            await care.send(json.dumps({"event": "meal_logged"}))
            await asyncio.sleep(0.2)

        async with websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=caregiver") as care:
            await _recv_event(care, "health")
            heard = await _recv_event(care, "log")
            if not any(row.get("event") == "meal_logged" for row in heard.get("entries", [])):
                raise AssertionError(heard)
            if _json(port, "/listen", json.dumps({"mode": "typed", "text": "Tulong"}).encode("utf-8"), "application/json")[0] != 202:
                raise AssertionError("listen")
            alert = await _recv_event(care, "alert")
            if alert.get("transcript") != "Tulong":
                raise AssertionError(alert)
            await care.send(json.dumps({
                "event": "urgent_reply",
                "text": "Papunta na ako",
                "speaker": "Joy",
                "reply_audio": "",
            }))
            reply = await _recv_event(care, "urgent_reply")
            if reply.get("text") != "Papunta na ako":
                raise AssertionError(reply)
    finally:
        server.enroll_request = real_enroll
        _stop(runner, thread)

    port, runner, thread = _start()
    try:
        await _wait_up(port)
        if _sino_photo(port) != "/media/sino-ka-troy-photo.jpg":
            raise AssertionError("photo lost on restart")
        if _request(port, "/media/sino-ka-troy-photo.jpg") != (200, TINY_JPEG):
            raise AssertionError("media lost on restart")
        status, gallery = _json(port, "/face/gallery")
        if gallery.get("people", {}).get("troy") != 1:
            raise AssertionError(gallery)
        if not (Path(os.environ["FACE_GALLERY"]) / "troy" / "1.jpg").is_file():
            raise AssertionError("gallery file lost")
        status, words = _json(port, "/safety-words")
        if "hilo" not in words.get("custom", []):
            raise AssertionError(words)
        status, listed = _json(port, "/questions")
        if not any(entry.get("id") == "nasaan-yung-aso" for entry in listed):
            raise AssertionError("question lost on restart")
        status, log = _json(port, "/log")
        if not any(row.get("event") == "meal_logged" for row in log.get("entries", [])):
            raise AssertionError(log)
        async with websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=caregiver") as care:
            await _recv_event(care, "health")
            snap = await _recv_event(care, "log")
            if not any(row.get("event") == "meal_logged" for row in snap.get("entries", [])):
                raise AssertionError(snap)
        async with websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=lola") as lola:
            await _recv_event(lola, "health")
            replay = await _recv_event(lola, "urgent_reply")
            if replay.get("text") != "Papunta na ako" or replay.get("speaker") != "Joy":
                raise AssertionError(replay)
        if (ROOT / "brain" / "seed.json").read_bytes() != SEED_BEFORE:
            raise AssertionError("seed changed")
        print("persist: PASS")
        return True
    finally:
        _stop(runner, thread)


if __name__ == "__main__":
    try:
        ok = asyncio.run(_run())
    except Exception as exc:
        print(f"persist: FAIL {exc}")
        ok = False
    raise SystemExit(0 if ok else 1)
