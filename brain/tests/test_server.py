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
from datetime import datetime, timedelta
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


def _post_jpeg(port, body):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/face/frame",
        data=body,
        headers={"Content-Type": "image/jpeg"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=2) as res:
        return res.status, json.loads(res.read().decode("utf-8"))


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

            face_passed, face_total = await _face(port, clients)
            passed += face_passed
            total += face_total

            meal_passed, meal_total = await _meals(port, clients, log_path)
            passed += meal_passed
            total += meal_total
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


def _check_seed_people():
    entries = json.loads((ROOT / "seed.json").read_text(encoding="utf-8"))
    sino = next(entry for entry in entries if entry.get("id") == "sino-ka")
    people = sino.get("by_person")
    if not isinstance(people, dict) or set(people) != {"troy", "joy", "donita"}:
        raise AssertionError(people)
    for name, person in people.items():
        if person.get("reply_audio") != "" or person.get("photo") != "":
            raise AssertionError(name)
        if not isinstance(person.get("speaker"), str) or not person["speaker"]:
            raise AssertionError(person)
    if sino.get("reply_audio") != "" or sino.get("photo") != "" or sino.get("speaker") != "Troy":
        raise AssertionError("fallback")


def _face_seed(load):
    entries = json.loads(json.dumps(load()))
    for entry in entries:
        if entry.get("id") != "sino-ka":
            continue
        entry["reply_audio"] = "troy-line"
        entry["photo"] = "troy.jpg"
        entry["by_person"] = {
            "troy": {"reply_audio": "troy-line", "photo": "troy.jpg", "speaker": "Troy"},
            "joy": {"reply_audio": "joy-line", "photo": "joy.jpg", "speaker": "Joy"},
            "donita": {"reply_audio": "donita-line", "photo": "donita.jpg", "speaker": "Donita"},
        }
    return entries


def _identify_as(who, score=0.91):
    def identify(_gallery, _jpeg):
        return {"who": who, "score": score, "faces": 0 if who is None else 1, "ms": 4}

    return identify


def _check_sino(msg, who):
    if set(msg) != DECIDED_KEYS | {"who"}:
        raise AssertionError(sorted(msg))
    if msg["event"] != "decided" or msg["action"] != "comfort" or msg["reply_id"] != "sino-ka":
        raise AssertionError(msg)
    if msg["transcript"] != "Sino ka?" or msg["who"] != who:
        raise AssertionError(msg)


async def _expect_sino(clients, audio, photo, who, seen_who):
    text = "Sino ka?"
    backstage, lola, caregiver = clients["backstage"], clients["lola"], clients["caregiver"]
    heard = await _recv(backstage)
    if heard != {"event": "heard", "transcript": text, "dropped": False, "drop_reason": ""}:
        raise AssertionError(heard)
    _check_sino(await _recv(backstage), who)
    seen = await _recv(backstage)
    if set(seen) != {"event", "who", "score"} or seen["event"] != "face_seen":
        raise AssertionError(seen)
    if seen["who"] != seen_who:
        raise AssertionError(seen)
    if isinstance(seen["score"], bool) or not isinstance(seen["score"], (int, float)):
        raise AssertionError(seen["score"])
    _check_sino(await _recv(lola), who)
    _check_sino(await _recv(caregiver), who)
    play = await _recv(lola)
    if set(play) != {"event", "reply_id", "reply_audio", "photo"}:
        raise AssertionError(play)
    if play["reply_id"] != "sino-ka" or play["reply_audio"] != audio or play["photo"] != photo:
        raise AssertionError(play)
    await _quiet(lola)
    await _quiet(caregiver)
    await _quiet(backstage)


async def _face_seen(backstage, who):
    msg = await _recv(backstage)
    if set(msg) != {"event", "who", "score"} or msg["event"] != "face_seen":
        raise AssertionError(msg)
    if msg["who"] != who:
        raise AssertionError(msg)


async def _one_face(name, fn):
    try:
        await fn()
        print(f"{name}: PASS")
        return 1
    except (AssertionError, asyncio.TimeoutError, urllib.error.URLError, KeyError) as exc:
        print(f"{name}: FAIL {exc}")
        return 0


def _ask_sino(port):
    status, body = _post(port, {"mode": "typed", "text": "Sino ka?"})
    if status != 202 or body != b"":
        raise AssertionError((status, body))


async def _face(port, clients):
    passed = 0
    total = 0
    real_load = server.load_seed
    real_identify = server.identify_jpeg
    real_grab = server.grab_jpeg
    real_read = server._camera_read
    backstage, lola, caregiver = clients["backstage"], clients["lola"], clients["caregiver"]

    total += 1
    try:
        _check_seed_people()
        passed += 1
        print("seed by_person: PASS")
    except (AssertionError, OSError, ValueError, StopIteration) as exc:
        print(f"seed by_person: FAIL {exc}")

    server.load_seed = lambda: _face_seed(real_load)
    server.grab_jpeg = lambda: b"\xff\xd8\xff\xd9"
    try:
        total += 1
        async def no_module():
            status, result = _post_jpeg(port, b"\xff\xd8\xff\xd9")
            if status != 200 or result.get("who") is not None:
                raise AssertionError(result)
            await _face_seen(backstage, None)
            await _quiet(lola)
            await _quiet(caregiver)
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as res:
                if res.status != 200:
                    raise AssertionError(res.status)
            server.identify_jpeg = _identify_as("joy", 0.99)
            _post_jpeg(port, b"\xff\xd8\xff\xd9")
            await _face_seen(backstage, "joy")
            await _quiet(lola)
            server.grab_jpeg = lambda: None
            server.identify_jpeg = _identify_as("joy", 0.99)
            _ask_sino(port)
            await _expect_sino(clients, "troy-line", "troy.jpg", "", None)

        passed += await _one_face("face frame without module", no_module)

        total += 1
        async def joy_line():
            server.grab_jpeg = lambda: b"\xff\xd8\xff\xd9"
            server.identify_jpeg = _identify_as("joy", 0.91)
            _ask_sino(port)
            await _expect_sino(clients, "joy-line", "joy.jpg", "joy", "joy")

        passed += await _one_face("sino ka joy", joy_line)

        total += 1
        async def low_score():
            server.identify_jpeg = _identify_as("joy", 0.54)
            _ask_sino(port)
            await _expect_sino(clients, "troy-line", "troy.jpg", "", None)

        passed += await _one_face("sino ka below threshold", low_score)

        total += 1
        async def at_threshold():
            server.identify_jpeg = _identify_as("joy", 0.55)
            _ask_sino(port)
            await _expect_sino(clients, "joy-line", "joy.jpg", "joy", "joy")

        passed += await _one_face("sino ka at threshold", at_threshold)

        total += 1
        async def unknown():
            server.identify_jpeg = _identify_as("visitor", 0.99)
            _ask_sino(port)
            await _expect_sino(clients, "troy-line", "troy.jpg", "", None)

        passed += await _one_face("sino ka unknown", unknown)

        total += 1
        async def camera_down():
            server.grab_jpeg = lambda: None
            server.identify_jpeg = _identify_as("joy", 0.99)
            _ask_sino(port)
            await _expect_sino(clients, "troy-line", "troy.jpg", "", None)

        passed += await _one_face("sino ka camera fail", camera_down)

        total += 1
        async def camera_timeout():
            def hang():
                time.sleep(3)
                return b"\xff\xd8\xff\xd9"

            server._camera_read = hang
            server.grab_jpeg = real_grab
            started = time.monotonic()
            jpeg = await asyncio.to_thread(server.grab_jpeg)
            elapsed = time.monotonic() - started
            if jpeg is not None or elapsed >= 2.5:
                raise AssertionError((jpeg, elapsed))

        passed += await _one_face("camera timeout", camera_timeout)
    finally:
        server.load_seed = real_load
        server.identify_jpeg = real_identify
        server.grab_jpeg = real_grab
        server._camera_read = real_read
    return passed, total


UNKNOWN_MEAL = "Lola asked if she's eaten. No meal logged."
MEAL_KEYS = DECIDED_KEYS | {"reply_variant", "last_meal_ts"}


def _hours_ago(hours):
    return (datetime.now().astimezone() - timedelta(hours=hours)).isoformat(timespec="seconds")


def _append_log(log_path, line):
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line if line.endswith("\n") else line + "\n")


def _meal_seed(load):
    entries = json.loads(json.dumps(load()))
    for entry in entries:
        if entry.get("id") != "meal-check":
            continue
        entry["replies"] = {
            "ate": {"reply_audio": "ate-line", "photo": "ate.jpg", "speaker": "Joy"},
            "ate_repeat": {"reply_audio": "ate-repeat-line", "photo": "ate-repeat.jpg", "speaker": "Joy"},
            "unknown": {"reply_audio": "unknown-line", "photo": "unknown.jpg", "speaker": "Joy"},
        }
    return entries


async def _expect_meal(clients, text, variant, audio, photo, last_meal_ts, card_count):
    backstage, lola, caregiver = clients["backstage"], clients["lola"], clients["caregiver"]
    heard = await _recv(backstage)
    if heard != {"event": "heard", "transcript": text, "dropped": False, "drop_reason": ""}:
        raise AssertionError(heard)
    for ws in (backstage, lola, caregiver):
        msg = await _recv(ws)
        if set(msg) != MEAL_KEYS:
            raise AssertionError(sorted(msg))
        if msg["action"] != "comfort" or msg["reply_id"] != "meal-check":
            raise AssertionError(msg)
        if msg["reply_variant"] != variant or msg["last_meal_ts"] != last_meal_ts:
            raise AssertionError(msg)
        if msg["transcript"] != text:
            raise AssertionError(msg)
    play = await _recv(lola)
    if set(play) != {"event", "reply_id", "reply_audio", "photo"}:
        raise AssertionError(play)
    if play["event"] != "play_reply" or play["reply_id"] != "meal-check":
        raise AssertionError(play)
    if play["reply_audio"] != audio or play["photo"] != photo:
        raise AssertionError(play)
    if card_count:
        card = await _recv(caregiver)
        if set(card) != {"event", "transcript", "count"}:
            raise AssertionError(card)
        if card["event"] != "ask_caregiver" or card["transcript"] != UNKNOWN_MEAL:
            raise AssertionError(card)
        if card["count"] != card_count:
            raise AssertionError(card)
        lowered = card["transcript"].lower()
        if "not yet" in lowered or "hindi pa" in lowered or "hasn't eaten" in lowered:
            raise AssertionError(card)
    await _quiet(lola)
    await _quiet(caregiver)
    await _quiet(backstage)


def _ask_meal(port, text="Kumain na ba ako?"):
    status, body = _post(port, {"mode": "typed", "text": text})
    if status != 202 or body != b"":
        raise AssertionError((status, body))


async def _one_meal(name, fn):
    try:
        await fn()
        print(f"{name}: PASS")
        return 1
    except (AssertionError, asyncio.TimeoutError, OSError, ValueError, KeyError) as exc:
        print(f"{name}: FAIL {exc}")
        return 0


async def _meals(port, clients, log_path):
    passed = 0
    total = 0
    real_load = server.load_seed
    server.load_seed = lambda: _meal_seed(real_load)
    try:
        total += 1
        async def no_log():
            _ask_meal(port)
            await _expect_meal(clients, "Kumain na ba ako?", "unknown", "unknown-line", "unknown.jpg", "", 1)

        passed += await _one_meal("no meal plays unknown", no_log)

        total += 1
        old_ts = _hours_ago(8)
        async def old_meal():
            _append_log(log_path, json.dumps({"event": "meal_logged", "ts": old_ts}))
            _ask_meal(port)
            await _expect_meal(clients, "Kumain na ba ako?", "unknown", "unknown-line", "unknown.jpg", old_ts, 2)

        passed += await _one_meal("meal 8h ago plays unknown", old_meal)

        total += 1
        async def broken_skipped():
            _append_log(log_path, "{broken\n")
            _ask_meal(port)
            await _expect_meal(clients, "Kumain na ba ako?", "unknown", "unknown-line", "unknown.jpg", old_ts, 3)

        passed += await _one_meal("broken jsonl line is skipped", broken_skipped)

        total += 1
        recent_ts = _hours_ago(1)
        async def recent_meal():
            _append_log(log_path, json.dumps({"event": "meal_logged", "ts": recent_ts}))
            _ask_meal(port)
            await _expect_meal(clients, "Kumain na ba ako?", "ate", "ate-line", "ate.jpg", recent_ts, 0)

        passed += await _one_meal("meal 1h ago plays ate", recent_meal)

        total += 1
        async def second_ask():
            _ask_meal(port)
            await _expect_meal(
                clients, "Kumain na ba ako?", "ate_repeat", "ate-repeat-line", "ate-repeat.jpg", recent_ts, 0
            )
            rows = []
            for line in log_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
            food = [
                row.get("food_asks_since_meal")
                for row in rows
                if row.get("reply_variant") == "ate_repeat"
            ]
            if food != [2]:
                raise AssertionError(food)
            how = server.answer_about_lola("Kamusta si Lola?", server.read_log())
            if "Asked about food 2x" not in how["answer"]:
                raise AssertionError(how["answer"])

        passed += await _one_meal("second ask plays ate_repeat", second_ask)

        total += 1
        async def caregiver_tap():
            before = log_path.read_text(encoding="utf-8").count('"meal_logged"')
            await clients["caregiver"].send(json.dumps({"event": "meal_logged"}))
            await _quiet(clients["backstage"])
            await _quiet(clients["lola"])
            await _quiet(clients["caregiver"])
            lines = [
                line for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()
            ]
            if lines[-1].startswith("{broken") or lines[-1].startswith("still-not"):
                raise AssertionError(lines[-1])
            last = json.loads(lines[-1])
            if last.get("event") != "meal_logged" or not isinstance(last.get("ts"), str) or not last["ts"]:
                raise AssertionError(last)
            if set(last) != {"event", "ts"}:
                raise AssertionError(sorted(last))
            stamped = datetime.fromisoformat(last["ts"])
            if abs((datetime.now().astimezone() - stamped).total_seconds()) > 30:
                raise AssertionError(last["ts"])
            if log_path.read_text(encoding="utf-8").count('"meal_logged"') != before + 1:
                raise AssertionError("meal_logged was not appended")

        passed += await _one_meal("meal_logged writes ts", caregiver_tap)
    finally:
        server.load_seed = real_load
    return passed, total


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(_run()) else 1)
