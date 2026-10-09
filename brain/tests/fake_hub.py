"""Post transcript lines at a running hub and print what the screens receive.

The mic stays off. Start brain/server.py first.

    SINO_MODEL=stub .venv/bin/python brain/tests/fake_hub.py
"""

import asyncio
import json
import os
import sys
import urllib.error
import urllib.request

import websockets

LINES = (
    "Nasaan si Nanay?",
    "Nasaan si Joy?",
    "Sino ka?",
    "Gusto ko nang umuwi",
    "Masakit dibdib ko",
    "Tulong",
    "Abangan ang susunod na kabanata",
    "Salamat sa panonood",
    "Inumin ko na ba ang gamot?",
    "Nasaan yung aso?",
)
SCREENS = ("lola", "caregiver", "backstage")


def _bases():
    http = os.environ.get("HUB", "http://127.0.0.1:8000").rstrip("/")
    if http.startswith("https://"):
        ws = "wss://" + http[len("https://"):]
    elif http.startswith("http://"):
        ws = "ws://" + http[len("http://"):]
    else:
        raise SystemExit(f"HUB must be http or https, got {http}")
    return http, ws


def _post(http, text):
    req = urllib.request.Request(
        f"{http}/listen",
        data=json.dumps({"mode": "typed", "text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=3) as res:
        if res.status != 202:
            raise SystemExit(f"POST /listen returned {res.status}")


async def _drain(ws, screen):
    seen = 0
    try:
        raw = await asyncio.wait_for(ws.recv(), 2)
    except asyncio.TimeoutError:
        return seen
    print(f"{screen} {raw}")
    seen += 1
    while True:
        try:
            raw = await asyncio.wait_for(ws.recv(), 0.25)
        except asyncio.TimeoutError:
            return seen
        print(f"{screen} {raw}")
        seen += 1


async def _run():
    http, ws_base = _bases()
    sockets = []
    try:
        for screen in SCREENS:
            sockets.append((screen, await websockets.connect(f"{ws_base}/ws?screen={screen}")))
    except OSError as exc:
        raise SystemExit(f"hub not reachable at {ws_base} ({exc})") from exc
    decided = 0
    try:
        for screen, ws in sockets:
            health = await asyncio.wait_for(ws.recv(), 3)
            print(f"{screen} {health}")
        for text in LINES:
            print(f"\n> {text}")
            await asyncio.to_thread(_post, http, text)
            counts = await asyncio.gather(*(_drain(ws, screen) for screen, ws in sockets))
            decided += sum(counts)
    finally:
        for _screen, ws in sockets:
            await ws.close()
    if decided == 0:
        raise SystemExit("no events came back")
    print(f"\nlines {len(LINES)} events {decided}")


if __name__ == "__main__":
    try:
        asyncio.run(_run())
    except urllib.error.URLError as exc:
        raise SystemExit(f"hub not reachable ({exc})") from exc
