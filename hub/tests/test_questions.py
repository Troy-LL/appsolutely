"""POST /questions and /media on the hub server, in stub mode, with a temp data folder.

Run from the repo root:

    ~/sino/hub-venv/bin/python hub/tests/test_questions.py
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
TMP = Path(tempfile.mkdtemp(prefix="sino-hub-test-"))
os.environ["HUB_DATA"] = str(TMP / "data")
os.environ["SINO_SEED"] = str(TMP / "data" / "questions.json")
os.environ["SINO_MODEL"] = "stub"
os.environ["SINO_LOG"] = str(TMP / "decisions.jsonl")
os.environ["OFFLINE_PROBE"] = "http://127.0.0.1:9"
os.environ["CLIP_MEDIA"] = str(TMP / "clips")
os.environ.pop("CERT", None)
os.environ.pop("KEY", None)
sys.path.insert(0, str(ROOT / "brain"))

import uvicorn  # noqa: E402
import websockets  # noqa: E402

import server  # noqa: E402

SEED = ROOT / "brain" / "seed.json"
AUDIO_1 = b"fake-webm-audio-1"
AUDIO_2 = b"fake-m4a-audio-2"
PHOTO = b"fake-jpeg-photo"


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _multipart(fields, files):
    # fields: [(name, text)]; files: [(name, filename, bytes)]. Repeated names are allowed.
    boundary = uuid.uuid4().hex
    body = b""
    for name, value in fields:
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
                 f"{value}\r\n").encode("utf-8")
    for name, filename, data in files:
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
                 f'filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'
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
        with urllib.request.urlopen(req, timeout=3) as res:
            return res.status, res.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


def _post_question(port, fields, files):
    status, body = _request(port, "/questions", *_multipart(fields, files))
    return status, json.loads(body or b"null")


async def _wait_up(port):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.3):
                return
        except (OSError, urllib.error.URLError):
            await asyncio.sleep(0.05)
    raise RuntimeError("server did not start")


async def _recv_event(ws, name, timeout=3):
    # Skip other events (health, decided) until the one we want arrives.
    deadline = time.monotonic() + timeout
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), deadline - time.monotonic()))
        if msg.get("event") == name:
            return msg


async def _no_event(ws, name, timeout=0.5):
    # True when no `name` event arrives within `timeout` seconds.
    try:
        await _recv_event(ws, name, timeout)
    except asyncio.TimeoutError:
        return True
    return False


def _passed(done, name):
    done.append(name)
    print(f"{name}: PASS")


def _check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} {detail}")


async def _cases(port, done):
    seed_ids = [entry["id"] for entry in json.loads(SEED.read_text(encoding="utf-8"))]

    # (a) GET /questions returns the seed questions.
    status, body = _request(port, "/questions")
    _check("a", status == 200 and [e["id"] for e in json.loads(body)] == seed_ids, body[:200])
    _passed(done, "a GET /questions returns the seed")

    # (b) New question, no id: the hub makes one and stores both files.
    status, new = _post_question(
        port,
        [("question", "Nasaan yung aso?"), ("phrasings", "Asan yung aso?"),
         ("phrasings", "Nasaan ang aso?"), ("speaker", "Joy")],
        [("reply_audio", "clip.webm", AUDIO_1), ("photo", "dog.JPG", PHOTO)],
    )
    _check("b", status == 200, new)
    _check("b", new == {"id": "nasaan-yung-aso", "question": "Nasaan yung aso?",
                        "phrasings": ["Asan yung aso?", "Nasaan ang aso?"],
                        "reply_audio": "/media/nasaan-yung-aso-reply.webm",
                        "photo": "/media/nasaan-yung-aso-photo.jpg", "speaker": "Joy"}, new)
    _passed(done, "b POST new question")

    # (c) The stored files come back byte for byte; paths outside media/ do not.
    _check("c", _request(port, new["reply_audio"]) == (200, AUDIO_1))
    _check("c", _request(port, new["photo"]) == (200, PHOTO))
    for bad in ("/media/../questions.json", "/media/..%2fquestions.json"):
        _check("c", _request(port, bad)[0] == 404, bad)
    _passed(done, "c GET /media returns the same bytes")

    # (d) Same id, new audio: audio replaced, question, phrasings and photo kept.
    status, again = _post_question(
        port, [("id", "nasaan-yung-aso"), ("question", "Changed?")],
        [("reply_audio", "clip.webm", AUDIO_2)],
    )
    _check("d", status == 200 and again == new, again)
    _check("d", _request(port, new["reply_audio"]) == (200, AUDIO_2))
    _check("d", _request(port, new["photo"]) == (200, PHOTO))
    _passed(done, "d POST same id replaces the audio")

    # (e) A new phrasing typed at /listen is matched by decide() and plays the reply.
    async with websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=lola") as lola:
        await _recv_event(lola, "health")
        body = json.dumps({"mode": "typed", "text": "Asan yung aso?"}).encode("utf-8")
        _check("e", _request(port, "/listen", body, "application/json")[0] == 202)
        play = await _recv_event(lola, "play_reply")
    _check("e", play == {"event": "play_reply", "reply_id": "nasaan-yung-aso",
                         "reply_audio": new["reply_audio"], "photo": new["photo"],
                         "speaker": "Joy"}, play)
    _passed(done, "e /listen matches the new question")

    # (f) Bad input is refused with 400 and changes nothing.
    status, before = _request(port, "/questions")
    bad_posts = (
        ([("id", "Bad ID!"), ("question", "x")], [("reply_audio", "a.webm", b"x")]),
        ([("id", "brand-new")], [("reply_audio", "a.webm", b"x")]),
        ([("question", "Exe?")], [("reply_audio", "a.exe", b"x")]),
        ([("question", "Empty?")], [("reply_audio", "a.webm", b"")]),
        ([("question", "No audio?")], []),
    )
    for fields, files in bad_posts:
        status, err = _post_question(port, fields, files)
        _check("f", status == 400 and isinstance(err.get("error"), str), (fields, status, err))
    _check("f", _request(port, "/questions") == (200, before))
    _passed(done, "f bad input gives 400")

    # The same question again without an id gets the next free id; the seed is untouched.
    status, dup = _post_question(port, [("question", "Nasaan yung aso?")],
                                 [("reply_audio", "b.m4a", AUDIO_1)])
    _check("id", status == 200 and dup["id"] == "nasaan-yung-aso-2", dup)
    _check("id", [e["id"] for e in json.loads(SEED.read_text(encoding="utf-8"))] == seed_ids)
    _passed(done, "id collision adds -2, seed.json unchanged")

    # (g) DELETE removes a family-added question, refuses a built-in one, tells every screen.
    seed_bytes = SEED.read_bytes()
    status, listed = _request(port, "/questions")
    before_ids = [e["id"] for e in json.loads(listed)]
    status, err = _request(port, "/questions/nasaan-si-nanay", method="DELETE")
    err = json.loads(err or b"null")
    _check("g", status == 400 and err.get("error") == "built-in questions stay", (status, err))
    _check("g", [e["id"] for e in json.loads(_request(port, "/questions")[1])] == before_ids)
    _check("g", _request(port, "/media/nasaan-si-nanay-reply.m4a")[0] == 200)
    status, err = _request(port, "/questions/no-such-question", method="DELETE")
    err = json.loads(err or b"null")
    _check("g", status == 404 and isinstance(err.get("error"), str), (status, err))
    status, err = _request(port, "/questions/Bad_ID", method="DELETE")
    err = json.loads(err or b"null")
    _check("g", status == 400 and isinstance(err.get("error"), str), (status, err))
    async with websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=caregiver") as caregiver, \
            websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=lola") as lola:
        await _recv_event(caregiver, "health")
        await _recv_event(lola, "health")
        status, removed = _request(port, "/questions/nasaan-yung-aso", method="DELETE")
        removed = json.loads(removed or b"null")
        _check("g", status == 200 and removed.get("id") == "nasaan-yung-aso", removed)
        gone_c = await _recv_event(caregiver, "question_removed")
        gone_l = await _recv_event(lola, "question_removed")
    _check("g", gone_c == {"event": "question_removed", "id": "nasaan-yung-aso"}, gone_c)
    _check("g", gone_l == gone_c, gone_l)
    left = [e["id"] for e in json.loads(_request(port, "/questions")[1])]
    _check("g", "nasaan-yung-aso" not in left and "nasaan-yung-aso-2" in left and "nasaan-si-nanay" in left, left)
    _check("g", _request(port, "/media/nasaan-yung-aso-reply.webm")[0] == 404)
    _check("g", _request(port, "/media/nasaan-yung-aso-photo.jpg")[0] == 404)
    _check("g", SEED.read_bytes() == seed_bytes)
    _passed(done, "g DELETE removes an added question and keeps the seed")

    # (h) play_now=1 (a reply to a yellow card) plays on Lola's screen at once; without it, nothing.
    form = [("id", "nasaan-ang-salamin"), ("question", "Nasaan ang salamin?"),
            ("phrasings", "Nasaan ang salamin?"), ("speaker", "Donita")]
    async with websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=lola") as lola:
        await _recv_event(lola, "health")
        status, quiet = _post_question(port, form, [("reply_audio", "r.webm", AUDIO_1)])
        _check("h", status == 200, quiet)
        _check("h", await _no_event(lola, "play_reply"), "play_reply without play_now")
        status, saved = _post_question(port, form + [("play_now", "1")],
                                       [("reply_audio", "r.webm", AUDIO_2)])
        _check("h", status == 200 and saved == quiet, saved)
        play = await _recv_event(lola, "play_reply")
    _check("h", play == {"event": "play_reply", "reply_id": "nasaan-ang-salamin",
                         "reply_audio": "/media/nasaan-ang-salamin-reply.webm", "photo": "",
                         "speaker": "Donita"}, play)
    _check("h", _request(port, play["reply_audio"]) == (200, AUDIO_2))
    _passed(done, "h play_now=1 plays the reply on Lola's screen; without it, silent")


async def _run():
    port = _free_port()
    runner = uvicorn.Server(uvicorn.Config(server.app, host="127.0.0.1", port=port,
                                           log_level="error"))
    thread = threading.Thread(target=runner.run, daemon=True)
    thread.start()
    done = []
    try:
        await _wait_up(port)
        await _cases(port, done)
    except (AssertionError, asyncio.TimeoutError, ValueError) as exc:
        print(f"FAIL {type(exc).__name__} {exc}")
    finally:
        runner.should_exit = True
        thread.join(timeout=5)
        shutil.rmtree(TMP, ignore_errors=True)
    print(f"PASS {len(done)}/9")
    return len(done) == 9


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(_run()) else 1)
