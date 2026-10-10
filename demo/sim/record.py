#!/usr/bin/env python3
"""Record a simulated Sino walkthrough and compose one 1920x1080 MP4.

The hub runs in stub mode. Typed lines go through POST /listen. Caregiver taps
and Ask Sino go through the real pages. Playwright records the three screens.
ffmpeg places them on one stage, eases the camera, and keeps the honesty label
and the English subtitles fixed. Joy's clips are the files in brain/media/.
The urgent chime is a generated stand-in: the hub's chime is macOS afplay
(docs/sino/hub-chime.md), which this machine does not have.

Run from the repo root. See demo/sim/README.md.
"""

import argparse
import asyncio
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEDIA = ROOT / "brain" / "media"
LOGO = ROOT / "assets" / "brand" / "sino-logo.png"
FONT = Path("/usr/share/fonts/truetype/macos/Inter-SemiBold.ttf")
FONT_REG = Path("/usr/share/fonts/truetype/macos/Inter-Regular.ttf")

OUT_W, OUT_H = 1920, 1080
STAGE_W, STAGE_H = 3840, 2160
FPS = 30
EASE = 0.65
END_CARD_S = 4.0
LABEL = "Simulated run on seeded demo data · stub model"
REPO_URL = "https://github.com/Troy-LL/appsolutely"

NANAY = "Nasaan si Nanay?"
TV_LINE = "Nasaan si Nanay? Abangan sa susunod na kabanata!"
MEAL = "Kumain na ba ako?"
URGENT = "Hirap huminga ako."
SAFETY_WORD = "lagnat"

TAP_JS = """
(() => {
  const ring = document.createElement('div');
  ring.setAttribute('data-sim-tap', '1');
  ring.style.cssText = [
    'position:fixed', 'left:0', 'top:0', 'width:48px', 'height:48px',
    'margin:-24px 0 0 -24px', 'border:3px solid #e9a83a', 'border-radius:50%',
    'box-shadow:0 0 0 6px rgba(233,168,58,0.35)', 'background:rgba(233,168,58,0.28)',
    'pointer-events:none', 'z-index:2147483647', 'opacity:0', 'transform:scale(0.3)',
  ].join(';');
  document.documentElement.appendChild(ring);
  const show = (x, y) => {
    ring.style.transition = 'none';
    ring.style.left = x + 'px';
    ring.style.top = y + 'px';
    ring.style.opacity = '1';
    ring.style.transform = 'scale(0.35)';
    requestAnimationFrame(() => requestAnimationFrame(() => {
      ring.style.transition = 'transform .5s ease-out, opacity .6s ease-out';
      ring.style.transform = 'scale(1.25)';
      ring.style.opacity = '0';
    }));
  };
  document.addEventListener('pointerdown', (e) => show(e.clientX, e.clientY), true);
})();
"""


def media_seconds(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        text=True,
    )
    return float(out.strip())


def free_port(start=8000):
    for port in range(start, start + 20):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("no free port from 8000")


def wait_health(port, timeout=20):
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{port}/health"
    last = "no response"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as res:
                return json.loads(res.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = str(exc)
            time.sleep(0.25)
    raise RuntimeError(f"hub did not answer /health ({last})")


def post_listen(port, text):
    body = json.dumps({"mode": "typed", "text": text}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/listen",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as res:
        if res.status != 202:
            raise RuntimeError(f"/listen returned {res.status}")


def start_hub(port, work):
    safety = work / "safety-words.json"
    safety.write_text('{"words":[]}\n', encoding="utf-8")
    env = {
        **os.environ,
        "SINO_MODEL": "stub",
        "OFFLINE_PROBE": "http://127.0.0.1:9",
        "SINO_LOG": str(work / "decisions.jsonl"),
        "SINO_SAFETY_WORDS": str(safety),
        "CHIME": "0",
        "PORT": str(port),
        "HOST": "127.0.0.1",
    }
    log = open(work / "hub.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "brain/server.py"],
        cwd=ROOT,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
    )
    proc._log = log
    return proc


def stop_hub(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    proc._log.close()


class Timeline:
    def __init__(self):
        self.t0 = None
        self.shots = []
        self.audio = []
        self.notes = {}

    def start(self):
        self.t0 = time.perf_counter()
        return 0.0

    def now(self):
        return time.perf_counter() - self.t0

    def shot(self, target, caption, ease=EASE):
        t = 0.0 if not self.shots else self.now()
        if self.shots and t < self.shots[-1]["t"] + self.shots[-1]["ease"]:
            ease = min(ease, 0.5)
        self.shots.append({"t": round(t, 3), "target": target, "ease": ease, "caption": caption})
        print(f"  {t:6.2f}s  {target:6}  {caption}")
        return t

    def sound(self, kind):
        t = self.now()
        self.audio.append({"t": round(t, 3), "kind": kind})
        print(f"  {t:6.2f}s  audio  {kind}")


def smooth_expr(shots, key, fps=FPS):
    """Nested smoothstep. `on` is zoompan's output frame, so time is on/fps."""
    expr = f"{shots[-1][key]:.4f}"
    for i in range(len(shots) - 1, 0, -1):
        t0 = shots[i]["t"]
        ease = max(shots[i]["ease"], 0.05)
        t1 = t0 + ease
        v0 = shots[i - 1][key]
        v1 = shots[i][key]
        u = f"clip((on/{fps}-{t0:.3f})/{ease:.3f},0,1)"
        stepped = f"({u})*({u})*(3-2*({u}))"
        eased = f"({v0:.4f})+(({v1:.4f})-({v0:.4f}))*({stepped})"
        expr = f"if(lt(on/{fps},{t0:.3f}),{v0:.4f},if(lt(on/{fps},{t1:.3f}),{eased},{expr}))"
    return expr


def stage_layout():
    """Where each screen sits on the 3840x2160 stage. Sizes keep the screen's aspect."""
    bezel = 16
    ipad_h, ipad_w = 1880, 1880 * 820 // 1180
    ipad_w -= ipad_w % 2
    phone_h, phone_w = 1840, 1840 * 390 // 844
    phone_w -= phone_w % 2
    back_w, back_h = 1240, 1240 * 900 // 1440
    back_h -= back_h % 2
    ipad = {"x": 56, "y": 150, "w": ipad_w, "h": ipad_h, "sw": ipad_w + bezel * 2, "sh": ipad_h + bezel * 2}
    phone = {
        "x": STAGE_W - 56 - phone_w - bezel * 2,
        "y": 160,
        "w": phone_w,
        "h": phone_h,
        "sw": phone_w + bezel * 2,
        "sh": phone_h + bezel * 2,
    }
    gap_l = ipad["x"] + ipad["sw"] + 32
    gap_r = phone["x"] - 32
    back = {
        "w": back_w,
        "h": back_h,
        "sw": back_w + bezel * 2,
        "sh": back_h + bezel * 2,
    }
    back["x"] = gap_l + max(0, (gap_r - gap_l - back["sw"]) // 2)
    back["y"] = (STAGE_H - back["sh"]) // 2
    return {"ipad": ipad, "phone": phone, "back": back, "bezel": bezel}


def camera_targets(layout):
    def center(box):
        return box["x"] + box["sw"] / 2, box["y"] + box["sh"] / 2

    ipad_c = center(layout["ipad"])
    phone_c = center(layout["phone"])
    back = layout["back"]
    z_back = 2.85
    view_h = STAGE_H / z_back
    # Bias up so the TV counter and the newest row stay in frame.
    back_cy = back["y"] + min(back["sh"], view_h) / 2
    return {
        "wide": {"z": 1.0, "cx": STAGE_W / 2, "cy": STAGE_H / 2},
        # 2.05 keeps Joy's frame large and leaves the reply line above the subtitle.
        "ipad": {"z": 2.05, "cx": ipad_c[0], "cy": ipad_c[1]},
        "phone": {"z": 2.7, "cx": phone_c[0], "cy": phone_c[1]},
        "chip": {"z": 2.9, "cx": phone_c[0], "cy": phone_c[1]},
        "back": {"z": z_back, "cx": back["x"] + back["sw"] / 2, "cy": back_cy},
    }


def apply_targets(shots, targets):
    out = []
    for shot in shots:
        aim = targets[shot["target"]]
        out.append({**shot, "z": aim["z"], "cx": aim["cx"], "cy": aim["cy"]})
    return out


def filter_path(path):
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace(",", "\\,")


def write_graph(path, layout, shots, audio, duration, font, bed_index):
    b = layout["bezel"]
    z = smooth_expr(shots, "z")
    cx = smooth_expr(shots, "cx")
    cy = smooth_expr(shots, "cy")
    x_expr = f"max(0,min(in_w-in_w/zoom,({cx})-in_w/zoom/2))"
    y_expr = f"max(0,min(in_h-in_h/zoom,({cy})-in_h/zoom/2))"
    lines = []
    # Pages are recorded at the viewport. Older takes put that picture in the
    # top-left of a larger frame, so crop the viewport out before scaling.
    content = {"ipad": (820, 1180), "phone": (390, 844), "back": (1440, 900)}
    for name, index in (("ipad", 0), ("phone", 1), ("back", 2)):
        box = layout[name]
        cw, ch = content[name]
        lines.append(
            f"[{index}:v]crop={cw}:{ch}:0:0,fps={FPS},scale={box['w']}:{box['h']}:flags=lanczos,"
            f"pad={box['sw']}:{box['sh']}:{b}:{b}:0x2B2420,setsar=1[{name}]"
        )
    lines.append(f"color=c=0x241C16:s={STAGE_W}x{STAGE_H}:r={FPS}:d={duration:.3f}[bg]")
    lines.append(f"[bg][ipad]overlay={layout['ipad']['x']}:{layout['ipad']['y']}:format=auto[a]")
    lines.append(f"[a][phone]overlay={layout['phone']['x']}:{layout['phone']['y']}:format=auto[b]")
    lines.append(f"[b][back]overlay={layout['back']['x']}:{layout['back']['y']}:format=auto[stage]")
    lines.append(
        f"[stage]zoompan=z='{z}':x='{x_expr}':y='{y_expr}':d=1:fps={FPS}:s={OUT_W}x{OUT_H},setsar=1[zoomed]"
    )
    font_esc = filter_path(font)
    font_reg = filter_path(FONT_REG)
    text_dir = path.parent
    draw = "[zoomed]"
    last = "zoomed"
    for i, shot in enumerate(shots):
        if not shot["caption"]:
            continue
        end = shots[i + 1]["t"] if i + 1 < len(shots) else duration
        if end - shot["t"] < 0.2:
            continue
        nxt = f"cap{i}"
        cap_file = text_dir / f"cap{i}.txt"
        cap_file.write_text(shot["caption"], encoding="utf-8")
        lines.append(
            f"{draw}drawtext=fontfile={font_esc}:textfile={filter_path(cap_file)}:fontsize=34:"
            f"fontcolor=0xF4EDE0:box=1:boxcolor=0x241C16@0.78:boxborderw=16:"
            f"x=(w-text_w)/2:y=h-78:enable=between(t\\,{shot['t']:.3f}\\,{end:.3f})[{nxt}]"
        )
        draw = f"[{nxt}]"
        last = nxt
    label_file = text_dir / "label.txt"
    label_file.write_text(LABEL, encoding="utf-8")
    lines.append(
        f"[{last}]drawtext=fontfile={font_esc}:textfile={filter_path(label_file)}:fontsize=22:"
        f"fontcolor=0xF4EDE0:box=1:boxcolor=0x2B2420@0.9:boxborderw=12:x=28:y=22[main]"
    )
    # End card is input 3 (logo). Built as its own 4s stream and concatenated.
    team_file = text_dir / "end-team.txt"
    url_file = text_dir / "end-url.txt"
    team_file.write_text("Team Appsolutely · #AppBuildersPH", encoding="utf-8")
    url_file.write_text(REPO_URL, encoding="utf-8")
    lines.append(f"color=c=0xF4EDE0:s={OUT_W}x{OUT_H}:r={FPS}:d={END_CARD_S}[paper]")
    lines.append("[3:v]scale=460:-1[logo]")
    lines.append("[paper][logo]overlay=(W-w)/2:250[card0]")
    lines.append(
        f"[card0]drawtext=fontfile={font_esc}:textfile={filter_path(team_file)}:"
        f"fontsize=48:fontcolor=0x2B2420:x=(w-text_w)/2:y=620[card1]"
    )
    lines.append(
        f"[card1]drawtext=fontfile={font_reg}:textfile={filter_path(url_file)}:"
        f"fontsize=32:fontcolor=0x2F5E4E:x=(w-text_w)/2:y=700[card2]"
    )
    lines.append(
        f"[card2]drawtext=fontfile={font_esc}:textfile={filter_path(label_file)}:fontsize=22:"
        f"fontcolor=0xF4EDE0:box=1:boxcolor=0x2B2420@0.9:boxborderw=12:x=28:y=22[card]"
    )
    lines.append("[main][card]concat=n=2:v=1:a=0[vout]")

    # Audio inputs follow the logo. The silence bed is the last input.
    lines.append(f"[{bed_index}:a]aformat=channel_layouts=stereo[bed]")
    mix = ["[bed]"]
    for n, item in enumerate(audio):
        ms = max(0, int(round(item["t"] * 1000)))
        src = 4 + n
        vol = {"nanay": 2.0, "ate": 1.6, "chime": 0.55}[item["kind"]]
        lines.append(
            f"[{src}:a]aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"adelay={ms}|{ms},volume={vol}[au{n}]"
        )
        mix.append(f"[au{n}]")
    lines.append(
        f"{''.join(mix)}amix=inputs={len(mix)}:duration=first:dropout_transition=0:normalize=0[aout]"
    )
    path.write_text(";\n".join(lines) + "\n", encoding="utf-8")


def make_chime(path):
    """Short stand-in for the hub Glass alarm and the phone's two-note. Not afplay."""
    graph = (
        "[0]atrim=0:0.9,afade=t=in:st=0:d=0.01,afade=t=out:st=0.12:d=0.16,volume=0.8[a];"
        "[1]atrim=0:0.9,afade=t=in:st=0:d=0.01,afade=t=out:st=0.12:d=0.18,volume=0.7,adelay=180|180[b];"
        "[2]atrim=0:0.9,afade=t=in:st=0:d=0.01,afade=t=out:st=0.16:d=0.22,volume=0.65,adelay=420|420[c];"
        "[a][b][c]amix=inputs=3:duration=longest:normalize=0"
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", "sine=frequency=880:duration=0.9:sample_rate=44100",
            "-f", "lavfi", "-i", "sine=frequency=660:duration=0.9:sample_rate=44100",
            "-f", "lavfi", "-i", "sine=frequency=1318:duration=0.9:sample_rate=44100",
            "-filter_complex", graph,
            "-t", "0.9",
            str(path),
        ],
        check=True,
    )


def compose(out_dir, marks):
    layout = stage_layout()
    shots = apply_targets(marks["shots"], camera_targets(layout))
    duration = marks["duration"]
    audio = marks["audio"]
    graph = out_dir / "graph.txt"
    chime = out_dir / "chime-standin.wav"
    make_chime(chime)
    write_graph(graph, layout, shots, audio, duration, FONT, bed_index=4 + len(audio))
    total = duration + END_CARD_S
    bed = out_dir / "bed.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", f"{total:.3f}",
         "-i", "anullsrc=r=44100:cl=stereo", str(bed)],
        check=True,
    )
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for key in ("lola", "caregiver", "backstage"):
        cmd += ["-ss", f"{marks['offsets'][key]:.3f}", "-t", f"{duration:.3f}", "-i", str(out_dir / f"{key}.webm")]
    cmd += ["-i", str(LOGO)]
    for item in audio:
        src = {"nanay": MEDIA / "nasaan-si-nanay-reply.m4a", "ate": MEDIA / "meal-check-ate-reply.m4a", "chime": chime}[item["kind"]]
        cmd += ["-i", str(src)]
    cmd += ["-i", str(bed), "-filter_complex_script", str(graph), "-map", "[vout]", "-map", "[aout]"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26", "-preset", "veryfast", "-r", str(FPS)]
    cmd += ["-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out_dir / "sino-sim.mp4")]
    print("composing", " ".join(cmd[:8]), "...")
    subprocess.run(cmd, check=True)
    return out_dir / "sino-sim.mp4"


async def center(page, selector):
    await page.locator(selector).first.evaluate("el => el.scrollIntoView({block:'center', inline:'nearest'})")


async def wait_answer(page):
    await page.wait_for_function(
        "() => document.querySelector('#answer')?.getAttribute('aria-hidden') === 'false'",
        timeout=8000,
    )


async def record(port, out_dir):
    from playwright.async_api import async_playwright

    base = f"http://127.0.0.1:{port}"
    nanay_s = media_seconds(MEDIA / "nasaan-si-nanay-reply.m4a")
    ate_s = media_seconds(MEDIA / "meal-check-ate-reply.m4a")
    tl = Timeline()
    offsets = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--autoplay-policy=no-user-gesture-required"],
        )
        screens = {
            # Video size matches the viewport. A larger size leaves the page in the
        # corner and fills the rest with empty frames (Playwright does not scale up).
        "lola": {"viewport": {"width": 820, "height": 1180}, "device_scale_factor": 2,
                     "record_video_size": {"width": 820, "height": 1180}},
            "caregiver": {"viewport": {"width": 390, "height": 844}, "device_scale_factor": 3,
                          "record_video_size": {"width": 390, "height": 844}},
            "backstage": {"viewport": {"width": 1440, "height": 900}, "device_scale_factor": 1,
                          "record_video_size": {"width": 1440, "height": 900}},
        }
        contexts = {}
        pages = {}
        created = {}
        for name, opts in screens.items():
            ctx = await browser.new_context(
                viewport=opts["viewport"],
                device_scale_factor=opts["device_scale_factor"],
                record_video_dir=str(out_dir / "raw"),
                record_video_size=opts["record_video_size"],
                timezone_id="Asia/Manila",
                locale="fil-PH",
                color_scheme="light",
            )
            await ctx.add_init_script(TAP_JS)
            page = await ctx.new_page()
            created[name] = time.perf_counter()
            contexts[name] = ctx
            pages[name] = page

        lola, care, back = pages["lola"], pages["caregiver"], pages["backstage"]
        await asyncio.gather(
            lola.goto(f"{base}/lola/?feed=hub&mic=off&lang=tl", wait_until="domcontentloaded"),
            care.goto(f"{base}/caregiver/?feed=hub", wait_until="domcontentloaded"),
            back.goto(f"{base}/backstage/?feed=hub", wait_until="domcontentloaded"),
        )
        await lola.locator("#start-btn").click()
        await lola.wait_for_function("() => document.querySelector('#start-sheet').classList.contains('gone')")
        await care.locator(".sn-monitor button").click()
        await care.locator(".sn-salabar b").wait_for()
        await back.locator("#offline").wait_for(state="visible")
        await back.wait_for_function(
            "() => document.querySelector('[data-part=\"server\"] .node')?.textContent === '✓'"
        )
        sala = (await care.locator(".sn-salabar b").inner_text()).strip()
        tl.notes["sala"] = sala
        print("caregiver sala line:", sala)
        await asyncio.sleep(0.4)

        tl.start()
        for name in created:
            offsets[name] = tl.t0 - created[name]
        tl.shot("wide", "Lola's clock. The caregiver's home. The hub is offline.", ease=0)
        await asyncio.sleep(8.0)

        post_listen(port, NANAY)
        await wait_answer(lola)
        tl.sound("nanay")
        tl.shot("ipad", "Where is Mother? Joy's recording answers.")
        await asyncio.sleep(nanay_s + 0.6)
        tl.shot("wide", "")
        await asyncio.sleep(1.0)

        post_listen(port, TV_LINE)
        await back.wait_for_function(
            "() => (document.querySelector('#ignored-tag')?.textContent || '').includes('TV lines ignored: 1')",
            timeout=8000,
        )
        tl.shot("back", "A TV line. Sino stays quiet, and the counter goes up.")
        await asyncio.sleep(3.6)
        tl.shot("wide", "")
        await asyncio.sleep(0.9)

        tl.shot("phone", "The caregiver logs that Lola has eaten.", ease=0.55)
        await asyncio.sleep(0.7)
        await care.locator("button.sn-ate").click()
        await care.get_by_text("Naitala sa hub").wait_for(timeout=5000)
        await asyncio.sleep(0.8)
        post_listen(port, MEAL)
        await wait_answer(lola)
        tl.sound("ate")
        tl.shot("ipad", "Have I eaten? Joy's clip plays.")
        await asyncio.sleep(ate_s + 0.5)
        tl.shot("wide", "")
        await asyncio.sleep(0.8)

        post_listen(port, URGENT)
        await care.locator(".sn-urgent").wait_for(timeout=8000)
        await center(care, ".sn-urgent")
        await asyncio.sleep(0.35)
        tl.sound("chime")
        tl.shot("phone", "I'm having trouble breathing. Red card on the phone.")
        await asyncio.sleep(2.4)
        await care.locator(".sn-urgent").get_by_role("button", name=re.compile("Papunta na ako")).click()
        tl.shot("ipad", "On my way. Lola's iPad stays calm and shows it.", ease=0.75)
        await lola.wait_for_function(
            "() => (document.querySelector('#answer .reply')?.textContent || '').includes('Papunta')",
            timeout=8000,
        )
        await asyncio.sleep(3.4)
        tl.shot("wide", "")
        await asyncio.sleep(0.7)

        tl.shot("phone", "Today's activity.", ease=0.55)
        await asyncio.sleep(0.7)
        await care.locator(".sn-tab", has_text="Talaan").click()
        await asyncio.sleep(2.2)
        tl.shot("wide", "", ease=0.55)
        await asyncio.sleep(0.55)

        tl.shot("phone", "The day's receipt.", ease=0.55)
        await asyncio.sleep(0.7)
        await care.get_by_role("button", name=re.compile("Resibo")).click()
        await asyncio.sleep(2.3)
        tl.shot("wide", "", ease=0.55)
        await asyncio.sleep(0.55)

        tl.shot("phone", "What Sino knows.", ease=0.55)
        await asyncio.sleep(0.65)
        await care.locator(".sn-tab", has_text="Alam ni Sino").click()
        await care.locator(".sn-word-add").wait_for()
        await center(care, ".sn-word-add")
        await asyncio.sleep(0.8)
        tl.shot("chip", "Adding a safety word.", ease=0.6)
        await asyncio.sleep(0.7)
        await care.locator(".sn-word-add").click()
        await care.locator("#add-word").click()
        await care.locator("#add-word").type(SAFETY_WORD, delay=110)
        await asyncio.sleep(0.35)
        await care.locator(".sn-sheet").get_by_role("button", name=re.compile("I-save")).click()
        await care.locator(".sn-word-tag", has_text=SAFETY_WORD).wait_for(timeout=8000)
        await asyncio.sleep(1.6)
        tl.shot("wide", "", ease=0.6)
        await asyncio.sleep(0.55)

        tl.shot("phone", "How is Lola?", ease=0.55)
        await asyncio.sleep(0.65)
        await care.locator(".sn-tab", has_text="Sino AI").click()
        await asyncio.sleep(0.7)
        await care.get_by_role("button", name=re.compile(r"Kamusta si Lola\?")).click()
        await care.wait_for_function(
            """() => [...document.querySelectorAll('.sn-msg--sino')].some(
                (b) => !b.querySelector('.sn-msg__thinking') && (b.innerText || '').trim().length > 8)""",
            timeout=12000,
        )
        await asyncio.sleep(2.8)
        tl.shot("wide", "", ease=0.55)
        await asyncio.sleep(0.6)

        tl.shot("back", "Every decision: the line, the rule, then the action.", ease=0.7)
        await asyncio.sleep(4.6)
        duration = tl.now()
        await asyncio.sleep(0.3)

        saved = {}
        for name, page in pages.items():
            video = page.video
            await contexts[name].close()
            src = await video.path()
            dest = out_dir / f"{name}.webm"
            shutil.move(src, dest)
            saved[name] = dest
        await browser.close()

    marks = {
        "duration": round(duration, 3),
        "offsets": {k: round(v, 3) for k, v in offsets.items()},
        "shots": tl.shots,
        "audio": tl.audio,
        "notes": tl.notes,
    }
    (out_dir / "marks.json").write_text(json.dumps(marks, indent=2), encoding="utf-8")
    print(f"scenario {duration:.1f}s")
    return marks


def main():
    parser = argparse.ArgumentParser(description="Record the simulated Sino demo and compose an MP4.")
    parser.add_argument("--out", type=Path, default=ROOT / "demo" / "sim" / "out")
    parser.add_argument("--compose-only", action="store_true")
    args = parser.parse_args()
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if not (ROOT / "web" / "caregiver" / "dist" / "index.html").is_file():
        sys.exit("web/caregiver/dist is missing. From web/caregiver: npm ci && npm run build")
    if not FONT.is_file():
        sys.exit(f"subtitle font missing: {FONT}")
    if args.compose_only:
        marks = json.loads((out_dir / "marks.json").read_text(encoding="utf-8"))
        mp4 = compose(out_dir, marks)
    else:
        port = free_port()
        work = Path(tempfile.mkdtemp(prefix="sino-sim-"))
        proc = start_hub(port, work)
        try:
            health = wait_health(port)
            print("health", {k: health.get(k) for k in ("model", "offline", "server", "whisper", "ollama", "mic")})
            if health.get("offline") is not True:
                sys.exit("OFFLINE badge would be hidden. OFFLINE_PROBE did not fail.")
            marks = asyncio.run(record(port, out_dir))
        finally:
            stop_hub(proc)
            shutil.rmtree(work, ignore_errors=True)
        mp4 = compose(out_dir, marks)
    size = mp4.stat().st_size
    print(f"wrote {mp4} ({size / 1e6:.1f} MB)")
    if size > 50 * 1024 * 1024:
        sys.exit("mp4 is over 50 MB")


if __name__ == "__main__":
    main()
