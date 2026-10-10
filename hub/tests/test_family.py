"""POST /family keeps a member and their photo across a hub restart.

Stub mode. No camera and no model. Run from the repo root:

    python3 hub/tests/test_family.py
"""

import asyncio
import json
import os
import shutil
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
TMP = Path(tempfile.mkdtemp(prefix="sino-family-"))
os.environ["HUB_DATA"] = str(TMP / "data")
os.environ["SINO_SEED"] = str(TMP / "data" / "questions.json")
os.environ["SINO_MODEL"] = "stub"
os.environ["SINO_LOG"] = str(TMP / "decisions.jsonl")
os.environ["OFFLINE_PROBE"] = "http://127.0.0.1:9"
os.environ.pop("CERT", None)
os.environ.pop("KEY", None)
sys.path.insert(0, str(ROOT / "brain"))

import uvicorn  # noqa: E402
import websockets  # noqa: E402

import server  # noqa: E402

SEED_BEFORE = (ROOT / "brain" / "seed.json").read_bytes()
PHOTO = b"\xff\xd8\xff\xd9"


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
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method)
    if content_type:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
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
            if _request(port, "/health")[0] == 200:
                return
        except OSError:
            await asyncio.sleep(0.05)
    raise RuntimeError("server did not start")


async def _recv_event(ws, name, timeout=5):
    deadline = time.monotonic() + timeout
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), deadline - time.monotonic()))
        if msg.get("event") == name:
            return msg


def _check(cond, detail):
    if not cond:
        raise AssertionError(detail)


async def _run():
    port, runner, thread = _start()
    photo_path = ""
    try:
        await _wait_up(port)
        status, empty = _json(port, "/family")
        _check(status == 200 and empty.get("members") == [], empty)

        async with websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=caregiver") as other:
            await _recv_event(other, "health")
            status, member = _json(
                port,
                "/family",
                *_multipart(
                    [("name", "Ate Tricia"), ("color", "green")],
                    [("photo", "tricia.jpg", PHOTO)],
                ),
            )
            event = await _recv_event(other, "family_added")
        _check(status == 200 and member.get("name") == "Ate Tricia", member)
        _check(member.get("id") == "ate-tricia" and member.get("color") == "green", member)
        photo_path = member.get("photo") or ""
        _check(photo_path == "/media/family-ate-tricia-photo.jpg", member)
        _check(event.get("id") == "ate-tricia" and event.get("photo") == photo_path, event)
        _check(_request(port, photo_path) == (200, PHOTO), "photo bytes")
        status, listed = _json(port, "/family")
        _check(status == 200 and listed["members"] == [member], listed)
        _check((ROOT / "brain" / "seed.json").read_bytes() == SEED_BEFORE, "seed changed")
    finally:
        _stop(runner, thread)

    port, runner, thread = _start()
    try:
        await _wait_up(port)
        status, listed = _json(port, "/family")
        _check(status == 200 and len(listed.get("members") or []) == 1, listed)
        member = listed["members"][0]
        _check(member.get("name") == "Ate Tricia" and member.get("photo") == photo_path, member)
        _check(_request(port, photo_path) == (200, PHOTO), "photo lost on restart")
        _check((ROOT / "brain" / "seed.json").read_bytes() == SEED_BEFORE, "seed changed after restart")
        print("family: PASS")
        return True
    finally:
        _stop(runner, thread)
        shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    try:
        ok = asyncio.run(_run())
    except Exception as exc:
        print(f"family: FAIL {type(exc).__name__} {exc}")
        ok = False
    raise SystemExit(0 if ok else 1)
