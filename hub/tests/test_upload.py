"""The iPad's mic (POST /listen/audio): upload checks, ffmpeg conversion, deaf windows,
newest wins, and the same heard/decided events as listen now.

No microphone and no sound (the chime is never enabled in tests). The Whisper checks send
c03.wav, a .m4a copy of it, and u07.wav to whisper-server on 127.0.0.1:8080 and are skipped
without it. Ollama is never asked (stub mode). Transcripts are never printed, only lengths.

Run from the repo root:

    ~/sino/hub-venv/bin/python hub/tests/test_upload.py
"""

import array
import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TMP = Path(tempfile.mkdtemp(prefix="sino-upload-test-"))
os.environ["HUB_DATA"] = str(TMP / "data")
os.environ["SINO_SEED"] = str(TMP / "data" / "questions.json")
os.environ["SINO_MODEL"] = "stub"
os.environ["SINO_LOG"] = str(TMP / "decisions.jsonl")
os.environ["OFFLINE_PROBE"] = "http://127.0.0.1:9"
os.environ["HUB_URL"] = "http://127.0.0.1:9"  # stub mode: the health light never asks Ollama
for name in ("CERT", "KEY", "CHIME", "QUIET_DBFS", "WHISPER_HINT", "ALWAYS_LISTEN",
             "REPLY_DEAF_SECONDS", "CHIME_DEAF_SECONDS"):
    os.environ.pop(name, None)
sys.path.insert(0, str(ROOT / "brain"))

import uvicorn  # noqa: E402
import websockets  # noqa: E402

import server  # noqa: E402
import always  # noqa: E402  (hub/ modules, put on sys.path by server)
import listen  # noqa: E402
import upload  # noqa: E402

# Every temp file the hub makes in this process lands here, so "nothing left" is easy to check.
SPOOL = TMP / "spool"
SPOOL.mkdir()
tempfile.tempdir = str(SPOOL)

LOLA = ROOT / "brain" / "tests" / "audio" / "lola"
C03, U07 = LOLA / "c03.wav", LOLA / "u07.wav"  # "Nasaan si Nanay?" (comfort), "Tulong naman"


def _wav_bytes(seconds, amplitude=0):
    # 16 kHz mono 16-bit. amplitude 0 is digital silence.
    path = TMP / f"gen-{uuid.uuid4().hex}.wav"
    samples = array.array("h", [amplitude if i % 2 else -amplitude
                                for i in range(int(16000 * seconds))])
    if sys.byteorder == "big":
        samples.byteswap()
    with wave.open(str(path), "wb") as clip:
        clip.setnchannels(1)
        clip.setsampwidth(2)
        clip.setframerate(16000)
        clip.writeframes(samples.tobytes())
    data = path.read_bytes()
    path.unlink()
    return data


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _multipart(fields, files):
    # fields: [(name, text)]; files: [(name, filename, bytes)].
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


def _post(port, body, content_type):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/listen/audio", data=body,
                                 method="POST")
    req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, res.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


def _upload(port, filename, data, source="ipad"):
    fields = [("source", source)] if source is not None else []
    return _post(port, *_multipart(fields, [("audio", filename, data)]))


def _typed(port, text):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/listen", method="POST",
                                 data=json.dumps({"mode": "typed", "text": text}).encode("utf-8"))
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=3) as res:
        return res.status


async def _wait_up(port):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.3):
                return
        except (OSError, urllib.error.URLError):
            await asyncio.sleep(0.05)
    raise RuntimeError("server did not start")


async def _recv_event(ws, name, timeout=20):
    # Skip other events (health, face_seen) until the one we want arrives.
    deadline = time.monotonic() + timeout
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), deadline - time.monotonic()))
        if msg.get("event") == name:
            return msg


async def _count_events(ws, names, seconds):
    found, deadline = 0, time.monotonic() + seconds
    while True:
        try:
            msg = json.loads(await asyncio.wait_for(ws.recv(), deadline - time.monotonic()))
        except asyncio.TimeoutError:
            return found
        found += msg.get("event") in names


async def _wait_deaf(timeout=2.0):
    # publish() sends `decided` before it opens the deaf window, so wait for the window.
    deadline = time.monotonic() + timeout
    while always._deaf_until == 0.0 and time.monotonic() < deadline:
        await asyncio.sleep(0.01)
    return always._deaf_until > time.monotonic()


def _reset_deaf():
    always._deaf_from = always._deaf_until = 0.0


def _left():
    return [p.name for p in SPOOL.iterdir()]


def _passed(done, name):
    done.append(name)
    print(f"{name}: PASS")


def _check(name, cond, detail=""):
    # detail never holds a transcript, only flags, reasons, codes, and lengths.
    if not cond:
        raise AssertionError(f"{name} {detail}")


async def _bad_cases(port, ws, done):
    c03 = C03.read_bytes()
    cases = (
        ("no audio part", _multipart([("source", "ipad")], []), "audio is required"),
        ("audio as text", _multipart([("audio", "hello")], []), "audio is required"),
        ("not multipart", (b'{"audio": "x"}', "application/json"), "audio is required"),
        ("empty file", _multipart([], [("audio", "clip.wav", b"")]), "audio is empty"),
        (".exe name", _multipart([], [("audio", "clip.exe", c03)]),
         "audio must be .wav .m4a .mp4 .webm .ogg or .aac"),
        ("over 2 MB", _multipart([], [("audio", "big.wav", c03 + bytes(2 * 1024 * 1024))]),
         "audio is over 2 MB"),
        ("not audio", _multipart([], [("audio", "clip.wav", b"not a wav file at all")]),
         "audio could not be read"),
    )
    for name, (body, content_type), want in cases:
        status, raw = _post(port, body, content_type)
        _check("bad", (status, json.loads(raw or b"null")) == (400, {"error": want}),
               (name, status, raw[:80]))
        print(f"  {name}: 400 {want}")
    _check("bad", await _count_events(ws, ("heard", "decided"), 1.0) == 0, "event on bad input")
    _check("bad", _left() == [], _left())
    _passed(done, "bad input: 400 {error}, no event, no temp file")


async def _silent_case(port, ws, done):
    listen.MIC_OK = True  # an iPad clip must not touch the hub mic's health light
    _check("silent", _upload(port, "clip.wav", _wav_bytes(1.0), source=None) == (202, b""))
    heard = await _recv_event(ws, "heard")
    _check("silent", (heard["dropped"], heard["drop_reason"], heard["transcript"])
           == (True, "too quiet", ""), (heard["dropped"], heard["drop_reason"]))
    _check("silent", await _count_events(ws, ("heard", "decided"), 1.0) == 0, "extra event")
    _check("silent", listen.MIC_OK is True, "hub mic light changed by an iPad clip")
    _check("silent", _left() == [], _left())
    _passed(done, "silent WAV: dropped too quiet, no decided, hub mic light untouched, no temp file")


async def _speech_case(port, ws, done, name, filename, data, want_action=None):
    _reset_deaf()
    _check(name, _upload(port, filename, data) == (202, b""))
    heard = await _recv_event(ws, "heard")
    _check(name, heard["dropped"] is False and heard["drop_reason"] == "",
           (heard["dropped"], heard["drop_reason"]))
    _check(name, isinstance(heard["transcript"], str) and heard["transcript"],
           f"length {len(heard['transcript'])}")
    decided = await _recv_event(ws, "decided")
    _check(name, decided["transcript"] == heard["transcript"], decided["action"])
    if want_action:
        _check(name, decided["action"] == want_action, decided["action"])
    print(f"  heard {len(heard['transcript'])} characters; decided: {decided['action']} "
          f"({decided['source']})")
    _check(name, await _count_events(ws, ("heard", "decided"), 1.0) == 0, "extra event")
    _check(name, _left() == [], _left())
    _reset_deaf()  # comfort and urgent opened a deaf window; the next case starts clean
    _passed(done, name)


async def _whisper_cases(port, ws, done):
    await _speech_case(port, ws, done, "c03.wav upload: heard + decided, no temp file",
                       "clip.wav", C03.read_bytes())
    m4a = TMP / "c03.m4a"
    subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", str(C03), "-c:a", "aac",
                    str(m4a)], check=True, capture_output=True)
    await _speech_case(port, ws, done, "c03.m4a upload: heard + decided, no temp file",
                       "clip.m4a", m4a.read_bytes())
    await _speech_case(port, ws, done, "u07.wav upload (Tulong naman): decided urgent",
                       "clip.wav", U07.read_bytes(), "urgent")


async def _deaf_cases(port, ws, done):
    silent = _wav_bytes(1.0)
    for text, window in (("Nasaan si Nanay?", "reply"), ("Tulong", "chime")):
        _reset_deaf()
        _check("deaf", _typed(port, text) == 202)
        decided = await _recv_event(ws, "decided")
        _check("deaf", await _wait_deaf(), f"no deaf window after {decided['action']}")
        _check("deaf", _upload(port, "clip.wav", silent) == (202, b""))
        _check("deaf", await _count_events(ws, ("heard", "decided"), 1.0) == 0,
               f"event inside the {window} window")
        _check("deaf", _left() == [], _left())
        print(f"  {decided['action']} -> upload inside the {window} window: no event")

    # A window that ended 0.5 s ago: a 2 s clip still holds some of it (dropped), 0.2 s does not.
    now = time.monotonic()
    always._deaf_from, always._deaf_until = now - 3, now - 0.5
    _check("deaf", _upload(port, "clip.wav", _wav_bytes(2.0)) == (202, b""))
    _check("deaf", await _count_events(ws, ("heard", "decided"), 1.0) == 0, "overlap kept")
    _check("deaf", _upload(port, "clip.wav", _wav_bytes(0.2)) == (202, b""))
    heard = await _recv_event(ws, "heard", 5)
    _check("deaf", heard["drop_reason"] == "too quiet", heard["drop_reason"])
    _check("deaf", _left() == [], _left())
    _reset_deaf()
    _passed(done, "deaf windows: uploads during a reply or chime, or overlapping one, give no event")


async def _newest_case(port, done):
    seen, release = [], threading.Event()

    async def fake_process(_hub, path, label="", hub_mic=True):
        # Stands in for Whisper: note the clip, stay "busy" until the test says so.
        with wave.open(path, "rb") as clip:
            seen.append((round(clip.getnframes() / 16000, 1), label, hub_mic))
        await asyncio.to_thread(release.wait, 10)
        Path(path).unlink(missing_ok=True)

    real = listen.process_clip
    listen.process_clip = fake_process
    try:
        _check("newest", _upload(port, "a.wav", _wav_bytes(0.5)) == (202, b""))
        deadline = time.monotonic() + 3
        while not seen and time.monotonic() < deadline:
            await asyncio.sleep(0.02)
        _check("newest", len(seen) == 1, "first clip never started")
        _check("newest", _upload(port, "b.wav", _wav_bytes(1.0)) == (202, b""))
        _check("newest", _upload(port, "c.wav", _wav_bytes(1.5)) == (202, b""))
        # Busy with a, c waiting; b was replaced by c and deleted.
        _check("newest", len(_left()) == 2, _left())
        release.set()
        deadline = time.monotonic() + 3
        while (len(seen) < 2 or _left()) and time.monotonic() < deadline:
            await asyncio.sleep(0.02)
        _check("newest", seen == [(0.5, "ipad clip", False), (1.5, "ipad clip", False)], seen)
        _check("newest", _left() == [], _left())
    finally:
        release.set()
        listen.process_clip = real
    _passed(done, "newest wins: one clip at a time, an older waiting clip is deleted")


async def _section(run, *args):
    # One group of checks. A failure prints its reason here; the other groups still run.
    try:
        await run(*args)
    except Exception as exc:
        print(f"FAIL {type(exc).__name__} {exc}")


async def _run():
    whisper_up = server._reachable(server.WHISPER_URL, 0.5)
    port = _free_port()
    runner = uvicorn.Server(uvicorn.Config(server.app, host="127.0.0.1", port=port,
                                           log_level="error"))
    thread = threading.Thread(target=runner.run, daemon=True)
    thread.start()
    done = []
    total = 4 + (3 if whisper_up else 0)
    try:
        await _wait_up(port)
        async with websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=backstage") as ws:
            await _recv_event(ws, "health", 3)
            await _section(_bad_cases, port, ws, done)
            await _section(_silent_case, port, ws, done)
            if whisper_up:
                await _section(_whisper_cases, port, ws, done)
            else:
                print("c03 / m4a / u07 uploads: SKIPPED (whisper-server not reachable)")
            await _section(_deaf_cases, port, ws, done)
        await _section(_newest_case, port, done)
    finally:
        runner.should_exit = True
        thread.join(timeout=5)
        _reset_deaf()
        left = _left()
        shutil.rmtree(TMP, ignore_errors=True)
    if left:
        print(f"FAIL temp files left after the server stopped: {left}")
    print(f"PASS {len(done)}/{total}")
    return len(done) == total and not left


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(_run()) else 1)
