"""Joy's committed replies in brain/media/ reach /lola through play_reply and /media.

Starts from an old hub working copy (every reply_audio empty, two caregiver recordings),
like a hub that ran before the clips were committed. Run from the repo root:

    SINO_MODEL=stub .venv/bin/python brain/tests/test_media.py
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
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SEED = ROOT / "brain" / "seed.json"
SEED_MEDIA = ROOT / "brain" / "media"
TMP = Path(tempfile.mkdtemp(prefix="sino-media-test-"))
DATA = TMP / "data"
LOG = TMP / "decisions.jsonl"
OWN = {
    "nasaan-ako-reply.m4a": b"caregiver re-recorded under the default name",
    "nasaan-si-joy-reply.wav": b"caregiver recording in another format",
}
os.environ["HUB_DATA"] = str(DATA)
os.environ["SINO_SEED"] = str(DATA / "questions.json")
os.environ["SINO_MODEL"] = "stub"
os.environ["SINO_LOG"] = str(LOG)
os.environ["OFFLINE_PROBE"] = "http://127.0.0.1:9"
os.environ["CAREGIVER_DIST"] = str(TMP / "no-dist")
os.environ.pop("CERT", None)
os.environ.pop("KEY", None)
sys.path.insert(0, str(ROOT / "brain"))


def _old_working_copy():
    entries = json.loads(SEED.read_text(encoding="utf-8"))
    for entry in entries:
        entry["reply_audio"] = ""
        for sub in (entry.get("replies") or {}).values():
            sub["reply_audio"] = ""
        if entry["id"] == "nasaan-ako":
            entry["reply_audio"] = "/media/nasaan-ako-reply.m4a"
        if entry["id"] == "nasaan-si-joy":
            entry["reply_audio"] = "/media/nasaan-si-joy-reply.wav"
    (DATA / "media").mkdir(parents=True)
    for name, data in OWN.items():
        (DATA / "media" / name).write_bytes(data)
    (DATA / "questions.json").write_text(json.dumps(entries), encoding="utf-8")


_old_working_copy()

import uvicorn  # noqa: E402
import websockets  # noqa: E402

import server  # noqa: E402

COMFORT = (
    ("Nasaan si Nanay?", "nasaan-si-nanay", "/media/nasaan-si-nanay-reply.m4a"),
    ("Nasaan si Joy?", "nasaan-si-joy", "/media/nasaan-si-joy-reply.wav"),
    ("Nasaan ako?", "nasaan-ako", "/media/nasaan-ako-reply.m4a"),
    ("Gusto ko nang umuwi", "gusto-ko-nang-umuwi", "/media/gusto-ko-nang-umuwi-reply.m4a"),
)
MEALS = (
    (None, "unknown", "/media/meal-check-unknown-reply.m4a"),
    (1, "ate", "/media/meal-check-ate-reply.m4a"),
    (None, "ate_repeat", "/media/meal-check-ate-repeat-reply.m4a"),
)


def _check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name}: {detail}")


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _get(port, path):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=3) as res:
        return res.status, res.headers.get("content-type", ""), res.read()


def _ask(port, text):
    body = json.dumps({"mode": "typed", "text": text}).encode("utf-8")
    req = urllib.request.Request(f"http://127.0.0.1:{port}/listen", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=3) as res:
        _check("listen", res.status == 202, res.status)


async def _play_reply(ws):
    deadline = time.monotonic() + 5
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), deadline - time.monotonic()))
        if msg.get("event") == "play_reply":
            return msg


def _seed_paths():
    # Every non-empty seed path names a committed file; sino-ka and photos stay empty.
    entries = {e["id"]: e for e in json.loads(SEED.read_text(encoding="utf-8"))}
    ids = [reply_id for _, reply_id, _ in COMFORT]
    paths = [entries[i]["reply_audio"] for i in ids] + [entries["meal-check"]["reply_audio"]]
    paths += [v["reply_audio"] for v in entries["meal-check"]["replies"].values()]
    for path in paths:
        _check("seed", path.startswith("/media/") and (SEED_MEDIA / path[7:]).is_file(), path)
    sino = entries["sino-ka"]
    _check("seed", sino["reply_audio"] == "" and all(
        p["reply_audio"] == "" for p in sino["by_person"].values()), sino)
    _check("seed", all(e["photo"] == "" for e in entries.values()))


async def _cases(port):
    done = []
    _seed_paths()
    done.append("seed paths point at brain/media files")

    working = {e["id"]: e for e in json.loads((DATA / "questions.json").read_text(encoding="utf-8"))}
    _check("fill", working["nasaan-si-nanay"]["reply_audio"] == "/media/nasaan-si-nanay-reply.m4a",
           working["nasaan-si-nanay"])
    _check("fill", working["nasaan-si-joy"]["reply_audio"] == "/media/nasaan-si-joy-reply.wav",
           working["nasaan-si-joy"])
    _check("fill", working["meal-check"]["replies"]["ate"]["reply_audio"]
           == "/media/meal-check-ate-reply.m4a", working["meal-check"])
    done.append("old working copy filled, caregiver recording kept")

    async with websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=lola") as lola:
        for text, reply_id, audio in COMFORT:
            _ask(port, text)
            play = await _play_reply(lola)
            _check(reply_id, play["reply_id"] == reply_id and play["reply_audio"] == audio, play)
            status, kind, body = _get(port, audio)
            _check(reply_id, status == 200 and kind.startswith("audio/"), (status, kind))
            want = OWN.get(audio[7:]) or (SEED_MEDIA / audio[7:]).read_bytes()
            _check(reply_id, body == want, f"{len(body)} bytes")
            done.append(f"{reply_id} plays {audio}")

        for hours_ago, variant, audio in MEALS:
            if hours_ago is not None:
                ts = (datetime.now().astimezone() - timedelta(hours=hours_ago)).isoformat(timespec="seconds")
                with LOG.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"event": "meal_logged", "ts": ts}) + "\n")
            _ask(port, "Kumain na ba ako?")
            play = await _play_reply(lola)
            _check(variant, play["reply_id"] == "meal-check" and play["reply_audio"] == audio, play)
            status, kind, body = _get(port, audio)
            _check(variant, status == 200 and kind.startswith("audio/"), (status, kind))
            _check(variant, body == (SEED_MEDIA / audio[7:]).read_bytes(), f"{len(body)} bytes")
            done.append(f"meal {variant} plays {audio}")

    status, kind, _ = _get(port, "/media/nasaan-si-joy-reply.m4a")
    _check("copy", status == 200 and kind.startswith("audio/"), (status, kind))
    done.append("missing default clips copied next to the caregiver's")
    return done


async def _run():
    server.ensure_working_copy()
    port = _free_port()
    runner = uvicorn.Server(uvicorn.Config(server.app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=runner.run, daemon=True)
    thread.start()
    done = []
    total = 10
    try:
        deadline = time.monotonic() + 5
        while True:
            try:
                _get(port, "/health")
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise
                await asyncio.sleep(0.05)
        done = await _cases(port)
    except (AssertionError, asyncio.TimeoutError, OSError, KeyError, ValueError) as exc:
        print(f"FAIL {type(exc).__name__} {exc}")
    finally:
        runner.should_exit = True
        thread.join(timeout=5)
        shutil.rmtree(TMP, ignore_errors=True)
    for name in done:
        print(f"{name}: PASS")
    print(f"PASS {len(done)}/{total}")
    return len(done) == total


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(_run()) else 1)
