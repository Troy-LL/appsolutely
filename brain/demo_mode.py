"""Public demo sessions: one seeded day per visitor, stub decisions, no shared hub files."""

import asyncio
import json
import os
import re
import shutil
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs

from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.staticfiles import StaticFiles

from decide import decide
from family import read_family
from questions import ensure_working_copy
from scope import bind, current_root, current_session, pop_root, push_root, unbind

COOKIE = "sino_demo_sid"
IDLE_S = 15 * 60
MAX_AGE_S = 60 * 60
MAX_SESSIONS = 40
LISTEN_LIMIT = 30
UPLOAD_LIMIT = 12
WRITE_LIMIT = 30
WINDOW_S = 60
PHOTO_CAP = 3 * 1024 * 1024
_SID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_LIMITS = {"listen": LISTEN_LIMIT, "upload": UPLOAD_LIMIT, "write": WRITE_LIMIT}
NANAY = "Nasaan si Nanay?"
URGENT_LINE = "Hirap huminga ako."
RESOLVED = {"text": "Papunta na ako", "speaker": "Joy", "reply_audio": ""}
WEB = Path(__file__).resolve().parent.parent / "web"
_factory = None


def is_demo():
    return os.environ.get("SINO_MODE") == "demo"


def configure(factory):
    global _factory
    _factory = factory


def photo_cap():
    return PHOTO_CAP


class Session:
    def __init__(self, sid, root, hub):
        self.sid = sid
        self.root = root
        self.hub = hub
        self.created = time.monotonic()
        self.touched = self.created
        self.seeded = True
        self.hits = []
        self.worker = None
        self.watch = None

    def touch(self):
        self.touched = time.monotonic()

    def allow(self, bucket, limit, window=WINDOW_S):
        now = time.monotonic()
        self.hits = [(stamp, kind) for stamp, kind in self.hits if now - stamp < window]
        used = sum(1 for _stamp, kind in self.hits if kind == bucket)
        if used >= limit:
            return False
        self.hits.append((now, bucket))
        return True


class SessionStore:
    def __init__(self):
        self.sessions = {}
        self.lock = None
        self.base = None

    def _lock(self):
        if self.lock is None:
            self.lock = asyncio.Lock()
        return self.lock

    def _base(self):
        if self.base is None:
            raw = os.environ.get("SINO_DEMO_ROOT", "")
            if raw:
                self.base = Path(raw)
            else:
                self.base = Path(__file__).resolve().parent.parent / "hub" / "data" / "demo-sessions"
            self.base.mkdir(parents=True, exist_ok=True)
        return self.base

    def evict(self):
        now = time.monotonic()
        for session in list(self.sessions.values()):
            if now - session.created > MAX_AGE_S or now - session.touched > IDLE_S:
                self.drop(session)

    def make_room(self):
        self.evict()
        while len(self.sessions) >= MAX_SESSIONS:
            oldest = min(self.sessions.values(), key=lambda session: session.touched)
            self.drop(oldest)

    def drop(self, session):
        for task in (session.worker, session.watch):
            if task is not None:
                task.cancel()
        self.sessions.pop(session.sid, None)
        shutil.rmtree(session.root, ignore_errors=True)

    def _new(self, sid):
        root = self._base() / sid
        reply = seed_day(root)
        made = _factory(root)
        apply_seed(made, reply)
        session = Session(sid, root, made)
        session.worker = asyncio.create_task(made.worker())
        session.watch = asyncio.create_task(made.watch_health())
        self.sessions[sid] = session
        return session

    async def attach(self, scope, create):
        async with self._lock():
            self.evict()
            sid = sid_from_scope(scope)
            if sid and sid in self.sessions:
                self.sessions[sid].touch()
                return self.sessions[sid], False
            if not create:
                return None, False
            if sid is None:
                sid = str(uuid.uuid4())
            self.make_room()
            if sid in self.sessions:
                self.sessions[sid].touch()
                return self.sessions[sid], False
            return self._new(sid), True

    async def shutdown(self):
        if self.lock is None:
            return
        async with self.lock:
            for session in list(self.sessions.values()):
                self.drop(session)


STORE = SessionStore()


def shutdown_sessions():
    return STORE.shutdown()


def clean_sid(value):
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    if not _SID.fullmatch(value):
        return None
    return value


def sid_from_scope(scope):
    raw_qs = scope.get("query_string", b"")
    if isinstance(raw_qs, bytes):
        raw_qs = raw_qs.decode("latin-1")
    query_sid = clean_sid((parse_qs(raw_qs).get("sid") or [None])[0])
    if query_sid:
        return query_sid
    cookie = ""
    for key, value in scope.get("headers") or []:
        if key.lower() == b"cookie":
            cookie = value.decode("latin-1")
            break
    for part in cookie.split(";"):
        name, _, raw = part.strip().partition("=")
        if name == COOKIE:
            return clean_sid(raw)
    return None


def cookie_bytes(sid):
    return f"{COOKIE}={sid}; HttpOnly; SameSite=Lax; Path=/".encode("ascii")


def state_body(session):
    return {
        "sid": session.sid,
        "mode": "demo",
        "simulated": True,
        "seeded": bool(session.seeded),
    }


def reject_if_limited(bucket):
    if not is_demo():
        return None
    session = current_session()
    if session is None:
        return None
    if session.allow(bucket, _LIMITS[bucket]):
        return None
    return JSONResponse({"error": "slow down"}, status_code=429)


def _ago(now, minutes=0, hours=0):
    return now - timedelta(minutes=minutes, hours=hours)


def _decision(text, result, when, repeat_count=None):
    entry = {
        "at": when.strftime("%I:%M %p").lstrip("0"),
        "transcript": text,
        "action": result["action"],
        "reply_id": result.get("reply_id", ""),
        "reason": result.get("reason", ""),
        "trigger_words": list(result.get("trigger_words") or []),
        "confidence": result.get("confidence", 0.0),
        "latency_ms": result.get("latency_ms", 0),
        "source": result.get("source", ""),
        "ignored": result.get("ignored", ""),
        "ts": when.isoformat(timespec="seconds"),
    }
    if repeat_count is not None:
        entry["repeat_count"] = repeat_count
    return entry


def seed_day(root):
    """Copy the seed and write one resolved day. Leaves no active red alert."""
    root.mkdir(parents=True, exist_ok=True)
    token = push_root(root)
    try:
        ensure_working_copy()
        if not read_family():
            members = [
                {"id": "joy", "name": "Joy", "color": "green", "photo": ""},
                {"id": "troy", "name": "Troy", "color": "green", "photo": ""},
                {"id": "donita", "name": "Donita", "color": "amber", "photo": ""},
            ]
            text = json.dumps({"members": members}, ensure_ascii=False, indent=2) + "\n"
            (root / "family.json").write_text(text, encoding="utf-8")
        (root / "safety-words.json").write_text('{"words":[]}\n', encoding="utf-8")
        now = datetime.now().astimezone()
        nanay = decide(NANAY)
        urgent = decide(URGENT_LINE)
        rows = [
            {"event": "meal_logged", "ts": _ago(now, hours=2).isoformat(timespec="seconds")},
            _decision(NANAY, nanay, _ago(now, minutes=90), repeat_count=1),
            _decision(NANAY, nanay, _ago(now, minutes=70), repeat_count=2),
            _decision(URGENT_LINE, urgent, _ago(now, minutes=40)),
            {
                "event": "urgent_reply",
                "ts": _ago(now, minutes=38).isoformat(timespec="seconds"),
                "speaker": "Joy",
            },
            _decision(NANAY, nanay, _ago(now, minutes=15), repeat_count=3),
        ]
        (root / "decisions.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )
        ack = {"active": False, "transcript": "", "reply": dict(RESOLVED)}
        (root / "urgent-ack.json").write_text(
            json.dumps(ack, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    finally:
        pop_root(token)
    return {"event": "urgent_reply", **RESOLVED}


def apply_seed(hub, reply):
    hub.alert_active = False
    hub.urgent_transcript = ""
    hub.lola_reply = reply
    hub.lola_reply_got = set()
    hub.last_event_at = ""


def wipe(session):
    root = session.root
    for child in list(root.iterdir()):
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    reply = seed_day(root)
    apply_seed(session.hub, reply)
    session.hub.generation += 1
    session.seeded = True
    session.hits = []


def _safe_name(name):
    if not isinstance(name, str) or not name or "/" in name or "\\" in name or name in (".", ".."):
        return None
    return name


def register_demo(app):
    @app.post("/demo/reset")
    async def demo_reset():
        if not is_demo():
            return JSONResponse({"error": "demo"}, status_code=404)
        session = current_session()
        if session is None:
            return JSONResponse({"error": "demo"}, status_code=404)
        blocked = reject_if_limited("write")
        if blocked is not None:
            return blocked
        wipe(session)
        return state_body(session)

    @app.get("/demo/state")
    async def demo_state():
        if not is_demo():
            return JSONResponse({"error": "demo"}, status_code=404)
        session = current_session()
        if session is None:
            return JSONResponse({"error": "demo"}, status_code=404)
        return state_body(session)

    if is_demo():
        brain_media = Path(__file__).resolve().parent / "media"

        @app.get("/media/{name}")
        async def demo_media(name: str):
            safe = _safe_name(name)
            if safe is None:
                return Response(status_code=404)
            root = current_root()
            if root is not None:
                path = (root / "media" / safe).resolve()
                if path.is_file() and root.resolve() in path.parents:
                    return FileResponse(path)
            bundled = (brain_media / safe).resolve()
            if bundled.is_file() and brain_media.resolve() in bundled.parents:
                return FileResponse(bundled)
            return Response(status_code=404)

    landing = WEB / "landing" / "index.html"
    if landing.is_file():
        @app.get("/")
        def landing_index():
            return FileResponse(landing)

    demo_index = WEB / "demo" / "index.html"
    if demo_index.is_file():
        @app.get("/demo")
        @app.get("/demo/")
        def demo_index_page():
            return FileResponse(demo_index)

        app.mount(
            "/demo",
            StaticFiles(directory=WEB / "demo", html=True),
            name="demo-pages",
        )


class DemoMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket") or not is_demo():
            await self.app(scope, receive, send)
            return
        path = scope.get("path") or ""
        method = scope.get("method") or "GET"
        create = not (scope["type"] == "http" and method == "GET" and path == "/health")
        session, _created = await STORE.attach(scope, create)
        if session is None:
            await self.app(scope, receive, send)
            return
        tokens = bind(session.root, session.hub, session)

        async def send_cookie(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                headers.append((b"set-cookie", cookie_bytes(session.sid)))
                message = {**message, "headers": headers}
            await send(message)

        try:
            if scope["type"] == "http":
                await self.app(scope, receive, send_cookie)
            else:
                await self.app(scope, receive, send)
        finally:
            unbind(tokens)
