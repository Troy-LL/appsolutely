"""QA end to end: a test copy of the hub server (real Qwen, no chime, no mic, separate log).

Typed lines go in through POST /listen; what each screen receives on /ws is checked.
Usage: e2e_eval.py <out.json>
"""
import asyncio
import json
import os
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

REPO = Path("/Users/guest1/Desktop/Guest D/appsolutely")
QA = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "brain"))
os.environ.update({"SINO_MODEL": "ollama", "SINO_LOG": str(QA / "e2e-decisions.jsonl"),
                   "OFFLINE_PROBE": "http://127.0.0.1:9", "HUB_URL": "http://127.0.0.1:11434"})
os.environ.pop("CERT", None)
os.environ.pop("KEY", None)
(QA / "e2e-decisions.jsonl").unlink(missing_ok=True)

import uvicorn  # noqa: E402
import websockets  # noqa: E402

import server  # noqa: E402  (main() is never called: mic and chime stay off)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


PORT = free_port()
threading.Thread(target=uvicorn.Server(uvicorn.Config(server.app, host="127.0.0.1", port=PORT,
                                                      log_level="warning")).run, daemon=True).start()
for _ in range(50):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1)
        break
    except OSError:
        time.sleep(0.2)


def post(text):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/listen", method="POST",
                                 data=json.dumps({"mode": "typed", "text": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=5).status


async def collect(socks, seconds):
    """Everything each screen receives during `seconds`, with arrival time."""
    got = {name: [] for name in socks}

    async def reader(name, ws):
        try:
            while True:
                msg = json.loads(await ws.recv())
                got[name].append((time.monotonic(), msg))
        except Exception:
            return
    tasks = [asyncio.create_task(reader(n, w)) for n, w in socks.items()]
    await asyncio.sleep(seconds)
    for t in tasks:
        t.cancel()
    return got


async def scenario(name, lines, wait, gap=0.0):
    socks = {}
    for screen in ("lola", "caregiver", "backstage"):
        ws = await websockets.connect(f"ws://127.0.0.1:{PORT}/ws?screen={screen}")
        await ws.recv()  # health on connect
        socks[screen] = ws
    started = time.monotonic()
    reader = asyncio.create_task(collect(socks, wait))
    for line in lines:
        await asyncio.to_thread(post, line)
        if gap:
            await asyncio.sleep(gap)
    got = await reader
    for ws in socks.values():
        await ws.close()
    events = {s: [(round((t - started) * 1000), m["event"], m.get("action") or m.get("transcript", ""))
                  for t, m in msgs] for s, msgs in got.items()}
    raw = {s: [m for _, m in msgs] for s, msgs in got.items()}
    print(f"\n== {name}: {lines}")
    for s, ev in events.items():
        print(f"  {s:9}: {ev}")
    return {"name": name, "lines": lines, "events": events, "raw": raw}


async def main():
    out = []
    out.append(await scenario("E1 known question -> family reply on iPad", ["Nasaan si Nanay?"], 3))
    out.append(await scenario("E2 urgent -> red card on caregiver phone", ["Hindi ako makahinga"], 3))
    out.append(await scenario("E3 new question (Qwen) -> quiet card, repeats grouped",
                              ["Nasaan yung aso?", "Nasaan yung aso?"], 9, gap=4.5))
    out.append(await scenario("E4 TV line -> silent, backstage only", ["Abangan ang susunod na kabanata"], 3))
    out.append(await scenario("E5 urgent said while Qwen is busy, then another line",
                              ["Nasaan yung susi?", "Saklolo", "Nasaan si Joy?"], 8, gap=0.15))
    os.environ["HUB_URL"] = "http://127.0.0.1:9"  # nothing listens there: Ollama is "down"
    out.append(await scenario("E6 Qwen down -> caregiver, not silent", ["Nasaan yung susi?"], 3))
    # A fake Ollama that accepts the connection and never answers: the 4 s timeout must fire.
    hang = socket.socket()
    hang.bind(("127.0.0.1", 0))
    hang.listen(5)
    os.environ["HUB_URL"] = f"http://127.0.0.1:{hang.getsockname()[1]}"
    out.append(await scenario("E7 Qwen hangs -> 4 s timeout -> caregiver", ["Nasaan yung susi?"], 7))
    hang.close()
    os.environ["HUB_URL"] = "http://127.0.0.1:11434"
    Path(sys.argv[1]).write_text(json.dumps(out, ensure_ascii=False, indent=1))


asyncio.run(main())
