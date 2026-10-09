"""Hub server: POST /listen and /ws call decide() and fan out the locked events.

Wire shapes live in docs/sino/architecture.md. Gaps are marked there.
"""

import asyncio
import json
import os
import time
import urllib.request
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import Response
from starlette.websockets import WebSocketDisconnect

from ask import answer_about_lola
from decide import decide, load_seed
from model import DEFAULT_HUB_URL

SCREENS = ("lola", "caregiver", "backstage")
WHISPER_URL = "http://127.0.0.1:8080"
DEFAULT_PORT = 8000


def log_path():
    raw = os.environ.get("SINO_LOG", "")
    if raw:
        return Path(raw)
    return Path(__file__).resolve().parent / "decisions.jsonl"


def read_log():
    path = log_path()
    entries = []
    if not path.is_file():
        return {"entries": entries}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict):
            entries.append(item)
    return {"entries": entries}


def append_decision(text, result):
    entry = {
        "at": datetime.now().strftime("%I:%M %p").lstrip("0"),
        "transcript": text,
        "action": result["action"],
        "reply_id": result.get("reply_id", ""),
        "reason": result.get("reason", ""),
        "trigger_words": list(result.get("trigger_words") or []),
        "confidence": result.get("confidence", 0.0),
        "latency_ms": result.get("latency_ms", 0),
        "source": result.get("source", ""),
        "ignored": result.get("ignored", ""),
    }
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def media_for(reply_id):
    try:
        entries = load_seed()
    except (OSError, ValueError):
        return "", ""
    for entry in entries:
        if entry.get("id") != reply_id:
            continue
        audio = entry.get("reply_audio") or ""
        photo = entry.get("photo") or ""
        return audio if isinstance(audio, str) else "", photo if isinstance(photo, str) else ""
    return "", ""


def _reachable(url, timeout):
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except Exception:
        return False


def model_mode():
    mode = os.environ.get("SINO_MODEL", "stub")
    return mode if mode in ("stub", "ollama") else "stub"


class Hub:
    def __init__(self):
        self.clients = {}
        self.queue = None
        self.generation = 0
        self.decide_call = decide
        self.last_event_at = ""
        self._offline = None
        self._offline_checked = 0.0

    def health_payload(self):
        now = time.monotonic()
        if self._offline is None or now - self._offline_checked > 5:
            probe = os.environ.get("OFFLINE_PROBE", "https://example.com")
            self._offline = not _reachable(probe, 1.0)
            self._offline_checked = now
        hub = (os.environ.get("HUB_URL") or DEFAULT_HUB_URL).rstrip("/")
        return {
            "event": "health",
            "whisper": _reachable(WHISPER_URL, 0.3),
            "ollama": _reachable(f"{hub}/api/tags", 0.3),
            "server": True,
            "mic": False,
            "offline": bool(self._offline),
            "model": model_mode(),
            "last_event_at": self.last_event_at,
        }

    async def submit(self, text):
        self.generation += 1
        await self.queue.put((self.generation, text))

    async def worker(self):
        while True:
            gen, text = await self.queue.get()
            while True:
                try:
                    gen, text = self.queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            try:
                result = await asyncio.to_thread(self.decide_call, text)
            except Exception:
                if gen != self.generation:
                    continue
                result = {
                    "action": "caregiver",
                    "reply_id": "",
                    "reason": "model unavailable",
                    "trigger_words": [],
                    "confidence": 0.0,
                    "latency_ms": 0,
                    "source": "model",
                    "ignored": "",
                }
            if gen != self.generation:
                continue
            await self.publish(text, result)

    async def publish(self, text, result):
        append_decision(text, result)
        self.last_event_at = datetime.now().astimezone().isoformat(timespec="seconds")
        heard = {
            "event": "heard",
            "transcript": text,
            "dropped": False,
            "drop_reason": "",
        }
        decided = {
            "event": "decided",
            "action": result["action"],
            "reply_id": result["reply_id"],
            "reason": result["reason"],
            "trigger_words": result["trigger_words"],
            "confidence": result["confidence"],
            "latency_ms": result["latency_ms"],
            "source": result["source"],
            "ignored": result["ignored"],
            "transcript": text,
        }
        await self.send_to("backstage", heard)
        action = result["action"]
        screens = ("backstage",) if action == "silent" else SCREENS
        for screen in screens:
            await self.send_to(screen, decided)
        if action == "comfort":
            audio, photo = media_for(result["reply_id"])
            await self.send_to("lola", {
                "event": "play_reply",
                "reply_id": result["reply_id"],
                "reply_audio": audio,
                "photo": photo,
            })
        elif action == "urgent":
            await self.send_to("caregiver", {"event": "alert", "transcript": text})
        elif action == "caregiver":
            await self.send_to("caregiver", {
                "event": "ask_caregiver",
                "transcript": text,
                "count": self._caregiver_count(text),
            })
        elif action == "silent":
            return
        else:
            raise RuntimeError(f"unknown action {action}")

    def _caregiver_count(self, transcript):
        return sum(
            1
            for entry in read_log()["entries"]
            if entry.get("transcript") == transcript and entry.get("action") == "caregiver"
        )

    async def send_to(self, screen, payload):
        raw = json.dumps(payload, ensure_ascii=False)
        for ws, role in list(self.clients.items()):
            if role != screen:
                continue
            try:
                await ws.send_text(raw)
            except Exception:
                self.clients.pop(ws, None)

    async def on_message(self, websocket, screen, raw):
        try:
            data = json.loads(raw)
        except ValueError:
            return
        if not isinstance(data, dict) or data.get("event") != "ask_about_lola":
            return
        if screen != "caregiver":
            return
        question = data.get("question", "")
        if not isinstance(question, str) or not question.strip() or len(question) > 2000:
            return
        result = await asyncio.to_thread(answer_about_lola, question.strip(), read_log())
        reply = {
            "event": "about_lola",
            "intent": result["intent"],
            "answer": result["answer"],
            "source": result["source"],
            "latency_ms": result["latency_ms"],
        }
        await websocket.send_text(json.dumps(reply, ensure_ascii=False))

    async def watch_health(self):
        previous = None
        while True:
            payload = await asyncio.to_thread(self.health_payload)
            core = (
                payload["whisper"],
                payload["ollama"],
                payload["server"],
                payload["mic"],
                payload["offline"],
            )
            if previous is not None and core != previous:
                for screen in SCREENS:
                    await self.send_to(screen, payload)
            previous = core
            await asyncio.sleep(5)


hub = Hub()


@asynccontextmanager
async def lifespan(_app):
    hub.queue = asyncio.Queue()
    worker = asyncio.create_task(hub.worker())
    watch = asyncio.create_task(hub.watch_health())
    try:
        yield
    finally:
        worker.cancel()
        watch.cancel()
        for task in (worker, watch):
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return hub.health_payload()


@app.get("/questions")
def questions():
    return load_seed()


@app.post("/listen")
async def listen(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return Response(status_code=400)
    if not isinstance(payload, dict):
        return Response(status_code=400)
    mode = payload.get("mode")
    if mode == "listen_now":
        return Response(status_code=202)
    if mode != "typed":
        return Response(status_code=400)
    text = payload.get("text", "")
    if not isinstance(text, str) or len(text) > 2000:
        return Response(status_code=400)
    if text.strip():
        await hub.submit(text)
    return Response(status_code=202)


@app.websocket("/ws")
async def socket(websocket: WebSocket):
    screen = websocket.query_params.get("screen", "")
    if screen not in SCREENS:
        await websocket.accept()
        await websocket.close(code=1008)
        return
    await websocket.accept()
    hub.clients[websocket] = screen
    try:
        payload = await asyncio.to_thread(hub.health_payload)
        await websocket.send_text(json.dumps(payload, ensure_ascii=False))
        while True:
            raw = await websocket.receive_text()
            await hub.on_message(websocket, screen, raw)
    except WebSocketDisconnect:
        pass
    finally:
        hub.clients.pop(websocket, None)


def _ssl_kwargs():
    cert = os.environ.get("CERT", "")
    key = os.environ.get("KEY", "")
    if not cert and not key:
        return {}
    if not cert or not key or not Path(cert).is_file() or not Path(key).is_file():
        raise SystemExit("CERT and KEY must both point at mkcert files")
    return {"ssl_certfile": cert, "ssl_keyfile": key}


def main():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", str(DEFAULT_PORT)))
    uvicorn.run(app, host=host, port=port, log_level="info", **_ssl_kwargs())


if __name__ == "__main__":
    main()
