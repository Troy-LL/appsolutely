"""Custom safety words: the hub stores one, decide() alarms on it, a TV line does not.

Run from the worktree root:

    SINO_MODEL=stub .venv/bin/python brain/tests/test_safety_words.py
"""

import asyncio
import json
import os
import socket
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

TMP = Path(tempfile.mkdtemp(prefix="sino-safety-"))
os.environ["SINO_MODEL"] = "stub"
os.environ["SINO_SAFETY_WORDS"] = str(TMP / "safety-words.json")
os.environ["SINO_LOG"] = str(TMP / "decisions.jsonl")
os.environ["OFFLINE_PROBE"] = "http://127.0.0.1:9"
os.environ["CAREGIVER_DIST"] = str(TMP / "no-dist")
os.environ.pop("CERT", None)
os.environ.pop("KEY", None)

import uvicorn  # noqa: E402
import websockets  # noqa: E402

import server  # noqa: E402
from decide import SafetyWordError, add_custom_safety_word, decide  # noqa: E402


def _check(name, fn):
    try:
        fn()
    except Exception as exc:
        print(f"{name}: FAIL {exc}")
        return 0
    print(f"{name}: PASS")
    return 1


def _rules():
    before = decide("May lagnat ako")
    if before["action"] == "urgent":
        raise AssertionError(before)

    if add_custom_safety_word("  Lagnat! ") != "lagnat":
        raise AssertionError("stored spelling")

    hit = decide("May lagnat ako")
    if hit["action"] != "urgent" or "lagnat" not in hit["trigger_words"] or hit["source"] != "rule":
        raise AssertionError(hit)

    fuzzy = decide("May lagnot ako")
    if fuzzy["action"] != "urgent" or "lagnat" not in fuzzy["trigger_words"]:
        raise AssertionError(fuzzy)

    glued = decide("Lagnatang bigla")
    if glued["action"] != "urgent" or "lagnat" not in glued["trigger_words"]:
        raise AssertionError(glued)

    tv = decide("Abangan ang susunod na kabanata, may lagnat")
    if tv["action"] != "silent" or tv["ignored"] != "tv":
        raise AssertionError(tv)

    still = decide("Abangan ang susunod na kabanata. Tulong!")
    if still["action"] != "urgent" or "tulong" not in still["trigger_words"]:
        raise AssertionError(still)

    for raw, code in (("", "empty"), ("   ", "empty"), ("aba", "short"), ("tulong", "duplicate"), ("LAGNAT", "duplicate")):
        try:
            add_custom_safety_word(raw)
        except SafetyWordError as exc:
            if str(exc) != code:
                raise AssertionError((raw, exc, code))
        else:
            raise AssertionError(f"{raw!r} was accepted")


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _json(port, method, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=3) as res:
        return res.status, json.loads(res.read().decode("utf-8"))


def _post_error(port, payload):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/safety-words",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=3)
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))
    raise AssertionError("expected 400")


async def _recv(ws, timeout=3):
    return json.loads(await asyncio.wait_for(ws.recv(), timeout))


async def _route(port):
    status, body = _json(port, "GET", "/safety-words")
    if status != 200 or "lagnat" not in body.get("custom", []) or "tulong" not in body.get("builtin", []):
        raise AssertionError(body)

    code, err = _post_error(port, {"word": "lagnat"})
    if code != 400 or err.get("error") != "duplicate":
        raise AssertionError((code, err))

    async with websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=caregiver") as care, \
            websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=backstage") as back:
        if (await _recv(care)).get("event") != "health":
            raise AssertionError("caregiver health")
        if (await _recv(back)).get("event") != "health":
            raise AssertionError("backstage health")
        status, saved = _json(port, "POST", "/safety-words", {"word": "Hilo"})
        if status != 200 or saved != {"word": "hilo"}:
            raise AssertionError(saved)
        got_care = await _recv(care)
        got_back = await _recv(back)
        if got_care != {"event": "safety_word", "word": "hilo"}:
            raise AssertionError(got_care)
        if got_back != {"event": "safety_word", "word": "hilo"}:
            raise AssertionError(got_back)

    fresh = decide("May hilo ako")
    if fresh["action"] != "urgent" or "hilo" not in fresh["trigger_words"]:
        raise AssertionError(fresh)
    tv = decide("Salamat sa panonood, hilo")
    if tv["action"] != "silent" or tv["ignored"] != "tv":
        raise AssertionError(tv)


async def _main():
    passed = _check("custom word is urgent, TV line stays silent", _rules)
    total = 1
    port = _free_port()
    config = uvicorn.Config(server.app, host="127.0.0.1", port=port, log_level="error")
    runner = uvicorn.Server(config)
    thread = threading.Thread(target=runner.run, daemon=True)
    thread.start()
    deadline = asyncio.get_event_loop().time() + 5
    while asyncio.get_event_loop().time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.3) as res:
                if res.status == 200:
                    break
        except OSError:
            await asyncio.sleep(0.05)
    else:
        print("route: FAIL server did not start")
        print(f"{passed}/{total + 1}")
        return 1
    total += 1
    try:
        await _route(port)
        passed += 1
        print("GET POST and safety_word: PASS")
    except Exception as exc:
        print(f"GET POST and safety_word: FAIL {exc}")
    runner.should_exit = True
    print(f"{passed}/{total}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
