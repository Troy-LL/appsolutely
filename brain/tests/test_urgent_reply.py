"""Urgent, then a caregiver reply, then Lola's event, then the chime stops.

Stub mode: decide() does not call the model. No sound is made: chime._start is a fake.
Run from the repo root:

    SINO_MODEL=stub python3 brain/tests/test_urgent_reply.py
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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TMP = Path(tempfile.mkdtemp(prefix="sino-urgent-reply-"))
os.environ["HUB_DATA"] = str(TMP / "data")
os.environ["SINO_SEED"] = str(TMP / "data" / "questions.json")
os.environ["SINO_MODEL"] = "stub"
os.environ["SINO_LOG"] = str(TMP / "decisions.jsonl")
os.environ["OFFLINE_PROBE"] = "http://127.0.0.1:9"
os.environ["CLIP_MEDIA"] = str(TMP / "clips")
for name in ("CERT", "KEY", "CHIME"):
    os.environ.pop(name, None)
sys.path.insert(0, str(ROOT / "brain"))

import uvicorn  # noqa: E402
import websockets  # noqa: E402

import server  # noqa: E402
import chime  # noqa: E402

PLAYED = []
ALARMS = []
REPLY_KEYS = {"event", "text", "speaker", "reply_audio"}


class FakeAlarm:
    def __init__(self):
        self.playing = True
        self.stopped = False

    def poll(self):
        return None if self.playing else 0

    def terminate(self):
        self.stopped = True
        self.playing = False


def fake_start(cmd):
    PLAYED.append(cmd)
    ALARMS.append(FakeAlarm())
    return ALARMS[-1]


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _post_json(port, path, payload):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
    )
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=3) as res:
            return res.status, res.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _post_audio(port, text, speaker, filename, data):
    boundary = "sino-urgent-reply"
    body = b"".join([
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="text"\r\n\r\n',
        text.encode(),
        b"\r\n",
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="speaker"\r\n\r\n',
        speaker.encode(),
        b"\r\n",
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="reply_audio"; filename="{filename}"\r\n'.encode(),
        b"Content-Type: audio/wav\r\n\r\n",
        data,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ])
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/urgent-reply",
        method="POST",
        data=body,
    )
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req, timeout=3) as res:
        return res.status, json.loads(res.read().decode("utf-8"))


async def _wait_up(port):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.3):
                return
        except (OSError, urllib.error.URLError):
            await asyncio.sleep(0.05)
    raise RuntimeError("server did not start")


async def _recv_event(ws, name, timeout=8):
    deadline = time.monotonic() + timeout
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), deadline - time.monotonic()))
        if msg.get("event") == name:
            return msg


async def _drain(ws, seconds):
    seen, deadline = [], time.monotonic() + seconds
    while True:
        try:
            msg = json.loads(await asyncio.wait_for(ws.recv(), deadline - time.monotonic()))
        except asyncio.TimeoutError:
            return seen
        seen.append(msg.get("event"))


def _check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} {detail}")


def _reply(msg, text, speaker, audio=""):
    _check("reply", set(msg) == REPLY_KEYS, sorted(msg))
    _check("reply", msg["event"] == "urgent_reply", msg)
    _check("reply", msg["text"] == text, msg)
    _check("reply", msg["speaker"] == speaker, msg)
    _check("reply", msg["reply_audio"] == audio, msg)
    _check("reply", "red" not in json.dumps(msg), msg)


async def _run():
    chime._start = fake_start
    chime.enable_chime()
    port = _free_port()
    runner = uvicorn.Server(uvicorn.Config(server.app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=runner.run, daemon=True)
    thread.start()
    passed = 0
    try:
        await _wait_up(port)
        base = f"ws://127.0.0.1:{port}/ws?screen="
        async with websockets.connect(base + "lola") as lola, \
                websockets.connect(base + "caregiver") as care, \
                websockets.connect(base + "backstage") as back:
            for ws in (lola, care, back):
                await _recv_event(ws, "health", 3)

            await lola.send(json.dumps({
                "event": "urgent_reply", "text": "Papunta na ako", "speaker": "Joy", "reply_audio": "",
            }))
            early = await _drain(lola, 0.3)
            _check("early", "urgent_reply" not in early, early)
            _check("early", PLAYED == [], PLAYED)
            passed += 1
            print("reply before an urgent alert: ignored, chime stays quiet")

            _check("urgent", _post_json(port, "/listen", {"mode": "typed", "text": "Hindi ako makahinga."})[0] == 202)
            alert = await _recv_event(care, "alert")
            _check("urgent", alert == {"event": "alert", "transcript": "Hindi ako makahinga."}, alert)
            decided = await _recv_event(lola, "decided")
            _check("urgent", decided["action"] == "urgent", decided.get("action"))
            lola_rest = await _drain(lola, 0.4)
            _check("urgent", "alert" not in lola_rest and "urgent_reply" not in lola_rest, lola_rest)
            _check("urgent", len(PLAYED) == 1 and ALARMS[-1].playing and not ALARMS[-1].stopped, len(PLAYED))
            await _recv_event(back, "decided")
            passed += 1
            print("urgent: caregiver alert, lola gets no alert, chime starts")

            await lola.send(json.dumps({
                "event": "urgent_reply", "text": "Papunta na ako", "speaker": "Joy", "reply_audio": "",
            }))
            still = await _drain(lola, 0.3)
            _check("not-caregiver", "urgent_reply" not in still, still)
            _check("not-caregiver", ALARMS[-1].playing, "chime stopped too soon")
            passed += 1
            print("lola socket cannot answer an urgent alert")

            await care.send(json.dumps({
                "event": "urgent_reply", "text": "Papunta na ako", "speaker": "Joy", "reply_audio": "",
            }))
            for ws in (lola, care, back):
                _reply(await _recv_event(ws, "urgent_reply"), "Papunta na ako", "Joy")
            _check("chime", ALARMS[-1].stopped and not ALARMS[-1].playing, "chime still playing")
            log = Path(os.environ["SINO_LOG"]).read_text(encoding="utf-8")
            _check("log", '"urgent_reply"' in log and "Papunta na ako" not in log, "reply text was logged")
            passed += 1
            print("caregiver reply: every screen gets it, chime stops")

            async with websockets.connect(base + "lola") as late:
                health = await _recv_event(late, "health", 3)
                _check("replay", health["event"] == "health", health)
                _reply(await _recv_event(late, "urgent_reply"), "Papunta na ako", "Joy")
            passed += 1
            print("lola reconnect receives the reply after health")

            _check("again", _post_json(port, "/listen", {"mode": "typed", "text": "tulong naman"})[0] == 202)
            await _recv_event(care, "alert")
            _check("again", len(PLAYED) == 2 and ALARMS[-1].playing, len(PLAYED))
            async with websockets.connect(base + "lola") as fresh:
                await _recv_event(fresh, "health", 3)
                fresh_seen = await _drain(fresh, 0.4)
                _check("again", "urgent_reply" not in fresh_seen, fresh_seen)
            passed += 1
            print("next urgent starts the chime and does not replay the old reply")

            status, body = _post_audio(port, "Papunta na ako", "Joy", "reply.wav", b"RIFFstub")
            _check("voice", status == 200, status)
            _check("voice", body["reply_audio"].startswith("/media/urgent-reply-") and body["reply_audio"].endswith(".wav"), body)
            _check("voice", (TMP / "data" / "media" / body["reply_audio"].rsplit("/", 1)[-1]).is_file())
            for ws in (lola, care, back):
                _reply(await _recv_event(ws, "urgent_reply"), "Papunta na ako", "Joy", body["reply_audio"])
            _check("voice", ALARMS[-1].stopped, "chime still playing after the voice reply")
            passed += 1
            print("recorded voice: lola event carries /media path, chime stops")
    finally:
        runner.should_exit = True
        thread.join(timeout=5)
        shutil.rmtree(TMP, ignore_errors=True)
    print(f"PASS {passed}/7")
    return passed == 7


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(_run()) else 1)
