"""Always-listening (D4): loudness gate, newest wins, deaf windows, and the app end to end.

No real microphone and no sound. The gate gets synthetic 30 ms frames. The ffmpeg capture is
replaced by a small Python process (a fake mic) that streams quiet noise and, once, noise +
c03.wav + noise. The end-to-end part uses whisper-server on 127.0.0.1:8080; with SKIP_WHISPER=1,
or when it is not reachable, a fake transcriber stands in and nothing is sent to it. Ollama is
never asked (stub mode, health probe on a closed port). Transcripts are never printed.

Run from the repo root:

    ~/sino/hub-venv/bin/python hub/tests/test_always.py
    SKIP_WHISPER=1 ~/sino/hub-venv/bin/python hub/tests/test_always.py
"""

import array
import asyncio
import contextlib
import io
import json
import os
import random
import shutil
import signal
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
TMP = Path(tempfile.mkdtemp(prefix="sino-always-test-"))
os.environ["HUB_DATA"] = str(TMP / "data")
os.environ["SINO_SEED"] = str(TMP / "data" / "questions.json")
os.environ["SINO_MODEL"] = "stub"
os.environ["SINO_LOG"] = str(TMP / "decisions.jsonl")
os.environ["OFFLINE_PROBE"] = "http://127.0.0.1:9"
os.environ["HUB_URL"] = "http://127.0.0.1:9"  # stub mode: the health light never asks Ollama
for name in ("CERT", "KEY", "CHIME", "QUIET_DBFS", "WHISPER_HINT", "MIC_DEVICE", "ALWAYS_LISTEN",
             "GATE_MARGIN_DB", "GATE_DBFS", "SILENCE_SECONDS", "MAX_CLIP_SECONDS",
             "REPLY_DEAF_SECONDS", "CHIME_DEAF_SECONDS"):
    os.environ.pop(name, None)
sys.path.insert(0, str(ROOT / "brain"))

import uvicorn  # noqa: E402
import websockets  # noqa: E402

import server  # noqa: E402
import always  # noqa: E402  (hub/always.py, put on sys.path by server)
import listen  # noqa: E402

C03 = ROOT / "brain" / "tests" / "audio" / "lola" / "c03.wav"
FRAME = always.FRAME_BYTES
WRITTEN = []  # every temp clip always.write_wav made, to check none is left on disk
_real_write_wav = always.write_wav
FAKE_SEEN = []  # lengths in seconds of the clips the fake transcriber got

E2E = "e2e fake mic stream -> heard + decided, exactly one clip, deleted"
CHECKS = (
    "gate: silence, quiet noise, and a 0.1 s click give no clip",
    "gate: noise + c03.wav + noise gives exactly one clip of about that length",
    "gate: a long loud sound is cut at MAX_CLIP_SECONDS",
    "gate: GATE_DBFS sets a fixed threshold",
    "newest wins: only the newest waiting clip is processed, older one deleted",
    "stopping the worker deletes the clip still waiting",
    "deaf windows (reply 12 s, chime 9 s) and listen now drop clips, no file kept",
    "ffmpeg stops or is missing: mic false, restarted, no crash",
    "mic flag: true while sound arrives, false after a second of exact zeros",
    "enable_always: on only with ALWAYS_LISTEN=1, prints one line",
    "default off: importing and running the app starts no capture",
    E2E,
    "server: play_reply and the urgent chime start the deaf windows",
    "server stop kills the mic process and leaves no clip file",
)

# The fake mic: streams 1 s of quiet noise per second; once the "go" file exists, it sends the
# speech stream once (noise + c03.wav + noise). Killed by the server when it stops.
FAKE_MIC = r"""
import os, sys, time
go, noise, speech, pidfile = sys.argv[1:5]
with open(pidfile, "w") as f:
    f.write(str(os.getpid()))
noise, speech = open(noise, "rb").read(), open(speech, "rb").read()
sent = False
while True:
    if not sent and os.path.exists(go):
        sys.stdout.buffer.write(speech)
        sent = True
    else:
        sys.stdout.buffer.write(noise)
    sys.stdout.buffer.flush()
    time.sleep(1.0)
"""
# Writes one file's bytes to stdout, then waits (stands in for ffmpeg that keeps running).
FAKE_ONCE = "import sys, time; sys.stdout.buffer.write(open(sys.argv[1], 'rb').read()); " \
            "sys.stdout.buffer.flush(); time.sleep(30)"


def _spy_write_wav(pcm):
    path = _real_write_wav(pcm)
    WRITTEN.append(Path(path))
    return path


def _fake_transcribe(path):
    # Stands in for whisper-server: notes the clip's length and returns a known question.
    with wave.open(str(path), "rb") as clip:
        FAKE_SEEN.append(clip.getnframes() / clip.getframerate())
    return "Nasaan si Nanay?"


def _pcm(samples):
    data = array.array("h", samples)
    if sys.byteorder == "big":
        data.byteswap()
    return data.tobytes()


def _noise(seconds, amplitude, seed=7):
    # Steady random noise. amplitude 57 is about -60 dBFS RMS (a quiet room), 8000 about -17.
    rng = random.Random(seed)
    return _pcm([rng.randint(-amplitude, amplitude) for _ in range(int(16000 * seconds))])


def _wav_pcm(path):
    with wave.open(str(path), "rb") as clip:
        return clip.readframes(clip.getnframes())


def _cut(pcm, gate=None):
    # Feed whole 30 ms frames to a gate; return the clips it cut.
    gate = gate or always.Gate()
    clips = []
    for i in range(0, len(pcm) - FRAME + 1, FRAME):
        clip = gate.feed(pcm[i:i + FRAME])
        if clip:
            clips.append(clip)
    return clips


def _secs(pcm):
    return len(pcm) / 32000


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _post(port, payload):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/listen", method="POST",
                                 data=json.dumps(payload).encode("utf-8"))
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
    # Skip other events (health, play_reply) until the one we want arrives.
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


def _passed(done, name):
    _check("unknown check name", name in CHECKS, name)
    done.append(name)
    print(f"{name}: PASS")


def _check(name, cond, detail=""):
    # detail never holds a transcript, only flags, reasons, and lengths.
    if not cond:
        raise AssertionError(f"{name} {detail}")


def _reset_deaf():
    always._deaf_from = always._deaf_until = 0.0


def _gate_cases(done):
    quiet = _noise(3, 57)
    print(f"  quiet noise: {always.frame_dbfs(quiet[:FRAME]):.1f} dBFS per frame")
    _check("silence", _cut(bytes(3 * 32000)) == [], "clip from digital silence")
    _check("noise", _cut(quiet) == [], "clip from quiet noise")
    click = _noise(1.5, 57) + _noise(0.1, 8000, 3) + _noise(2, 57, 5)
    _check("click", _cut(click) == [], "a 0.1 s click made a clip")
    _passed(done, "gate: silence, quiet noise, and a 0.1 s click give no clip")

    speech = _wav_pcm(C03)
    clips = _cut(_noise(1.5, 57) + speech + _noise(2, 57, 5))
    _check("speech", len(clips) == 1, f"{len(clips)} clips")
    most = _secs(speech) + always.PRE_ROLL_SECONDS + always.SILENCE_SECONDS + 0.1
    _check("speech", _secs(speech) <= _secs(clips[0]) <= most, _secs(clips[0]))
    print(f"  c03.wav {_secs(speech):.2f} s -> clip {_secs(clips[0]):.2f} s")
    _passed(done, "gate: noise + c03.wav + noise gives exactly one clip of about that length")

    gate = always.Gate()
    clips = _cut(_noise(1.5, 57) + _noise(12, 8000, 3) + _noise(2, 57, 5), gate)
    _check("max", clips and len(clips[0]) == gate.max_frames * FRAME, [_secs(c) for c in clips])
    print(f"  12 s loud noise -> first clip {_secs(clips[0]):.2f} s, {len(clips)} clip(s) in all")
    _passed(done, "gate: a long loud sound is cut at MAX_CLIP_SECONDS")

    stream = _noise(1.5, 57) + speech + _noise(2, 57, 5)
    os.environ["GATE_DBFS"] = "-5"  # c03.wav is never this loud (loudest frame about -11)
    try:
        _check("fixed", _cut(stream) == [], "clip above a fixed -5 dBFS")
        os.environ["GATE_DBFS"] = "-30"
        _check("fixed", len(_cut(stream)) == 1, "no clip above a fixed -30 dBFS")
    finally:
        os.environ.pop("GATE_DBFS", None)
    _passed(done, "gate: GATE_DBFS sets a fixed threshold")


async def _newest_wins(done):
    processed, finish = [], asyncio.Event()

    async def fake_process(_hub, path, _label):
        processed.append(path)
        await finish.wait()  # "still at Whisper" until the test says so
        Path(path).unlink(missing_ok=True)

    real = listen.process_clip
    listen.process_clip = fake_process
    always._ready = asyncio.Event()
    task = asyncio.create_task(always._process(None))
    leftover = []
    try:
        a, b, c = (always.write_wav(bytes(FRAME * 20)) for _ in range(3))
        always.offer(a)
        await asyncio.sleep(0.05)  # a is now being processed
        always.offer(b)
        always.offer(c)  # c is newer than the waiting b: b is deleted, no event
        _check("newest", not Path(b).exists(), "older waiting clip still on disk")
        finish.set()
        await asyncio.sleep(0.05)
        _check("newest", processed == [a, c], [Path(p).name for p in processed])
        _check("newest", not any(Path(p).exists() for p in (a, b, c)), "clip left on disk")
        _passed(done, "newest wins: only the newest waiting clip is processed, older one deleted")

        finish.clear()
        d, e = always.write_wav(bytes(FRAME)), always.write_wav(bytes(FRAME))
        leftover.append(d)
        always.offer(d)
        await asyncio.sleep(0.05)
        always.offer(e)
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        listen.process_clip = real
    _check("stop", not Path(e).exists() and always._waiting is None, "waiting clip kept on stop")
    for path in leftover:
        Path(path).unlink(missing_ok=True)  # the fake did not get to delete it
    _passed(done, "stopping the worker deletes the clip still waiting")


def _deaf_cases(done):
    pcm = bytes(FRAME * 30)
    always._ready = asyncio.Event()
    _reset_deaf()
    always.clip_done(pcm)  # no window: saved and queued
    _check("deaf", always._waiting is not None, "clip not queued outside a window")
    Path(always._waiting).unlink(missing_ok=True)
    always._waiting = None

    always.deafen_for_reply()
    t0 = always._deaf_from
    _check("deaf", always._deaf_until - t0 == 12, always._deaf_until - t0)
    _check("deaf", not always.deaf(t0 - 5, t0 - 1), "clip from before the reply dropped")
    _check("deaf", always.deaf(t0 - 3, t0 + 1), "clip with the start of the reply kept")
    _check("deaf", always.deaf(t0 + 11, t0 + 13), "clip starting in the window kept")
    _check("deaf", not always.deaf(t0 + 12.5, t0 + 14), "clip after the window dropped")
    always.clip_done(pcm)
    _check("deaf", always._waiting is None, "clip queued during the reply window")

    _reset_deaf()
    always.deafen_for_chime()
    _check("deaf", always._deaf_until - always._deaf_from == 9, "chime window not 9 s")
    always.clip_done(pcm)
    _check("deaf", always._waiting is None, "clip queued during the chime window")

    _reset_deaf()
    os.environ["REPLY_DEAF_SECONDS"] = "3"
    always.deafen_for_reply()
    os.environ.pop("REPLY_DEAF_SECONDS")
    _check("deaf", always._deaf_until - always._deaf_from == 3, "REPLY_DEAF_SECONDS ignored")
    _reset_deaf()

    real = listen.capturing
    listen.capturing = lambda: True
    try:
        always.clip_done(pcm)
    finally:
        listen.capturing = real
    _check("deaf", always._waiting is None, "clip queued during listen now")
    _passed(done, "deaf windows (reply 12 s, chime 9 s) and listen now drop clips, no file kept")


async def _capture_cases(done):
    real_cmd, real_wait = always.capture_command, always.RESTART_SECONDS
    always.RESTART_SECONDS = 0.05
    starts = []

    async def run(cmd, seconds):
        def fake():
            starts.append(1)
            return cmd
        always.capture_command = fake
        task = asyncio.create_task(always._capture())
        await asyncio.sleep(seconds)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    try:
        listen.MIC_OK = True
        await run([sys.executable, "-c", "pass"], 1.0)  # ffmpeg exits at once
        _check("restart", len(starts) >= 3 and listen.MIC_OK is False, (len(starts), listen.MIC_OK))
        starts.clear()
        listen.MIC_OK = True
        await run([str(TMP / "no-such-ffmpeg")], 0.5)  # ffmpeg missing
        _check("restart", len(starts) >= 3 and listen.MIC_OK is False, (len(starts), listen.MIC_OK))
        _passed(done, "ffmpeg stops or is missing: mic false, restarted, no crash")

        zeros, hiss = TMP / "zeros.raw", TMP / "hiss.raw"
        zeros.write_bytes(bytes(2 * 32000))
        hiss.write_bytes(_noise(2, 57))
        await run([sys.executable, "-c", FAKE_ONCE, str(hiss)], 0.5)
        _check("mic", listen.MIC_OK is True, "mic false while noise arrives")
        await run([sys.executable, "-c", FAKE_ONCE, str(zeros)], 0.5)
        _check("mic", listen.MIC_OK is False, "mic true after 2 s of exact zeros")
        _passed(done, "mic flag: true while sound arrives, false after a second of exact zeros")
    finally:
        always.capture_command, always.RESTART_SECONDS = real_cmd, real_wait


def _enable_cases(done):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        always.enable_always()
        off = always.ENABLED
        os.environ["ALWAYS_LISTEN"] = "1"
        always.enable_always()
        on = always.ENABLED
    os.environ.pop("ALWAYS_LISTEN")
    always.ENABLED = False
    lines = out.getvalue().splitlines()
    _check("enable", (off, on) == (False, True), (off, on))
    _check("enable", lines == ["always-listening: off", "always-listening: on"], lines)
    _passed(done, "enable_always: on only with ALWAYS_LISTEN=1, prints one line")


def _serve(port):
    runner = uvicorn.Server(uvicorn.Config(server.app, host="127.0.0.1", port=port,
                                           log_level="error"))
    thread = threading.Thread(target=runner.run, daemon=True)
    thread.start()
    return runner, thread


async def _default_off(done):
    starts = []
    real = always.capture_command
    always.capture_command = lambda: starts.append(1) or real()
    os.environ["ALWAYS_LISTEN"] = "1"  # set, but main() never ran: still off
    port = _free_port()
    runner, thread = _serve(port)
    try:
        await _wait_up(port)
        await asyncio.sleep(0.5)
    finally:
        runner.should_exit = True
        thread.join(timeout=5)
        always.capture_command = real
        os.environ.pop("ALWAYS_LISTEN")
    _check("off", starts == [] and always.ENABLED is False, len(starts))
    _passed(done, "default off: importing and running the app starts no capture")


async def _e2e_cases(port, done, whisper_up, go):
    await _wait_up(port)
    async with websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=backstage") as ws:
        await _recv_event(ws, "health", 3)
        await asyncio.sleep(1.2)  # the fake mic's first second of noise: the gate learns the room
        go.write_text("go")
        heard = await _recv_event(ws, "heard")
        _check("e2e", heard["dropped"] is False and heard["drop_reason"] == "",
               (heard["dropped"], heard["drop_reason"]))
        _check("e2e", isinstance(heard["transcript"], str) and heard["transcript"],
               f"length {len(heard['transcript'])}")
        decided = await _recv_event(ws, "decided")
        _check("e2e", decided["transcript"] == heard["transcript"], decided["action"])
        print(f"  {'Whisper' if whisper_up else 'fake transcriber'}: heard "
              f"{len(heard['transcript'])} characters; decided: {decided['action']} "
              f"({decided['source']})")
        if not whisper_up:  # the fake got exactly the one cut clip: c03.wav plus pre-roll/hangover
            most = 1.6 + always.PRE_ROLL_SECONDS + always.SILENCE_SECONDS + 0.1
            _check("e2e", len(FAKE_SEEN) == 1 and 1.6 <= FAKE_SEEN[0] <= most, FAKE_SEEN)
            print(f"  fake transcriber got one clip of {FAKE_SEEN[0]:.2f} s")
        _check("e2e", len(WRITTEN) == 1, f"{len(WRITTEN)} clips written")
        _check("e2e", not any(p.exists() for p in WRITTEN), "clip still on disk")
        _check("e2e", await _count_events(ws, ("heard", "decided"), 2.0) == 0, "extra event")
        _passed(done, E2E)


async def _wait_deaf(timeout=2.0):
    # publish() sends `decided` before it calls deafen_for_reply()/deafen_for_chime(), so wait
    # (up to `timeout`) for the window to open. Returns the seconds left in it.
    deadline = time.monotonic() + timeout
    while always._deaf_until == 0.0 and time.monotonic() < deadline:
        await asyncio.sleep(0.01)
    return always._deaf_until - time.monotonic()


async def _wiring_cases(port, done):
    await _wait_up(port)
    async with websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=backstage") as ws:
        await _recv_event(ws, "health", 3)
        for text, seconds in (("Nasaan si Nanay?", 12), ("Tulong", 9)):
            _reset_deaf()
            _check("wiring", _post(port, {"mode": "typed", "text": text}) == 202)
            decided = await _recv_event(ws, "decided")
            left = await _wait_deaf()
            _check("wiring", seconds - 2 < left <= seconds, (decided["action"], round(left, 2)))
            before = len(WRITTEN)
            always.clip_done(bytes(FRAME * 30))  # a clip now is dropped: nothing written
            _check("wiring", len(WRITTEN) == before, "clip written during a deaf window")
            print(f"  {decided['action']} -> deaf for {seconds} s")
        _reset_deaf()
        _passed(done, "server: play_reply and the urgent chime start the deaf windows")


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


async def _stop_cases(done, pidfile):
    _check("stop", pidfile.exists(), "the fake mic never started")
    pid = int(pidfile.read_text())
    deadline = time.monotonic() + 2
    while _pid_alive(pid) and time.monotonic() < deadline:
        await asyncio.sleep(0.05)
    alive = _pid_alive(pid)
    if alive:
        os.kill(pid, signal.SIGKILL)  # leave nothing running
    left = [p for p in WRITTEN if p.exists()]
    for path in left:
        path.unlink()
    _check("stop", not alive, "fake mic still running after the server stopped (killed now)")
    _check("stop", not left, f"{len(left)} clip file(s) left on disk")
    _passed(done, "server stop kills the mic process and leaves no clip file")


async def _section(run, *args):
    # One group of checks. A failure prints its reason here; the other groups still run.
    try:
        result = run(*args)
        if asyncio.iscoroutine(result):
            await result
    except Exception as exc:
        print(f"FAIL {type(exc).__name__} {exc}")


async def _run():
    # SKIP_WHISPER=1: no request at all to whisper-server, not even the reachability check.
    whisper_up = (os.environ.get("SKIP_WHISPER") != "1"
                  and server._reachable(server.WHISPER_URL, 0.5))
    if not whisper_up:
        server.WHISPER_URL = listen.WHISPER_INFERENCE = "http://127.0.0.1:9"
        listen.transcribe = _fake_transcribe
        print("Whisper: fake transcriber (SKIP_WHISPER=1 or whisper-server not reachable)")
    always.write_wav = _spy_write_wav
    done = []
    go, pidfile = TMP / "go", TMP / "fake-mic.pid"
    (TMP / "noise.raw").write_bytes(_noise(1, 57, 11))
    (TMP / "speech.raw").write_bytes(_noise(1.5, 57) + _wav_pcm(C03) + _noise(2, 57, 5))
    fake_mic = [sys.executable, "-c", FAKE_MIC, str(go), str(TMP / "noise.raw"),
                str(TMP / "speech.raw"), str(pidfile)]
    await _section(_gate_cases, done)
    await _section(_newest_wins, done)
    await _section(_deaf_cases, done)
    await _section(_capture_cases, done)
    await _section(_enable_cases, done)
    await _section(_default_off, done)

    WRITTEN.clear()
    always.ENABLED = True  # what main() does with ALWAYS_LISTEN=1
    always.capture_command = lambda: fake_mic
    port = _free_port()
    runner, thread = _serve(port)
    try:
        await _section(_e2e_cases, port, done, whisper_up, go)
        await _section(_wiring_cases, port, done)
    finally:
        runner.should_exit = True
        thread.join(timeout=5)
        always.ENABLED = False
        _reset_deaf()
    await _section(_stop_cases, done, pidfile)
    shutil.rmtree(TMP, ignore_errors=True)
    for name in CHECKS:
        if name not in done:
            print(f"FAIL {name}")
    print(f"PASS {len(done)}/{len(CHECKS)}")
    return len(done) == len(CHECKS)


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(_run()) else 1)
