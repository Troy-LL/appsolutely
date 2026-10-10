# Run: ~/sino/hub-venv/bin/python web/lola/reply.test.py   (offline; needs Google Chrome; no mic, no sound)
"""Browser test for how Lola's screen plays family replies (lola.js).

It serves web/ from a tiny fake hub (FastAPI: /ws, /media, /questions) on a free
local port, opens /lola/ in headless Google Chrome (muted), sends play_reply
events over the socket and reads what the page did: which state showed, when the
audio played and ended, and whether play() was refused.

Desktop Chrome is not iPadOS: Chrome lets any element play after one tap on the
page, iPadOS only the element that was played inside the tap. Case 5 checks that
the same element is reused. Case 6 makes element play() refuse real clips (what
iPad Safari does once the unlock clip has ended) and checks the AudioContext
path still plays them with no second tap.
"""

import asyncio
import io
import json
import math
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
import wave
from pathlib import Path

import uvicorn
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
WEB = Path(__file__).resolve().parents[1]


def tone(seconds):
    """A short quiet 440 Hz WAV (16 kHz mono 16-bit), made in memory."""
    rate, buf = 16000, io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(
            int(3000 * math.sin(2 * math.pi * 440 * i / rate)).to_bytes(2, "little", signed=True)
            for i in range(int(rate * seconds))))
    return buf.getvalue()


WAVS = {"half.wav": tone(0.5), "one.wav": tone(1.0)}

# ---- fake hub: the same routes lola.js uses on the real hub ----
app = FastAPI()
screens = []  # open /ws sockets from the page


@app.get("/questions")
def questions():
    return []


@app.get("/media/{name}")
def media(name: str):
    return Response(WAVS[name], media_type="audio/wav") if name in WAVS else Response(status_code=404)


@app.websocket("/ws")
async def ws(sock: WebSocket):
    await sock.accept()
    screens.append(sock)
    try:
        while True:
            await sock.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if sock in screens:
            screens.remove(sock)


app.mount("/", StaticFiles(directory=WEB, html=True), name="web")


async def reply(reply_id, audio=""):
    """Send one play_reply event, shaped like brain/server.py sends it."""
    msg = {"event": "play_reply", "reply_id": reply_id, "photo": "", "speaker": "joy",
           "reply_audio": f"/media/{audio}" if audio else ""}
    for s in list(screens):
        await s.send_json(msg)


# ---- page hook: logs state changes and every play()/ended with a timestamp (ms) ----
HOOK = r"""
window.__log = []
const now = () => Math.round(performance.now())
const ids = new WeakMap(); let n = 0
const idOf = (el) => { if (!ids.has(el)) ids.set(el, ++n); return ids.get(el) }
const name = (el) => el.src.startsWith('data:') ? 'silent' : el.src.split('/').pop()
const play = HTMLMediaElement.prototype.play
HTMLMediaElement.prototype.play = function () {
  const el = this, src = name(el), id = idOf(el)
  // capture: runs before lola.js's own 'ended' handler, which may already set the next clip's src
  if (!el.__hooked) { el.__hooked = true; el.addEventListener('ended', () => __log.push({ t: now(), kind: 'ended', el: id, src: name(el) }), true) }
  // Case 6: iPad refuses a new src after the unlock clip. data: is the Simulan prime.
  if (window.__denyElement && !String(el.src).startsWith('data:')) {
    __log.push({ t: now(), kind: 'refused', el: id, src, err: 'NotAllowedError' })
    return Promise.reject(new DOMException('denied', 'NotAllowedError'))
  }
  __log.push({ t: now(), kind: 'play', el: id, src })
  const p = play.call(el)
  p.then(() => __log.push({ t: now(), kind: 'played', el: id, src }),
         (e) => __log.push({ t: now(), kind: 'refused', el: id, src, err: e.name }))
  return p
}
const NativeCtx = window.AudioContext || window.webkitAudioContext
if (NativeCtx) {
  function SinoCtx(...args) {
    const ctx = new NativeCtx(...args)
    const create = ctx.createBufferSource.bind(ctx)
    ctx.createBufferSource = function () {
      const node = create()
      const start = node.start.bind(node)
      node.start = function (...a) {
        const src = node.__clip || 'prime'
        __log.push({ t: now(), kind: 'played', el: 'ctx', src })
        const fn = node.onended
        node.onended = () => {
          __log.push({ t: now(), kind: 'ended', el: 'ctx', src })
          if (typeof fn === 'function') fn()
        }
        return start(...a)
      }
      return node
    }
    return ctx
  }
  window.AudioContext = SinoCtx
  if (window.webkitAudioContext) window.webkitAudioContext = SinoCtx
}
for (const kind of ['pointerdown', 'click']) {
  document.addEventListener(kind, (e) => __log.push({ t: now(), kind, pointer: e.pointerType, gesture: navigator.userActivation.isActive }), true)
}
document.addEventListener('DOMContentLoaded', () => {
  for (const state of ['waiting', 'listening', 'answer']) {
    const el = document.getElementById(state)
    new MutationObserver(() => { if (el.classList.contains('show')) __log.push({ t: now(), kind: 'show', state }) })
      .observe(el, { attributes: true, attributeFilter: ['class'] })
  }
})
"""


class Chrome:
    """One headless Chrome with a fresh profile, driven over the DevTools protocol."""

    def __init__(self, autoplay):
        self.autoplay, self.n, self.waiting = autoplay, 0, {}

    async def __aenter__(self):
        self.dir = tempfile.mkdtemp(prefix="lola-test-")
        args = [CHROME, "--headless=new", "--remote-debugging-port=0", f"--user-data-dir={self.dir}",
                "--no-first-run", "--no-default-browser-check", "--disable-background-networking", "--mute-audio",
                "--window-size=1180,820", f"--autoplay-policy={self.autoplay}", "about:blank"]
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port_file = Path(self.dir, "DevToolsActivePort")
        for _ in range(200):
            if port_file.exists() and port_file.read_text().strip():
                break
            await asyncio.sleep(0.05)
        port = int(port_file.read_text().split()[0])
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # never use a proxy for localhost
        targets = json.load(opener.open(f"http://127.0.0.1:{port}/json/list"))
        url = next(t["webSocketDebuggerUrl"] for t in targets if t["type"] == "page")
        self.ws = await websockets.connect(url, max_size=None, proxy=None)
        self.reader = asyncio.create_task(self._read())
        return self

    async def __aexit__(self, *exc):
        self.reader.cancel()
        await self.ws.close()
        self.proc.terminate()
        self.proc.wait(10)
        shutil.rmtree(self.dir, ignore_errors=True)

    async def _read(self):
        async for raw in self.ws:
            msg = json.loads(raw)
            fut = self.waiting.pop(msg.get("id"), None)
            if fut and not fut.done():
                fut.set_result(msg)

    async def send(self, method, **params):
        self.n += 1
        fut = asyncio.get_running_loop().create_future()
        self.waiting[self.n] = fut
        await self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        msg = await asyncio.wait_for(fut, 10)
        if "error" in msg:
            raise RuntimeError(f"{method}: {msg['error']}")
        return msg.get("result", {})

    async def js(self, expr):
        res = await self.send("Runtime.evaluate", expression=expr, returnByValue=True)
        if "exceptionDetails" in res:
            raise RuntimeError(f"{expr}: {res['exceptionDetails']}")
        return res["result"].get("value")

    async def open_lola(self, port, deny_element=False):
        screens.clear()
        await self.send("Page.enable")
        if deny_element:
            await self.send("Page.addScriptToEvaluateOnNewDocument", source="window.__denyElement = true")
        await self.send("Page.addScriptToEvaluateOnNewDocument", source=HOOK)
        await self.send("Page.navigate", url=f"http://127.0.0.1:{port}/lola/?feed=hub&hub=127.0.0.1:{port}&mic=off&lang=tl")
        for _ in range(200):
            if screens and await self.js("!!window.__log && document.querySelector('#waiting').classList.contains('show')"):
                return
            await asyncio.sleep(0.05)
        raise RuntimeError("Lola page did not load or did not connect to the fake hub /ws")

    async def now(self):
        return round(await self.js("performance.now()"))

    async def wait_for(self, pred, seconds):
        """Poll the page log until pred(log) is true or time runs out; return the log."""
        end = time.monotonic() + seconds
        while True:
            log = await self.js("__log")
            if pred(log) or time.monotonic() > end:
                return log
            await asyncio.sleep(0.05)

    async def click(self, x, y):
        for kind in ("mousePressed", "mouseReleased"):
            await self.send("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left", clickCount=1)

    async def tap(self, x, y):
        await self.send("Emulation.setTouchEmulationEnabled", enabled=True, maxTouchPoints=1)
        await self.send("Input.dispatchTouchEvent", type="touchStart", touchPoints=[{"x": x, "y": y}])
        await self.send("Input.dispatchTouchEvent", type="touchEnd", touchPoints=[])


def find(log, kind, after, **match):
    """First log entry of this kind at or after time `after` whose fields match."""
    for e in log:
        if e["kind"] == kind and e["t"] >= after and all(e.get(k) == v for k, v in match.items()):
            return e
    return None


failed = 0


def check(name, ok, detail=""):
    global failed
    print(f"{'ok  ' if ok else 'FAIL'} {name}{f'  ({detail})' if detail else ''}")
    failed += 0 if ok else 1


def back_after_end(log, t, src):
    """ms from the clip's end to the clock showing again, or None."""
    ended, back = find(log, "ended", t, src=src), find(log, "show", t, state="waiting")
    return back["t"] - ended["t"] if ended and back else None


def tapped_since(log, t):
    """A pointer or click at or after t: a per-reply gesture, which autoplay must not need."""
    return any(e["kind"] in ("pointerdown", "click") and e["t"] >= t for e in log)


async def cases_autoplay_on(port):
    async with Chrome("no-user-gesture-required") as c:
        await c.open_lola(port)

        # 1. A reply with audio plays, shows the answer, and is back on the clock ~1 s after the voice ends.
        t = await c.now()
        await reply("r1", "half.wav")
        log = await c.wait_for(lambda L: find(L, "show", t, state="waiting"), 6)
        ans, played = find(log, "show", t, state="answer"), find(log, "played", t, src="half.wav")
        back = find(log, "show", t, state="waiting")
        gap = back_after_end(log, t, "half.wav")
        check("1 reply with audio: answer shows and the audio plays", bool(ans and played))
        check("1 back to the clock about 1 s after the audio ends", gap is not None and 900 <= gap <= 1500,
              f"audio end -> clock {gap} ms; 0.5 s clip, answer on screen {back['t'] - ans['t'] if ans and back else None} ms")

        # 2. A reply with no recording stays on the answer for the long hold (8 s).
        t = await c.now()
        await reply("r2")
        log = await c.wait_for(lambda L: find(L, "show", t, state="waiting"), 12)
        ans, back = find(log, "show", t, state="answer"), find(log, "show", t, state="waiting")
        held = back["t"] - ans["t"] if ans and back else None
        check("2 no reply_audio: answer held about 8 s", held is not None and 7900 <= held <= 8600, f"held {held} ms")
        check("2 no reply_audio: nothing played", find(log, "play", t) is None)

        # 3. A second reply arriving while the first plays is queued and plays right after it.
        t = await c.now()
        await reply("r3", "one.wav")
        await asyncio.sleep(0.4)
        t4 = await c.now()
        await reply("r4", "half.wav")
        log = await c.wait_for(lambda L: find(L, "show", t, state="waiting"), 8)
        p1, e1 = find(log, "played", t, src="one.wav"), find(log, "ended", t, src="one.wav")
        p2 = find(log, "play", t, src="half.wav")
        gap = back_after_end(log, t, "half.wav")
        check("3 second reply arrived while the first was playing", bool(p1 and e1 and p1["t"] <= t4 < e1["t"]),
              f"first played +{p1 and p1['t'] - t} ms, second sent +{t4 - t} ms, first ended +{e1 and e1['t'] - t} ms")
        check("3 second reply plays after the first ends", bool(e1 and p2 and p2["t"] >= e1["t"] and find(log, "played", t, src="half.wav")),
              f"second play() {e1 and p2 and p2['t'] - e1['t']} ms after the first ended")
        check("3 clock only after the second clip, about 1 s after it ends", gap is not None and 900 <= gap <= 1500,
              f"audio end -> clock {gap} ms")


async def case_blocked(port, how):
    # 4. Chrome's normal policy, no gesture yet: play() is refused, the answer stays, a click/tap plays it.
    # A finger tap (touch) sends pointerdown with no user gesture yet; only the click after it has one.
    async with Chrome("document-user-activation-required") as c:
        await c.open_lola(port)
        t = await c.now()
        await reply("r5", "half.wav")
        await asyncio.sleep(2.5)
        log = await c.js("__log")
        refused = find(log, "refused", t, src="half.wav")
        check(f"4 ({how}) no gesture: play() refused", bool(refused), refused and refused["err"])
        check(f"4 ({how}) answer still up 2.5 s later (hold, not 1 s)",
              bool(find(log, "show", t, state="answer")) and find(log, "show", t, state="waiting") is None)
        tc = await c.now()
        await (c.click(20, 20) if how == "click" else c.tap(20, 20))  # on the start sheet, away from buttons
        log = await c.wait_for(lambda L: find(L, "show", tc, state="waiting"), 6)
        played = find(log, "played", tc, src="half.wav")
        gap = back_after_end(log, tc, "half.wav")
        check(f"4 ({how}) the {how} plays the held reply", bool(played),
              f"played {played['t'] - tc} ms after the {how}" if played else "")
        check(f"4 ({how}) then back to the clock about 1 s after the audio ends",
              gap is not None and 900 <= gap <= 1500, f"audio end -> clock {gap} ms")


async def case_start_unlocks(port):
    # 5. Simulan tap unlocks the one reused element; later replies play with no new gesture.
    async with Chrome("document-user-activation-required") as c:
        await c.open_lola(port)
        x, y = await c.js("(() => { const r = document.querySelector('#start-btn').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2] })()")
        await c.click(x, y)
        await asyncio.sleep(0.5)
        log = await c.js("__log")
        unlock = find(log, "play", 0, src="silent")
        check("5 Simulan plays the silent clip on the reply player", bool(unlock))
        check("5 silent unlock play() succeeded", bool(find(log, "played", 0, src="silent")))
        for rid, clip in (("r6", "half.wav"), ("r7", "one.wav")):
            t = await c.now()
            await reply(rid, clip)
            log = await c.wait_for(lambda L: find(L, "show", t, state="waiting"), 6)
            play, played = find(log, "play", t, src=clip), find(log, "played", t, src=clip)
            gap = back_after_end(log, t, clip)
            check(f"5 {rid} plays with no new gesture",
                  bool(played) and find(log, "refused", t) is None and not tapped_since(log, t))
            check(f"5 {rid} uses the same element Simulan unlocked", bool(unlock and play and play["el"] == unlock["el"]),
                  f"element #{play and play['el']} vs unlocked #{unlock and unlock['el']}")
            check(f"5 {rid} back to the clock about 1 s after the audio ends", gap is not None and 900 <= gap <= 1500,
                  f"audio end -> clock {gap} ms")


async def case_element_refused(port):
    # 6. After Simulan, element play() of a real clip is refused (iPad once the unlock clip ended).
    # The AudioContext from that tap plays it anyway. No second tap. Clock ~1 s after the voice.
    async with Chrome("document-user-activation-required") as c:
        await c.open_lola(port, deny_element=True)
        x, y = await c.js("(() => { const r = document.querySelector('#start-btn').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2] })()")
        await c.click(x, y)
        await asyncio.sleep(0.3)
        for rid, clip in (("r8", "half.wav"), ("r9", "one.wav")):
            t = await c.now()
            await reply(rid, clip)
            log = await c.wait_for(lambda L: find(L, "show", t, state="waiting"), 6)
            played, ended = find(log, "played", t, src=clip), find(log, "ended", t, src=clip)
            gap = back_after_end(log, t, clip)
            check(f"6 {rid} element play() refused", bool(find(log, "refused", t, src=clip)))
            check(f"6 {rid} context plays it with no new tap",
                  bool(played and played["el"] == "ctx" and ended and not tapped_since(log, t)))
            check(f"6 {rid} back to the clock about 1 s after the audio ends",
                  gap is not None and 900 <= gap <= 1500, f"audio end -> clock {gap} ms")


async def main():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))  # a free port, never the live hub's 8000/8080
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", lifespan="off"))
    task = asyncio.create_task(server.serve(sockets=[sock]))
    while not server.started:
        await asyncio.sleep(0.05)
    try:
        await cases_autoplay_on(port)
        await case_blocked(port, "click")
        await case_blocked(port, "tap")
        await case_start_unlocks(port)
        await case_element_refused(port)
    finally:
        server.should_exit = True
        await task
    print("all passed" if not failed else f"{failed} failed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
