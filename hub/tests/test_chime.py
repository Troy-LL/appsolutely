"""Urgent chime (D6): plays only on urgent, only in the hub process, only with CHIME=1, never on /lola.

Off by default since Sat ~8:05 AM (the urgent alarm rings on the caregiver iPhone): with
CHIME unset, urgent still sends `alert` to /caregiver and still starts the hub's deaf window.

No sound is made: chime._start (the afplay call) is replaced by a fake that records the
command and hands back a fake alarm we can mark "playing" or "done". Typed questions
go through POST /listen and the real decide() in stub mode.

Run from the repo root:

    ~/sino/hub-venv/bin/python hub/tests/test_chime.py
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
TMP = Path(tempfile.mkdtemp(prefix="sino-chime-test-"))
os.environ["HUB_DATA"] = str(TMP / "data")
os.environ["SINO_SEED"] = str(TMP / "data" / "questions.json")
os.environ["SINO_MODEL"] = "stub"
os.environ["SINO_LOG"] = str(TMP / "decisions.jsonl")
os.environ["OFFLINE_PROBE"] = "http://127.0.0.1:9"
for name in ("CERT", "KEY", "CHIME"):
    os.environ.pop(name, None)
sys.path.insert(0, str(ROOT / "brain"))

import uvicorn  # noqa: E402
import websockets  # noqa: E402

import server  # noqa: E402
import always  # noqa: E402  (hub/always.py: the deaf windows)
import chime  # noqa: E402  (hub/chime.py, put on sys.path by server)

PLAYED = []  # one entry per alarm that would have started
ALARMS = []  # the fake alarms handed back, newest last

# What one alarm must run: Glass at -v 1, 5 times back to back, no gap (no sleep).
GLASS = "afplay -v 1 /System/Library/Sounds/Glass.aiff"
EXPECTED = ["sh", "-c", f"{GLASS}; {GLASS}; {GLASS}; {GLASS}; {GLASS}"]


class FakeAlarm:
    """Stands in for the afplay process: poll() is None while playing, 0 once done."""

    def __init__(self):
        self.playing = True

    def poll(self):
        return None if self.playing else 0


def fake_start(cmd):
    PLAYED.append(cmd)
    ALARMS.append(FakeAlarm())
    return ALARMS[-1]


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _post_typed(port, text):
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


async def _recv_event(ws, name, timeout=10):
    # Skip other events until the one we want arrives. Returns it and the names seen on the way.
    seen, deadline = [], time.monotonic() + timeout
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), deadline - time.monotonic()))
        seen.append(msg.get("event"))
        if msg.get("event") == name:
            return msg, seen


async def _drain(ws, seconds):
    # Names of every event that arrives in the next `seconds`.
    seen, deadline = [], time.monotonic() + seconds
    while True:
        try:
            msg = json.loads(await asyncio.wait_for(ws.recv(), deadline - time.monotonic()))
        except asyncio.TimeoutError:
            return seen
        seen.append(msg.get("event"))


def _passed(done, name):
    done.append(name)
    print(f"{name}: PASS")


def _check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name} {detail}")


def _unit_cases(done):
    chime._start = fake_start
    chime.ENABLED = False
    os.environ["CHIME"] = "1"
    chime.play_chime()
    _check("off", PLAYED == [], len(PLAYED))
    _passed(done, "play_chime does nothing before enable_chime, even with CHIME=1")

    chime.enable_chime()
    os.environ.pop("CHIME")
    chime.play_chime()
    _check("default", PLAYED == [], len(PLAYED))
    _passed(done, "enabled, CHIME unset: off by default")

    os.environ["CHIME"] = "0"
    chime.play_chime()
    _check("chime=0", PLAYED == [], len(PLAYED))
    _passed(done, "CHIME=0 keeps it off after enable_chime")

    os.environ["CHIME"] = "1"
    chime.play_chime()
    _check("on", PLAYED == [EXPECTED], PLAYED)
    _check("on", (chime.TIMES, chime.GAP_SECONDS) == (5, 0), (chime.TIMES, chime.GAP_SECONDS))
    _check("on", "sleep" not in chime.COMMAND[2], chime.COMMAND)
    _passed(done, "CHIME=1: one alarm = Glass at -v 1, 5 times back to back, no sleep")

    chime.play_chime()  # a second urgent line while the first alarm is still playing
    _check("overlap", len(PLAYED) == 1, f"{len(PLAYED)} alarms started")
    _passed(done, "second urgent while one is playing: no second alarm")

    ALARMS[-1].playing = False  # the first alarm has finished
    chime.play_chime()
    _check("again", len(PLAYED) == 2, f"{len(PLAYED)} alarms started")
    _passed(done, "after the alarm ends, the next urgent plays again")

    def broken_start(cmd):
        raise OSError("test: no afplay")

    ALARMS[-1].playing = False
    chime._start = broken_start
    chime.play_chime()  # must not raise
    chime._start = fake_start
    _passed(done, "afplay failure does not raise")
    PLAYED.clear()


async def _e2e_cases(port, done):
    base = f"ws://127.0.0.1:{port}/ws?screen="
    async with websockets.connect(base + "lola") as lola, \
            websockets.connect(base + "caregiver") as care, \
            websockets.connect(base + "backstage") as back:
        for ws in (lola, care, back):
            await _recv_event(ws, "health", 3)
        lola_seen = []

        # Laptop chime off (the default): /caregiver still gets the alert, no sound, and the
        # hub still goes deaf after the urgent (the iPad mic may hear the phone's alarm).
        os.environ.pop("CHIME")
        now = time.monotonic()
        _check("chime off", not always.deaf(now - 0.1, now), "deaf before any urgent")
        _check("chime off", _post_typed(port, "Masakit dibdib ko") == 202)
        alert, _ = await _recv_event(care, "alert")
        _check("chime off", alert == {"event": "alert", "transcript": "Masakit dibdib ko"}, alert)
        now = time.monotonic()
        _check("chime off", always.deaf(now - 0.1, now), "no deaf window after urgent")
        await _recv_event(back, "decided")
        lola_seen += await _drain(lola, 1.0)
        _check("chime off", PLAYED == [], f"chime ran {len(PLAYED)} times")
        _passed(done, "laptop chime off: urgent still alerts /caregiver and deafens the hub, no sound")

        os.environ["CHIME"] = "1"
        _check("urgent", _post_typed(port, "Masakit dibdib ko") == 202)
        alert, _ = await _recv_event(care, "alert")
        _check("urgent", alert == {"event": "alert", "transcript": "Masakit dibdib ko"}, alert)
        _check("urgent", len(PLAYED) == 1, len(PLAYED))
        decided, _ = await _recv_event(back, "decided")
        _check("urgent", decided["action"] == "urgent", decided["action"])
        lola_seen += await _drain(lola, 1.0)
        _check("urgent", len(PLAYED) == 1, f"chime ran {len(PLAYED)} times")
        _passed(done, "CHIME=1 urgent: chime once, /caregiver gets alert")

        PLAYED.clear()
        for text, action, ignored in (("Nasaan si Nanay?", "comfort", ""),
                                      ("Abangan ang susunod na kabanata", "silent", "tv")):
            _check(action, _post_typed(port, text) == 202)
            decided, _ = await _recv_event(back, "decided")
            _check(action, (decided["action"], decided["ignored"]) == (action, ignored),
                   (decided["action"], decided["ignored"]))
            care_seen = await _drain(care, 1.0)
            lola_seen += await _drain(lola, 0.2)
            _check(action, "alert" not in care_seen, care_seen)
            _check(action, PLAYED == [], f"chime ran {len(PLAYED)} times")
            _passed(done, f"{action}{' (TV line)' if ignored else ''}: no chime, no alert")

        _check("lola", "alert" not in lola_seen and "decided" in lola_seen, lola_seen)
        _passed(done, "/lola never receives alert")


async def _run():
    port = _free_port()
    runner = uvicorn.Server(uvicorn.Config(server.app, host="127.0.0.1", port=port,
                                           log_level="error"))
    thread = threading.Thread(target=runner.run, daemon=True)
    thread.start()
    done = []
    total = 12
    try:
        _unit_cases(done)
        await _wait_up(port)
        await _e2e_cases(port, done)
    except (AssertionError, asyncio.TimeoutError, ValueError, OSError, RuntimeError) as exc:
        print(f"FAIL {type(exc).__name__} {exc}")
    finally:
        runner.should_exit = True
        thread.join(timeout=5)
        shutil.rmtree(TMP, ignore_errors=True)
    print(f"PASS {len(done)}/{total}")
    return len(done) == total


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(_run()) else 1)
