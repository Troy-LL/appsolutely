"""Public demo mode: isolated sessions, a seeded day, stub only.

Run from the worktree root:

    SINO_MODE=demo .venv/bin/python brain/tests/test_demo_mode.py
"""

import asyncio
import json
import os
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

os.environ["SINO_MODE"] = "demo"
os.environ["SINO_MODEL"] = "ollama"
os.environ["HUB_URL"] = "http://127.0.0.1:9"
os.environ["SINO_DEMO_ROOT"] = tempfile.mkdtemp(prefix="sino-demo-")
os.environ["SINO_LOG"] = str(HERE / "_demo_decisions.jsonl")
os.environ["OFFLINE_PROBE"] = "http://127.0.0.1:9"
os.environ["CLIP_MEDIA"] = tempfile.mkdtemp(prefix="sino-demo-clips-")
os.environ["CAREGIVER_DIST"] = str(HERE / "_no_caregiver_dist")
os.environ.pop("CERT", None)
os.environ.pop("KEY", None)
os.environ.pop("CHIME", None)
os.environ.pop("ALWAYS_LISTEN", None)

import uvicorn  # noqa: E402
import websockets  # noqa: E402

import server  # noqa: E402

NANAY = "Nasaan si Nanay?"


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _open(port, path, data=None, headers=None, method=None, timeout=8):
    if method is None:
        method = "POST" if data is not None else "GET"
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=data, method=method
    )
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, res.read(), res.headers
    except urllib.error.HTTPError as err:
        return err.code, err.read(), err.headers


def _cookie(sid):
    return {"Cookie": f"sino_demo_sid={sid}"}


def _json_headers(sid=None):
    headers = {"Content-Type": "application/json"}
    if sid:
        headers.update(_cookie(sid))
    return headers


def _sid_header(headers):
    raw = headers.get("Set-Cookie") or ""
    for part in raw.split(";"):
        name, _, value = part.strip().partition("=")
        if name == "sino_demo_sid":
            return value, raw
    return "", raw


def _multipart(fields, files):
    boundary = uuid.uuid4().hex
    body = b""
    for name, value in fields:
        body += (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        ).encode("utf-8")
    for name, filename, data in files:
        body += (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
            f'filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'
        ).encode("utf-8") + data + b"\r\n"
    body += f"--{boundary}--\r\n".encode("utf-8")
    return body, f"multipart/form-data; boundary={boundary}"


async def _wait_up(port):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        try:
            status, _body, _headers = _open(port, "/health", timeout=0.5)
            if status == 200:
                return
        except OSError:
            pass
        await asyncio.sleep(0.05)
    raise RuntimeError("server did not start")


async def _recv(ws, timeout=3):
    return json.loads(await asyncio.wait_for(ws.recv(), timeout))


async def _quiet(ws, timeout=0.4):
    try:
        msg = await asyncio.wait_for(ws.recv(), timeout)
    except asyncio.TimeoutError:
        return
    raise AssertionError(msg)


def _loads(body):
    return json.loads(body.decode("utf-8"))


def _meals(entries):
    return [row for row in entries if row.get("event") == "meal_logged"]


def _nanay(entries):
    return [
        row for row in entries
        if row.get("action") == "comfort" and row.get("reply_id") == "nasaan-si-nanay"
    ]


async def _run():
    port = _free_port()
    config = uvicorn.Config(server.app, host="127.0.0.1", port=port, log_level="error")
    runner = uvicorn.Server(config)
    thread = threading.Thread(target=runner.run, daemon=True)
    thread.start()
    passed = 0
    total = 0
    try:
        await _wait_up(port)

        total += 1
        try:
            status, body, headers = _open(port, "/health")
            payload = _loads(body)
            if status != 200 or payload.get("simulated") is not True or payload.get("mode") != "demo":
                raise AssertionError(payload)
            if payload.get("model") != "ollama" or payload.get("event") != "health":
                raise AssertionError(payload)
            if "whisper" not in payload or "mic" not in payload:
                raise AssertionError(sorted(payload))
            if _sid_header(headers)[0]:
                raise AssertionError("health created a session")
            home = _open(port, "/")
            if home[0] == 200 or (home[1] and b'"landing"' in home[1]):
                raise AssertionError((home[0], home[1][:80]))
            passed += 1
            print("health simulated: PASS")
        except Exception as exc:
            print(f"health simulated: FAIL {exc}")

        total += 1
        try:
            status_a, body_a, headers_a = _open(port, "/demo/state")
            state_a = _loads(body_a)
            sid_a, cookie_a = _sid_header(headers_a)
            status_b, body_b, headers_b = _open(port, "/demo/state")
            state_b = _loads(body_b)
            sid_b, _cookie_b = _sid_header(headers_b)
            if status_a != 200 or status_b != 200:
                raise AssertionError((status_a, status_b))
            if sid_a != state_a["sid"] or sid_b != state_b["sid"] or sid_a == sid_b:
                raise AssertionError((state_a, state_b))
            if "HttpOnly" not in cookie_a or "SameSite=Lax" not in cookie_a:
                raise AssertionError(cookie_a)
            if state_a["mode"] != "demo" or state_a["simulated"] is not True or state_a["seeded"] is not True:
                raise AssertionError(state_a)
            again, again_body, _again_headers = _open(port, "/demo/state", headers=_cookie(sid_a))
            if again != 200 or _loads(again_body)["sid"] != sid_a:
                raise AssertionError(again_body)
            by_query, query_body, _query_headers = _open(port, f"/log?sid={sid_a}")
            by_cookie, cookie_body, _cookie_headers = _open(port, "/log", headers=_cookie(sid_a))
            if _loads(query_body)["entries"] != _loads(cookie_body)["entries"]:
                raise AssertionError("query sid and cookie diverged")
            family_status, family_body, _family_headers = _open(
                port, "/family", headers=_cookie(sid_a)
            )
            names = {row["name"] for row in _loads(family_body)["members"]}
            if family_status != 200 or names != {"Joy", "Troy", "Donita"}:
                raise AssertionError(family_body)
            passed += 1
            print("two sessions: PASS")
        except Exception as exc:
            print(f"two sessions: FAIL {exc}")
            return passed == total and total > 0

        async with websockets.connect(
            f"ws://127.0.0.1:{port}/ws?screen=caregiver&sid={sid_a}"
        ) as care_a, websockets.connect(
            f"ws://127.0.0.1:{port}/ws?screen=lola&sid={sid_a}"
        ) as lola_a, websockets.connect(
            f"ws://127.0.0.1:{port}/ws?screen=caregiver&sid={sid_b}"
        ) as care_b:
            total += 1
            try:
                health_a = await _recv(care_a)
                log_a = await _recv(care_a)
                health_l = await _recv(lola_a)
                reply = await _recv(lola_a)
                await _recv(care_b)
                await _recv(care_b)
                if health_a.get("simulated") is not True or health_l.get("mode") != "demo":
                    raise AssertionError((health_a, health_l))
                if reply.get("event") != "urgent_reply" or reply.get("speaker") != "Joy":
                    raise AssertionError(reply)
                entries = log_a["entries"]
                if len(_meals(entries)) != 1 or [row.get("repeat_count") for row in _nanay(entries)] != [1, 2, 3]:
                    raise AssertionError(entries)
                if not any(row.get("event") == "urgent_reply" for row in entries):
                    raise AssertionError(entries)
                if any(row.get("event") == "alert" for row in entries):
                    raise AssertionError(entries)
                await _quiet(care_a)
                passed += 1
                print("seeded day: PASS")
            except Exception as exc:
                print(f"seeded day: FAIL {exc}")

            total += 1
            try:
                seen = []
                real_open = urllib.request.urlopen

                def _watch(url, *args, **kwargs):
                    target = url.full_url if isinstance(url, urllib.request.Request) else str(url)
                    seen.append(target)
                    return real_open(url, *args, **kwargs)

                urllib.request.urlopen = _watch
                started = time.monotonic()
                try:
                    status, body, _headers = _open(
                        port, "/listen",
                        data=json.dumps({"mode": "typed", "text": "Nasaan yung aso?"}).encode("utf-8"),
                        headers=_json_headers(sid_b),
                    )
                    decided = await _recv(care_b)
                finally:
                    urllib.request.urlopen = real_open
                elapsed = time.monotonic() - started
                if status != 202 or body != b"":
                    raise AssertionError((status, body))
                if decided.get("action") != "caregiver" or decided.get("source") != "model":
                    raise AssertionError(decided)
                if elapsed > 2 or any("/api/generate" in item for item in seen):
                    raise AssertionError((elapsed, seen))
                extra = await _recv(care_b)
                if extra.get("event") != "ask_caregiver" or extra.get("transcript") != "Nasaan yung aso?":
                    raise AssertionError(extra)
                passed += 1
                print("stub never calls ollama: PASS")
            except Exception as exc:
                print(f"stub never calls ollama: FAIL {exc}")

            total += 1
            try:
                status, body, _headers = _open(
                    port, "/listen",
                    data=json.dumps({"mode": "typed", "text": NANAY}).encode("utf-8"),
                    headers=_json_headers(sid_a),
                )
                if status != 202 or body != b"":
                    raise AssertionError((status, body))
                decided_c = await _recv(care_a)
                decided_l = await _recv(lola_a)
                play = await _recv(lola_a)
                if decided_c.get("action") != "comfort" or decided_c.get("reply_id") != "nasaan-si-nanay":
                    raise AssertionError(decided_c)
                if decided_l.get("reply_id") != "nasaan-si-nanay":
                    raise AssertionError(decided_l)
                if play.get("event") != "play_reply" or play.get("reply_audio") != "/media/nasaan-si-nanay-reply.m4a":
                    raise AssertionError(play)
                await _quiet(care_b)
                passed += 1
                print("typed comfort: PASS")
            except Exception as exc:
                print(f"typed comfort: FAIL {exc}")

            saved = {"id": ""}
            total += 1
            try:
                await care_a.send(json.dumps({"event": "meal_logged"}))
                await _quiet(care_a)
                await _quiet(care_b)
                log_status, log_body, _log_headers = _open(port, "/log", headers=_cookie(sid_a))
                other_status, other_body, _other_headers = _open(port, "/log", headers=_cookie(sid_b))
                if log_status != 200 or len(_meals(_loads(log_body)["entries"])) != 2:
                    raise AssertionError(log_body)
                if other_status != 200 or len(_meals(_loads(other_body)["entries"])) != 1:
                    raise AssertionError(other_body)
                fields = [("question", "Nasaan yung pusa?"), ("speaker", "Joy")]
                files = [("reply_audio", "reply.webm", b"demo-audio")]
                raw, content_type = _multipart(fields, files)
                q_status, q_body, _q_headers = _open(
                    port, "/questions", data=raw,
                    headers={"Content-Type": content_type, **_cookie(sid_a)},
                )
                saved = _loads(q_body)
                if q_status != 200 or not saved.get("id"):
                    raise AssertionError((q_status, q_body))
                a_questions = _loads(_open(port, "/questions", headers=_cookie(sid_a))[1])
                b_questions = _loads(_open(port, "/questions", headers=_cookie(sid_b))[1])
                if saved["id"] not in {row.get("id") for row in a_questions}:
                    raise AssertionError(a_questions)
                if saved["id"] in {row.get("id") for row in b_questions}:
                    raise AssertionError(b_questions)
                status, body, _headers = _open(
                    port, "/listen",
                    data=json.dumps({"mode": "typed", "text": "Tulong!"}).encode("utf-8"),
                    headers=_json_headers(sid_a),
                )
                if status != 202:
                    raise AssertionError((status, body))
                decided = await _recv(care_a)
                alert = await _recv(care_a)
                if decided.get("action") != "urgent" or alert != {"event": "alert", "transcript": "Tulong!"}:
                    raise AssertionError((decided, alert))
                await _quiet(care_b)
                passed += 1
                print("sessions stay isolated: PASS")
            except Exception as exc:
                print(f"sessions stay isolated: FAIL {exc}")

            total += 1
            try:
                status, body, headers = _open(port, "/demo/reset", data=b"", headers=_cookie(sid_a))
                state = _loads(body)
                if status != 200 or state.get("sid") != sid_a or _sid_header(headers)[0] != sid_a:
                    raise AssertionError((status, body, headers.get("Set-Cookie")))
                log_body = _loads(_open(port, "/log", headers=_cookie(sid_a))[1])
                questions = _loads(_open(port, "/questions", headers=_cookie(sid_a))[1])
                other = _loads(_open(port, "/log", headers=_cookie(sid_b))[1])
                if len(_meals(log_body["entries"])) != 1:
                    raise AssertionError(log_body["entries"])
                if [row.get("repeat_count") for row in _nanay(log_body["entries"])] != [1, 2, 3]:
                    raise AssertionError(log_body["entries"])
                if saved["id"] in {row.get("id") for row in questions}:
                    raise AssertionError(questions)
                if not any(row.get("transcript") == "Nasaan yung aso?" for row in other["entries"]):
                    raise AssertionError(other["entries"])
                fresh = await websockets.connect(
                    f"ws://127.0.0.1:{port}/ws?screen=caregiver&sid={sid_a}"
                )
                try:
                    await _recv(fresh)
                    await _recv(fresh)
                    await _quiet(fresh)
                finally:
                    await fresh.close()
                passed += 1
                print("reset restores seed: PASS")
            except Exception as exc:
                print(f"reset restores seed: FAIL {exc}")

        total += 1
        try:
            listen_now = _open(
                port, "/listen",
                data=json.dumps({"mode": "listen_now"}).encode("utf-8"),
                headers=_json_headers(sid_a),
            )
            audio = _open(
                port, "/listen/audio", data=b"not-a-clip",
                headers={"Content-Type": "application/octet-stream", **_cookie(sid_a)},
            )
            if listen_now[0] != 410 or audio[0] != 410:
                raise AssertionError((listen_now[0], audio[0], listen_now[1], audio[1]))
            passed += 1
            print("listen_now and audio rejected: PASS")
        except Exception as exc:
            print(f"listen_now and audio rejected: FAIL {exc}")

        total += 1
        try:
            _status_c, body_c, headers_c = _open(port, "/demo/state")
            sid_c = _sid_header(headers_c)[0] or _loads(body_c)["sid"]
            codes = []
            for _n in range(31):
                status, _body, _headers = _open(
                    port, "/listen",
                    data=json.dumps({"mode": "typed", "text": NANAY}).encode("utf-8"),
                    headers=_json_headers(sid_c),
                )
                codes.append(status)
            if codes[:30] != [202] * 30 or codes[30] != 429:
                raise AssertionError(codes)
            err = _loads(_open(
                port, "/listen",
                data=json.dumps({"mode": "typed", "text": NANAY}).encode("utf-8"),
                headers=_json_headers(sid_c),
            )[1])
            if err.get("error") != "slow down":
                raise AssertionError(err)
            passed += 1
            print("rate limit: PASS")
        except Exception as exc:
            print(f"rate limit: FAIL {exc}")
    finally:
        runner.should_exit = True
        thread.join(timeout=5)
    print(f"PASS {passed}/{total}")
    return passed == total and total > 0


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(_run()) else 1)
