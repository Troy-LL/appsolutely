"""Hub server in stub mode: one transcript in, the locked events out.

Run from the worktree root:

    SINO_MODEL=stub .venv/bin/python brain/tests/test_server.py
"""

import asyncio
import json
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

os.environ["SINO_MODEL"] = "stub"
os.environ["SINO_LOG"] = str(HERE / "_test_decisions.jsonl")
os.environ["OFFLINE_PROBE"] = "http://127.0.0.1:9"
os.environ.pop("CERT", None)
os.environ.pop("KEY", None)

import uvicorn  # noqa: E402
import websockets  # noqa: E402

import server  # noqa: E402
from decide import decide  # noqa: E402

DECIDED_KEYS = {
    "event",
    "action",
    "reply_id",
    "reason",
    "trigger_words",
    "confidence",
    "latency_ms",
    "source",
    "ignored",
    "transcript",
}
HEALTH_KEYS = {
    "event",
    "whisper",
    "ollama",
    "server",
    "mic",
    "offline",
    "model",
    "last_event_at",
}
LINES = (
    ("Nasaan si Nanay?", "comfort", "rule", ""),
    ("Masakit dibdib ko", "urgent", "rule", ""),
    ("Abangan ang susunod na kabanata", "silent", "rule", "tv"),
    ("Inumin ko na ba ang gamot?", "caregiver", "rule", ""),
    ("Nasaan yung aso?", "caregiver", "model", ""),
)


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _post(port, payload):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/listen",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=2) as res:
        return res.status, res.read()


async def _recv(ws, timeout=3):
    return json.loads(await asyncio.wait_for(ws.recv(), timeout))


async def _quiet(ws):
    try:
        msg = await asyncio.wait_for(ws.recv(), 0.2)
    except asyncio.TimeoutError:
        return
    raise AssertionError(f"unexpected {msg}")


def _check_decided(msg, text, action, source, ignored):
    if set(msg) != DECIDED_KEYS:
        raise AssertionError(f"decided keys {sorted(msg)}")
    if msg["event"] != "decided" or msg["action"] != action:
        raise AssertionError(msg)
    if msg["transcript"] != text or msg["source"] != source or msg["ignored"] != ignored:
        raise AssertionError(msg)
    if not isinstance(msg["latency_ms"], int) or msg["latency_ms"] < 0:
        raise AssertionError(msg["latency_ms"])
    if isinstance(msg["confidence"], bool) or not isinstance(msg["confidence"], (int, float)):
        raise AssertionError(msg["confidence"])
    if not isinstance(msg["trigger_words"], list) or not isinstance(msg["reply_id"], str):
        raise AssertionError(msg)
    if not isinstance(msg["reason"], str):
        raise AssertionError(msg)


async def _expect_line(clients, text, action, source, ignored):
    backstage, lola, caregiver = clients["backstage"], clients["lola"], clients["caregiver"]
    heard = await _recv(backstage)
    if heard != {"event": "heard", "transcript": text, "dropped": False, "drop_reason": ""}:
        raise AssertionError(heard)
    decided_b = await _recv(backstage)
    _check_decided(decided_b, text, action, source, ignored)
    if action == "silent":
        await _quiet(lola)
        await _quiet(caregiver)
        await _quiet(backstage)
        return decided_b
    decided_l = await _recv(lola)
    decided_c = await _recv(caregiver)
    _check_decided(decided_l, text, action, source, ignored)
    _check_decided(decided_c, text, action, source, ignored)
    if action == "comfort":
        play = await _recv(lola)
        if set(play) != {"event", "reply_id", "reply_audio", "photo"}:
            raise AssertionError(play)
        if play["event"] != "play_reply" or play["reply_id"] != decided_l["reply_id"]:
            raise AssertionError(play)
        if play["reply_audio"] != "" or play["photo"] != "":
            raise AssertionError(play)
        if decided_l["reply_id"] != "nasaan-si-nanay":
            raise AssertionError(decided_l["reply_id"])
        await _quiet(lola)
        await _quiet(caregiver)
    elif action == "urgent":
        alert = await _recv(caregiver)
        if alert != {"event": "alert", "transcript": text}:
            raise AssertionError(alert)
        await _quiet(lola)
        await _quiet(caregiver)
    elif action == "caregiver":
        ask = await _recv(caregiver)
        if set(ask) != {"event", "transcript", "count"}:
            raise AssertionError(ask)
        if ask["event"] != "ask_caregiver" or ask["transcript"] != text:
            raise AssertionError(ask)
        if not isinstance(ask["count"], int) or ask["count"] < 1:
            raise AssertionError(ask)
        await _quiet(lola)
        await _quiet(caregiver)
        await _quiet(backstage)
        return ask["count"]
    await _quiet(backstage)
    return decided_b


async def _wait_up(port):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.3) as res:
                if res.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            await asyncio.sleep(0.05)
    raise RuntimeError("server did not start")


async def _run():
    log_path = Path(os.environ["SINO_LOG"])
    if log_path.exists():
        log_path.unlink()
    port = _free_port()
    config = uvicorn.Config(server.app, host="127.0.0.1", port=port, log_level="error")
    runner = uvicorn.Server(config)
    thread = threading.Thread(target=runner.run, daemon=True)
    thread.start()
    passed = 0
    total = 0
    try:
        await _wait_up(port)
        async with websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=backstage") as backstage, \
                websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=lola") as lola, \
                websockets.connect(f"ws://127.0.0.1:{port}/ws?screen=caregiver") as caregiver:
            clients = {"backstage": backstage, "lola": lola, "caregiver": caregiver}
            for name, ws in clients.items():
                health = await _recv(ws)
                total += 1
                try:
                    if set(health) != HEALTH_KEYS:
                        raise AssertionError(sorted(health))
                    if health["event"] != "health" or health["model"] != "stub":
                        raise AssertionError(health)
                    if health["offline"] is not True or health["server"] is not True:
                        raise AssertionError(health)
                    if not isinstance(health["whisper"], bool) or not isinstance(health["ollama"], bool):
                        raise AssertionError(health)
                    if health["mic"] is not False or not isinstance(health["last_event_at"], str):
                        raise AssertionError(health)
                    passed += 1
                    print(f"health {name}: PASS")
                except AssertionError as exc:
                    print(f"health {name}: FAIL {exc}")

            total += 1
            status, body = _post(port, {"mode": "listen_now"})
            if status == 202 and body == b"":
                await _quiet(backstage)
                await _quiet(lola)
                await _quiet(caregiver)
                passed += 1
                print("listen_now: PASS")
            else:
                print(f"listen_now: FAIL {status} {body!r}")

            counts = []
            for text, action, source, ignored in LINES:
                total += 1
                status, body = _post(port, {"mode": "typed", "text": text})
                if status != 202 or body != b"":
                    print(f"{action} {text!r}: FAIL status {status} {body!r}")
                    continue
                try:
                    result = await _expect_line(clients, text, action, source, ignored)
                    if action == "caregiver":
                        counts.append(result)
                    passed += 1
                    print(f"{action} {text!r}: PASS")
                except (AssertionError, asyncio.TimeoutError) as exc:
                    print(f"{action} {text!r}: FAIL {exc}")

            total += 1
            if counts == [1, 1]:
                status, body = _post(port, {"mode": "typed", "text": "Nasaan yung aso?"})
                try:
                    again = await _expect_line(
                        clients, "Nasaan yung aso?", "caregiver", "model", ""
                    )
                    if again != 2:
                        raise AssertionError(f"count {again}")
                    passed += 1
                    print("repeat count: PASS")
                except (AssertionError, asyncio.TimeoutError) as exc:
                    print(f"repeat count: FAIL {exc}")
            else:
                print(f"repeat count: FAIL first counts {counts}")

            total += 1
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as res:
                    payload = json.loads(res.read().decode("utf-8"))
                if payload["model"] != "stub" or payload["offline"] is not True:
                    raise AssertionError(payload)
                if not payload["last_event_at"]:
                    raise AssertionError(payload["last_event_at"])
                rows = [
                    json.loads(line)
                    for line in log_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                logged = [row["transcript"] for row in rows]
                for text, _action, _source, _ignored in LINES:
                    if logged.count(text) < 1:
                        raise AssertionError(logged)
                if logged.count("Nasaan yung aso?") != 2:
                    raise AssertionError(logged)
                passed += 1
                print("log and health: PASS")
            except (AssertionError, OSError, ValueError) as exc:
                print(f"log and health: FAIL {exc}")

            total += 1
            try:
                await lola.send(json.dumps({"event": "ask_about_lola", "question": "Kamusta si Lola?"}))
                await _quiet(lola)
                await caregiver.send(json.dumps({
                    "event": "ask_about_lola",
                    "question": "Kamusta si Lola?",
                }))
                reply = await _recv(caregiver)
                if set(reply) != {"event", "intent", "answer", "source", "latency_ms"}:
                    raise AssertionError(sorted(reply))
                if reply["event"] != "about_lola" or reply["intent"] != "how":
                    raise AssertionError(reply)
                if "Not a diagnosis" not in reply["answer"]:
                    raise AssertionError(reply["answer"])
                await _quiet(backstage)
                await _quiet(lola)
                passed += 1
                print("ask about lola: PASS")
            except (AssertionError, asyncio.TimeoutError) as exc:
                print(f"ask about lola: FAIL {exc}")

            total += 1
            try:
                await _stale(port, clients)
                passed += 1
                print("stale newest wins: PASS")
            except (AssertionError, asyncio.TimeoutError) as exc:
                print(f"stale newest wins: FAIL {exc}")
    finally:
        server.hub.decide_call = decide
        runner.should_exit = True
        thread.join(timeout=5)
        if log_path.exists():
            log_path.unlink()
    print(f"PASS {passed}/{total}")
    return passed == total and total > 0


async def _stale(port, clients):
    seen = []
    gate = threading.Event()

    def blocking(text):
        seen.append(text)
        if len(seen) == 1:
            gate.wait(2)
        return decide(text)

    server.hub.decide_call = blocking
    try:
        _post(port, {"mode": "typed", "text": "Nasaan si Nanay?"})
        for _ in range(50):
            if seen:
                break
            await asyncio.sleep(0.02)
        if not seen:
            raise AssertionError("first clip never started")
        _post(port, {"mode": "typed", "text": "Tulong"})
        _post(port, {"mode": "typed", "text": "Nasaan yung susi?"})
        gate.set()
        await _expect_line(clients, "Nasaan yung susi?", "caregiver", "model", "")
        await _quiet(clients["backstage"])
    finally:
        gate.set()
        server.hub.decide_call = decide


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(_run()) else 1)
