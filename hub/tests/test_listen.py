"""Listen now (D4): peak level, junk filter, Whisper, and POST /listen end to end.

No real microphone is used: record_clip is replaced by a copy of a test WAV. The Whisper
checks need whisper-server on 127.0.0.1:8080 and are skipped without it. Transcripts are
never printed, only their length.

Run from the repo root:

    ~/sino/hub-venv/bin/python hub/tests/test_listen.py
"""

import array
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
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TMP = Path(tempfile.mkdtemp(prefix="sino-listen-test-"))
os.environ["HUB_DATA"] = str(TMP / "data")
os.environ["SINO_SEED"] = str(TMP / "data" / "questions.json")
os.environ["SINO_MODEL"] = "stub"
os.environ["SINO_LOG"] = str(TMP / "decisions.jsonl")
os.environ["OFFLINE_PROBE"] = "http://127.0.0.1:9"
for name in ("CERT", "KEY", "QUIET_DBFS", "WHISPER_HINT", "LISTEN_SECONDS", "MIC_DEVICE"):
    os.environ.pop(name, None)
sys.path.insert(0, str(ROOT / "brain"))

import uvicorn  # noqa: E402
import websockets  # noqa: E402

import server  # noqa: E402
import listen  # noqa: E402  (hub/listen.py, put on sys.path by server)

C03 = ROOT / "brain" / "tests" / "audio" / "lola" / "c03.wav"
ZEROS = TMP / "zeros.wav"
HUSH = TMP / "hush.wav"
LISTING = """[AVFoundation indev @ 0x1] AVFoundation video devices:
[AVFoundation indev @ 0x1] [0] FaceTime HD Camera
[AVFoundation indev @ 0x1] AVFoundation audio devices:
[AVFoundation indev @ 0x1] [0] MacBook Air Microphone
"""


def _write_wav(path, amplitude, seconds=1.0):
    # 16 kHz mono 16-bit. amplitude 0 is digital silence; 3 is a faint hiss (about -81 dBFS).
    samples = array.array("h", [amplitude if i % 2 else -amplitude for i in range(int(16000 * seconds))])
    if sys.byteorder == "big":
        samples.byteswap()
    with wave.open(str(path), "wb") as clip:
        clip.setnchannels(1)
        clip.setsampwidth(2)
        clip.setframerate(16000)
        clip.writeframes(samples.tobytes())


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _post_listen(port):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/listen", method="POST",
                                 data=json.dumps({"mode": "listen_now"}).encode("utf-8"))
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=3) as res:
        return res.status, res.read()


def _health(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as res:
        return json.loads(res.read())


async def _wait_up(port):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.3):
                return
        except (OSError, urllib.error.URLError):
            await asyncio.sleep(0.05)
    raise RuntimeError("server did not start")


async def _recv_event(ws, name, timeout=15):
    # Skip other events (health, decided) until the one we want arrives.
    deadline = time.monotonic() + timeout
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), deadline - time.monotonic()))
        if msg.get("event") == name:
            return msg


async def _count_events(ws, names, seconds):
    # How many of these events arrive in the next `seconds` (health updates are ignored).
    found, deadline = 0, time.monotonic() + seconds
    while True:
        try:
            msg = json.loads(await asyncio.wait_for(ws.recv(), deadline - time.monotonic()))
        except asyncio.TimeoutError:
            return found
        found += msg.get("event") in names


def _passed(done, name):
    done.append(name)
    print(f"{name}: PASS")


def _check(name, cond, detail=""):
    # detail never holds a transcript, only flags, reasons, and lengths.
    if not cond:
        raise AssertionError(f"{name} {detail}")


def _unit_cases(done, whisper_up):
    zeros, hush, c03 = listen.peak_dbfs(ZEROS), listen.peak_dbfs(HUSH), listen.peak_dbfs(C03)
    quiet = listen.quiet_dbfs()
    _check("peak", zeros == float("-inf") and hush < quiet < c03, (zeros, hush, quiet, c03))
    print(f"  peak dBFS: zeros {zeros}, hiss {hush:.1f}, c03.wav {c03:.1f} (threshold {quiet:g})")
    _passed(done, "peak_dbfs: silence below the threshold, c03.wav above")

    cases = (
        ("Nasaan si Nanay?", -100.0, "too quiet"),
        ("", -10.0, "likely no speech"),
        ("[BLANK_AUDIO]", -10.0, "likely no speech"),
        (" (silence) ♪ ", -10.0, "likely no speech"),
        ("Thank you for watching!", -10.0, "junk line"),
        ("Salamat sa panonood.", -10.0, "junk line"),
        ("Thanks for watching. Please subscribe!", -10.0, "junk line"),
        ("Nasaan si Nanay?", -10.0, ""),
        ("Masakit ang dibdib ko", -10.0, ""),
        ("Salamat sa panonood po", -10.0, ""),  # extra words: decide()'s TV rule handles it
    )
    for text, peak, want in cases:
        got = listen.junk_reason(text, peak)
        _check("junk", got == want, (text, peak, got, want))
    _passed(done, "junk_reason: too quiet / likely no speech / junk line / real speech")

    _check("device", listen.device_listed(LISTING, ":0"))
    _check("device", listen.device_listed(LISTING, ":MacBook Air Microphone"))
    _check("device", not listen.device_listed(LISTING, ":1"))
    _check("device", not listen.device_listed("", ":0"))
    _passed(done, "mic device found in the ffmpeg listing")

    if not whisper_up:
        print("transcribe: SKIPPED (whisper-server not reachable on 127.0.0.1:8080)")
        return
    text = listen.transcribe(C03)
    _check("transcribe", isinstance(text, str) and text, f"length {len(text)}")
    print(f"  transcript length: {len(text)} characters")
    _passed(done, "transcribe c03.wav returns text")


async def _e2e_cases(port, done, whisper_up):
    clips = []
    source = {"wav": C03, "delay": 0.0}

    def fake_record(seconds):
        # Stands in for the mic: copy a test WAV to a temp file, like record_clip would.
        time.sleep(source["delay"])
        fd, path = tempfile.mkstemp(prefix="sino-listen-", suffix=".wav", dir=TMP)
        os.close(fd)
        shutil.copyfile(source["wav"], path)
        clips.append(Path(path))
        return path

    def failing_record(seconds):
        raise listen.MicError("test: no microphone")

    listen.ENABLED = True
    listen.record_clip = fake_record
    async with websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=backstage") as ws:
        await _recv_event(ws, "health", 3)

        if whisper_up:
            _check("a", _post_listen(port) == (202, b""))
            heard = await _recv_event(ws, "heard")
            _check("a", heard["dropped"] is False and heard["drop_reason"] == "",
                   (heard["dropped"], heard["drop_reason"]))
            _check("a", isinstance(heard["transcript"], str) and heard["transcript"],
                   f"length {len(heard['transcript'])}")
            decided = await _recv_event(ws, "decided")
            _check("a", decided["transcript"] == heard["transcript"], decided["action"])
            _check("a", not clips[-1].exists(), "clip still on disk")
            print(f"  decided: {decided['action']} ({decided['source']})")
            _passed(done, "a listen now with c03.wav: heard + decided, clip deleted")
        else:
            print("a listen now with c03.wav: SKIPPED (whisper-server not reachable)")

        source["wav"] = HUSH
        _check("b", _post_listen(port) == (202, b""))
        heard = await _recv_event(ws, "heard")
        _check("b", heard == {"event": "heard", "transcript": "", "dropped": True,
                              "drop_reason": "too quiet"}, (heard["dropped"], heard["drop_reason"]))
        _check("b", await _count_events(ws, ("decided", "heard"), 1.0) == 0, "extra event")
        _check("b", not clips[-1].exists(), "clip still on disk")
        _check("b", _health(port)["mic"] is True)
        _passed(done, "b silent clip: dropped too quiet, no decided, clip deleted")

        source["delay"] = 0.5
        before = len(clips)
        _check("c", _post_listen(port) == (202, b"") and _post_listen(port) == (202, b""))
        _check("c", await _count_events(ws, ("heard",), 2.0) == 1, "not exactly one heard")
        _check("c", len(clips) == before + 1 and not clips[-1].exists(), len(clips) - before)
        _passed(done, "c second press during a capture is ignored")

        listen.record_clip = failing_record
        _check("d", _post_listen(port) == (202, b""))
        _check("d", await _count_events(ws, ("heard", "decided"), 1.0) == 0, "event on failure")
        _check("d", _health(port)["mic"] is False)
        _passed(done, "d recording failure: no event, health mic false")


async def _run():
    _write_wav(ZEROS, 0)
    _write_wav(HUSH, 3)
    whisper_up = server._reachable(server.WHISPER_URL, 0.5)
    port = _free_port()
    runner = uvicorn.Server(uvicorn.Config(server.app, host="127.0.0.1", port=port,
                                           log_level="error"))
    thread = threading.Thread(target=runner.run, daemon=True)
    thread.start()
    done = []
    total = 6 + (2 if whisper_up else 0)
    try:
        _unit_cases(done, whisper_up)
        await _wait_up(port)
        await _e2e_cases(port, done, whisper_up)
    except (AssertionError, asyncio.TimeoutError, ValueError, OSError) as exc:
        print(f"FAIL {type(exc).__name__} {exc}")
    finally:
        runner.should_exit = True
        thread.join(timeout=5)
        shutil.rmtree(TMP, ignore_errors=True)
    print(f"PASS {len(done)}/{total}")
    return len(done) == total


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(_run()) else 1)
