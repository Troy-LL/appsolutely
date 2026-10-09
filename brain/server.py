"""Hub server: POST /listen and /ws call decide() and fan out the locked events.

Wire shapes live in docs/sino/architecture.md. Gaps are marked there.
"""

import asyncio
import json
import mimetypes
import os
import sys
import threading
import time
import urllib.request
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import UploadFile
from starlette.websockets import WebSocketDisconnect

import clips as clipwhere
from ask import answer_about_lola
from decide import decide, load_seed, urgent_words
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
from questions import (  # noqa: E402
    MAX_BYTES, BadInput, ensure_working_copy, install_seed_media, media_dir, save_question,
)
# hub/listen.py (Donita, D4): listen now records the hub mic, runs Whisper and the junk filter.
from listen import enable_mic, mic_ok, start_listen  # noqa: E402
# hub/chime.py (Donita, D6): the urgent chime on the hub speaker.
from chime import enable_chime, play_chime  # noqa: E402
# hub/always.py (Donita, D4): always-listening, off unless ALWAYS_LISTEN=1.
from always import always_on, deafen_for_chime, deafen_for_reply, enable_always, start_always  # noqa: E402
# hub/upload.py (Donita): the iPad's mic. Lola's screen uploads short clips; same steps as listen now.
from upload import receive_clip  # noqa: E402

SCREENS = ("lola", "caregiver", "backstage")
UNKNOWN_MEAL_NOTE = "Lola asked if she's eaten. No meal logged."
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
    for key in ("reply_variant", "last_meal_ts", "food_asks_since_meal"):
        if key in result:
            entry[key] = result[key]
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def append_meal():
    entry = {
        "event": "meal_logged",
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def meal_window_hours():
    raw = os.environ.get("MEAL_WINDOW_H", "3")
    try:
        value = float(raw)
    except ValueError:
        return 3.0
    if value < 0:
        return 3.0
    return value


def _parse_ts(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return parsed


def latest_meal(entries):
    found = None
    for index, entry in enumerate(entries):
        if entry.get("event") != "meal_logged":
            continue
        parsed = _parse_ts(entry.get("ts"))
        if parsed is None:
            continue
        if found is None or parsed >= found[0]:
            found = (parsed, entry.get("ts"), index)
    return found


def _food_asks(entries):
    return sum(
        1
        for entry in entries
        if entry.get("reply_id") == "meal-check" and entry.get("action") == "comfort"
    )


def meal_choice(entries, now=None):
    found = latest_meal(entries)
    if found is None:
        prior = _food_asks(entries)
        return {
            "reply_variant": "unknown",
            "last_meal_ts": "",
            "food_asks_since_meal": prior + 1,
        }
    parsed, ts, index = found
    prior = _food_asks(entries[index + 1 :])
    now = now or datetime.now().astimezone()
    age_h = (now - parsed).total_seconds() / 3600
    if age_h <= meal_window_hours():
        variant = "ate_repeat" if prior else "ate"
    else:
        variant = "unknown"
    return {
        "reply_variant": variant,
        "last_meal_ts": ts if isinstance(ts, str) else "",
        "food_asks_since_meal": prior + 1,
    }


def _text(value):
    return value if isinstance(value, str) else ""


def meal_clip(variant):
    try:
        entries = load_seed()
    except (OSError, ValueError):
        return "", "", ""
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("id") != "meal-check":
            continue
        replies = entry.get("replies")
        chosen = replies.get(variant) if isinstance(replies, dict) else None
        if isinstance(chosen, dict):
            speaker = _text(chosen.get("speaker")) or _text(entry.get("speaker"))
            return _text(chosen.get("reply_audio")), _text(chosen.get("photo")), speaker
        return _text(entry.get("reply_audio")), _text(entry.get("photo")), _text(entry.get("speaker"))
    return "", "", ""


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


def speaker_for(reply_id):
    try:
        entries = load_seed()
    except (OSError, ValueError):
        return ""
    for entry in entries:
        if isinstance(entry, dict) and entry.get("id") == reply_id:
            return _text(entry.get("speaker"))
    return ""


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
            "always": always_on(),
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
                    newer = self.queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                # The throttle drops older lines, but never one with an urgent word (QA D-01).
                if urgent_words(text):
                    await self.publish(text, await self._decide(text))
                gen, text = newer
            result = await self._decide(text)
            # A newer line came in while deciding: drop this one, unless it is urgent.
            if gen != self.generation and result["action"] != "urgent":
                continue
            await self.publish(text, result)

    async def _decide(self, text):
        try:
            return await asyncio.to_thread(self.decide_call, text)
        except Exception:
            return {
                "action": "caregiver",
                "reply_id": "",
                "reason": "model unavailable",
                "trigger_words": [],
                "confidence": 0.0,
                "latency_ms": 0,
                "source": "model",
                "ignored": "",
            }

    async def publish(self, text, result):
        meal = None
        if result.get("action") == "comfort" and result.get("reply_id") == "meal-check":
            meal = meal_choice(read_log()["entries"])
            result = {**result, **meal}
        append_decision(text, result)
        self.last_event_at = datetime.now().astimezone().isoformat(timespec="seconds")
        utterance_id = uuid.uuid4().hex
        heard = {
            "event": "heard",
            "transcript": text,
            "dropped": False,
            "drop_reason": "",
            "utterance_id": utterance_id,
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
            "utterance_id": utterance_id,
        }
        if meal is not None:
            decided["reply_variant"] = meal["reply_variant"]
            decided["last_meal_ts"] = meal["last_meal_ts"]
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
                audio, photo, speaker = matched["audio"], matched["photo"], matched["speaker"]
            elif meal is not None:
                audio, photo, speaker = meal_clip(meal["reply_variant"])
            else:
                audio, photo = media_for(result["reply_id"])
                speaker = speaker_for(result["reply_id"])
            await self.send_to("lola", {
                "event": "play_reply",
                "reply_id": result["reply_id"],
                "reply_audio": audio,
                "photo": photo,
                "speaker": speaker,
            })
            deafen_for_reply()  # always-listening ignores the hub mic while the iPad speaks
            if meal is not None and meal["reply_variant"] == "unknown":
                await self.send_to("caregiver", {
                    "event": "ask_caregiver",
                    "transcript": UNKNOWN_MEAL_NOTE,
                    "count": self._unknown_meal_count(),
                })
        elif action == "urgent":
            play_chime()  # hub speaker, returns at once (docs/sino/hub-chime.md); never /lola
            deafen_for_chime()  # always-listening ignores the hub mic while the chime plays
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

    def _unknown_meal_count(self):
        return sum(
            1
            for entry in read_log()["entries"]
            if entry.get("reply_id") == "meal-check" and entry.get("reply_variant") == "unknown"
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
        if not isinstance(data, dict):
            return
        event = data.get("event")
        if event == "meal_logged":
            if screen == "caregiver":
                append_meal()
            return
        if event != "ask_about_lola" or screen != "caregiver":
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
    always = start_always(hub)  # [] unless main() turned always-listening on
    try:
        yield
    finally:
        worker.cancel()
        watch.cancel()
        for task in always:
            task.cancel()
        for task in (worker, watch, *always):
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(lifespan=lifespan)
# Recorded replies and photos. StaticFiles refuses paths that leave this folder.
# Some Python builds have no .m4a mimetype; without it /media would not send an audio type.
mimetypes.add_type("audio/mp4", ".m4a")
install_seed_media()
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


@app.post("/listen/audio")
async def listen_audio(request: Request):
    # Multipart: audio (file), source (optional). 202 empty, or 400 {"error"}. Results on /ws.
    return await receive_clip(hub, request)


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
        return audio, photo, _text(person.get("speaker"))
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
            "speaker": "",
            "use_person": False,
            "ms": int((time.monotonic() - started) * 1000),
        }
    seen = recognize(jpeg)
    who = ""
    audio, photo, speaker = "", "", ""
    use_person = False
    score = seen["score"]
    name = seen["who"]
    if isinstance(name, str) and name and score >= face_threshold():
        person = _person_entry(name)
        if person is not None:
            who = name
            audio, photo, speaker = person
            use_person = True
    return {
        "who": who,
        "seen_who": who or None,
        "score": score,
        "audio": audio,
        "photo": photo,
        "speaker": speaker,
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
    # Always-listening: only the hub process, and only with ALWAYS_LISTEN=1 (off by default).
    enable_always()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", str(DEFAULT_PORT)))
    uvicorn.run(app, host=host, port=port, log_level="info", **_ssl_kwargs())


_CLIP_BYTES = 100 * 1024 * 1024
_plain_read_log = read_log


def read_log():
    log = _plain_read_log()
    seen = clipwhere.last_seen_for_log()
    if seen:
        log["last_seen"] = seen
    return log


def _asked(raw, screen):
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict) or data.get("event") != "ask_about_lola":
        return None
    if screen != "caregiver":
        return None
    question = data.get("question", "")
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        return None
    return question.strip()


_hub_on_message = Hub.on_message


async def _on_message_clips(self, websocket, screen, raw):
    question = _asked(raw, screen)
    if question is None:
        await _hub_on_message(self, websocket, screen, raw)
        return
    log = read_log()
    result = await asyncio.to_thread(answer_about_lola, question, log)
    extra, card = clipwhere.followup(result, log)
    reply = {
        "event": "about_lola",
        "intent": result["intent"],
        "answer": result["answer"],
        "source": result["source"],
        "latency_ms": result["latency_ms"],
    }
    reply.update(extra)
    await websocket.send_text(json.dumps(reply, ensure_ascii=False))
    if card:
        await websocket.send_text(json.dumps(card, ensure_ascii=False))


Hub.on_message = _on_message_clips

_base_lifespan = app.router.lifespan_context


@asynccontextmanager
async def _lifespan_clips(_app):
    loop = asyncio.get_running_loop()
    if clipwhere.has_clips():
        threading.Thread(
            target=clipwhere.scan_and_emit,
            args=(loop, hub),
            daemon=True,
        ).start()
    else:
        await hub.send_to("backstage", clipwhere.scan_event(clipwhere.scan()))
    async with _base_lifespan(_app):
        yield


app.router.lifespan_context = _lifespan_clips


async def _save_clip(request):
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" not in content_type:
        return None
    try:
        async with request.form() as form:
            upload = form.get("clip")
            if upload is None or not getattr(upload, "filename", None):
                return None
            name = Path(upload.filename).name
            if Path(name).suffix.lower() not in clipwhere.SUFFIXES:
                return JSONResponse({"error": "clip must be mp4, mov, or webm"}, status_code=400)
            dest = clipwhere.media_dir() / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            total = 0
            with dest.open("wb") as handle:
                while True:
                    chunk = await upload.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > _CLIP_BYTES:
                        break
                    handle.write(chunk)
            if total > _CLIP_BYTES:
                dest.unlink(missing_ok=True)
                return JSONResponse({"error": "clip too large"}, status_code=400)
            if total == 0:
                dest.unlink(missing_ok=True)
                return JSONResponse({"error": "empty clip"}, status_code=400)
    except Exception:
        return JSONResponse({"error": "bad upload"}, status_code=400)
    return None


@app.post("/clips")
async def post_clips(request: Request):
    saved = await _save_clip(request)
    if isinstance(saved, JSONResponse):
        return saved
    summary = await asyncio.to_thread(clipwhere.scan)
    await hub.send_to("backstage", clipwhere.scan_event(summary))
    return summary


@app.get("/clips/snapshot")
def clips_snapshot():
    jpeg = clipwhere.snapshot_jpeg()
    if not jpeg:
        return Response(status_code=404)
    return Response(
        content=jpeg,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store"},
    )


WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class ScreenFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        name = path.rsplit("/", 1)[-1]
        if name in ("", ".", "index.html"):
            response.headers["Cache-Control"] = "no-cache"
        return response


def caregiver_dist():
    raw = os.environ.get("CAREGIVER_DIST", "")
    if raw:
        return Path(raw)
    return WEB_DIR / "caregiver" / "dist"


def mount_caregiver(application, folder):
    folder = Path(folder)
    if not folder.is_dir():
        return False
    application.mount(
        "/caregiver",
        ScreenFiles(directory=folder, html=True),
        name="caregiver",
    )
    return True


mount_caregiver(app, caregiver_dist())

if (WEB_DIR / "lola").is_dir():
    @app.get("/lola", include_in_schema=False)
    def lola_slash():
        return RedirectResponse("/lola/")

    app.mount("/lola", ScreenFiles(directory=WEB_DIR / "lola", html=True), name="lola")

_backstage_dir = WEB_DIR / "backstage"
if _backstage_dir.is_dir():
    @app.get("/backstage", include_in_schema=False)
    def _backstage_slash():
        return RedirectResponse("/backstage/", status_code=307)

    app.mount("/backstage", ScreenFiles(directory=_backstage_dir, html=True), name="backstage")

if (WEB_DIR / "fake-feed").is_dir():
    app.mount("/fake-feed", StaticFiles(directory=WEB_DIR / "fake-feed"), name="fake-feed")


if __name__ == "__main__":
    main()
