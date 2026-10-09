"""Hub server: POST /listen and /ws call decide() and fan out the locked events.

Wire shapes live in docs/sino/architecture.md. Gaps are marked there.
"""

import asyncio
import json
import os
import sys
import threading
import time
import urllib.request
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import UploadFile
from starlette.websockets import WebSocketDisconnect

from ask import answer_about_lola
from decide import decide, load_seed
from model import DEFAULT_HUB_URL

# brain/face ships on troy/face-engine and may be absent. Script launch also tries face.
try:
    from brain.face import load_gallery, identify_jpeg
except ImportError:
    try:
        from face import load_gallery, identify_jpeg
    except ImportError:
        def load_gallery():
            return None

        def identify_jpeg(_gallery, _jpeg):
            return {"who": None, "score": 0.0, "faces": 0, "ms": 0}

# hub/questions.py (Donita, D5) stores new questions and their files. Appended last so brain/ wins.
sys.path.append(str(Path(__file__).resolve().parent.parent / "hub"))
from questions import MAX_BYTES, BadInput, ensure_working_copy, media_dir, save_question  # noqa: E402
# hub/listen.py (Donita, D4): listen now records the hub mic, runs Whisper and the junk filter.
from listen import enable_mic, mic_ok, start_listen  # noqa: E402
# hub/chime.py (Donita, D6): the urgent chime on the hub speaker.
from chime import enable_chime, play_chime  # noqa: E402

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
            "mic": mic_ok(),
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
        matched = None
        if result["action"] == "comfort" and result.get("reply_id") == "sino-ka":
            matched = await asyncio.to_thread(look_at_camera)
            decided["who"] = matched["who"]
        await self.send_to("backstage", heard)
        action = result["action"]
        screens = ("backstage",) if action == "silent" else SCREENS
        for screen in screens:
            await self.send_to(screen, decided)
        if matched is not None:
            await self.send_to("backstage", {
                "event": "face_seen",
                "who": matched["seen_who"],
                "score": matched["score"],
            })
        if action == "comfort":
            if matched is not None and matched["use_person"]:
                audio, photo = matched["audio"], matched["photo"]
            else:
                audio, photo = media_for(result["reply_id"])
            await self.send_to("lola", {
                "event": "play_reply",
                "reply_id": result["reply_id"],
                "reply_audio": audio,
                "photo": photo,
            })
        elif action == "urgent":
            play_chime()  # hub speaker, returns at once (docs/sino/hub-chime.md); never /lola
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
# Recorded replies and photos. StaticFiles refuses paths that leave this folder.
media_dir().mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=media_dir()), name="media")


@app.get("/health")
def health():
    return hub.health_payload()


@app.get("/questions")
def questions():
    return load_seed()


async def _upload(part):
    # A file part becomes (filename, bytes). No part, a text value, or no file chosen -> None.
    if not isinstance(part, UploadFile) or not part.filename:
        return None
    return part.filename, await part.read(MAX_BYTES + 1)


@app.post("/questions")
async def add_question(request: Request):
    # Multipart form: id, question, speaker, phrasings (repeated); files reply_audio, photo.
    try:
        async with request.form() as form:
            fields = {
                "id": form.get("id"),
                "question": form.get("question"),
                "speaker": form.get("speaker"),
                "phrasings": form.getlist("phrasings"),
            }
            audio = await _upload(form.get("reply_audio"))
            photo = await _upload(form.get("photo"))
        # No await inside save_question, so two uploads cannot interleave their writes.
        return save_question(fields, audio, photo)
    except BadInput as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


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
        # Record, transcribe, and filter in the background; what happened arrives on /ws.
        start_listen(hub)
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


# One webcam frame when "Sino ka?" is comfort. cv2 may be absent; the server still starts.

FRAME_TIMEOUT = 1.5


def face_threshold():
    raw = os.environ.get("FACE_THRESHOLD_HIGH", "0.55")
    try:
        value = float(raw)
    except ValueError:
        return 0.55
    if isinstance(value, bool):
        return 0.55
    return value


def _camera_read():
    import cv2
    cap = cv2.VideoCapture(0)
    try:
        if not cap.isOpened():
            return None
        ok, frame = cap.read()
        if not ok or frame is None:
            return None
        good, buf = cv2.imencode(".jpg", frame)
        if not good:
            return None
        return buf.tobytes()
    finally:
        cap.release()


def grab_jpeg():
    box = {}

    def run():
        try:
            jpeg = _camera_read()
        except Exception:
            return
        if jpeg:
            box["jpeg"] = jpeg

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(FRAME_TIMEOUT)
    return box.get("jpeg")


def _person_entry(who):
    try:
        entries = load_seed()
    except (OSError, ValueError):
        return None
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("id") != "sino-ka":
            continue
        people = entry.get("by_person")
        if not isinstance(people, dict):
            return None
        person = people.get(who)
        if not isinstance(person, dict):
            return None
        audio = person.get("reply_audio") or ""
        photo = person.get("photo") or ""
        if not isinstance(audio, str):
            audio = ""
        if not isinstance(photo, str):
            photo = ""
        return audio, photo
    return None


def look_at_camera():
    started = time.monotonic()
    jpeg = grab_jpeg()
    if not jpeg:
        return {
            "who": "",
            "seen_who": None,
            "score": 0.0,
            "audio": "",
            "photo": "",
            "use_person": False,
            "ms": int((time.monotonic() - started) * 1000),
        }
    seen = recognize(jpeg)
    who = ""
    audio, photo = "", ""
    use_person = False
    score = seen["score"]
    name = seen["who"]
    if isinstance(name, str) and name and score >= face_threshold():
        person = _person_entry(name)
        if person is not None:
            who = name
            audio, photo = person
            use_person = True
    return {
        "who": who,
        "seen_who": who or None,
        "score": score,
        "audio": audio,
        "photo": photo,
        "use_person": use_person,
        "ms": int((time.monotonic() - started) * 1000),
    }


_gallery = None
_gallery_tried = False


def _gallery_or_none():
    global _gallery, _gallery_tried
    if _gallery_tried:
        return _gallery
    _gallery_tried = True
    try:
        _gallery = load_gallery()
    except Exception:
        _gallery = None
    return _gallery


def recognize(jpeg):
    try:
        result = identify_jpeg(_gallery_or_none(), jpeg)
    except Exception:
        return {"who": None, "score": 0.0, "faces": 0, "ms": 0}
    if not isinstance(result, dict):
        return {"who": None, "score": 0.0, "faces": 0, "ms": 0}
    who = result.get("who")
    if not isinstance(who, str) or not who.strip():
        who = None
    else:
        who = who.strip()
    score = result.get("score", 0.0)
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        score = 0.0
    faces = result.get("faces", 0)
    if isinstance(faces, bool) or not isinstance(faces, int) or faces < 0:
        faces = 0
    ms = result.get("ms", 0)
    if isinstance(ms, bool) or not isinstance(ms, int) or ms < 0:
        ms = 0
    return {"who": who, "score": float(score), "faces": faces, "ms": ms}


@app.post("/face/frame")
async def face_frame(request: Request):
    length = request.headers.get("content-length")
    if length is not None:
        try:
            if int(length) > MAX_BYTES:
                return Response("frame too large", status_code=400)
        except ValueError:
            return Response("bad content-length", status_code=400)
    chunks = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_BYTES:
            return Response("frame too large", status_code=400)
        chunks.append(chunk)
    result = await asyncio.to_thread(recognize, b"".join(chunks))
    await hub.send_to("backstage", {
        "event": "face_seen",
        "who": result["who"],
        "score": result["score"],
    })
    return result


def _ssl_kwargs():
    cert = os.environ.get("CERT", "")
    key = os.environ.get("KEY", "")
    if not cert and not key:
        return {}
    if not cert or not key or not Path(cert).is_file() or not Path(key).is_file():
        raise SystemExit("CERT and KEY must both point at mkcert files")
    return {"ssl_certfile": cert, "ssl_keyfile": key}


def main():
    # Point load_seed() at the hub's working copy. Done here, not at import, so
    # brain/tests/test_server.py (which imports app) keeps reading brain/seed.json.
    os.environ.setdefault("SINO_SEED", str(ensure_working_copy()))
    # Only the hub process opens the mic, so test_server.py (mic false, listen now silent) still holds.
    enable_mic()
    # Same for the chime: only the hub process makes sound (CHIME=0 keeps it off).
    enable_chime()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", str(DEFAULT_PORT)))
    uvicorn.run(app, host=host, port=port, log_level="info", **_ssl_kwargs())


if __name__ == "__main__":
    main()
