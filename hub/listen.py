"""Listen now (D4): record one short clip from the hub mic, transcribe it, drop junk, decide.

POST /listen {"mode":"listen_now"} calls start_listen(hub). No VAD yet: ffmpeg records a
fixed LISTEN_SECONDS clip (default 4.5) from MIC_DEVICE (default ":0"), whisper-server on
127.0.0.1:8080 turns it into text, and the clip is deleted right away. Junk goes to
/backstage only; real speech goes through hub.submit() (throttle, decide(), events).
Transcripts and audio are never printed or saved here.
"""

import array
import asyncio
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
import uuid
import wave
from pathlib import Path

WHISPER_INFERENCE = "http://127.0.0.1:8080/inference"
WHISPER_TIMEOUT = 10
HINT_CHARS = 400
MAX_TRANSCRIPT = 2000
# Whisper's own tags for non-speech: [BLANK_AUDIO], (silence), [MUSIC], *sighs*, music notes.
MARKERS = re.compile(r"\[[^\]]*\]|\([^)]*\)|\*[^*]*\*|[♪♫]")
# Lines Whisper "hears" in TV sign-offs and silence. Lowercase, no punctuation, longest first.
JUNK_LINES = (
    "maraming salamat sa panonood",
    # Whisper small spells "panonood" as "panunod" (t02.wav, every language setting tried).
    "maraming salamat sa panunod",
    "thank you so much for watching",
    "please like and subscribe",
    "thank you for watching",
    "salamat sa panonood",
    "salamat sa panunod",
    "thanks for watching",
    "like and subscribe",
    "please subscribe",
    "subscribe",
)

# Set only by brain/server.py main(), so tests that import the app never open the microphone.
ENABLED = False
# Health light "mic": device found at start, then true after a good recording, false after a bad one.
MIC_OK = False
_task = None  # the capture in progress (one at a time); also keeps asyncio from dropping it


class MicError(RuntimeError):
    """ffmpeg could not record from the mic."""


def _env_float(name, default, low, high):
    # Settings from the environment: use the default when missing, not a number, or out of range.
    try:
        value = float(os.environ.get(name, default))
    except ValueError:
        return default
    return value if low <= value <= high else default


def listen_seconds():
    return _env_float("LISTEN_SECONDS", 4.5, 0.5, 30)


def quiet_dbfs():
    return _env_float("QUIET_DBFS", -45.0, -120, 0)


def mic_device():
    return os.environ.get("MIC_DEVICE") or ":0"


def audio_devices(listing):
    """{index: name} of the audio devices in `ffmpeg -f avfoundation -list_devices true` output."""
    devices, in_audio = {}, False
    for line in listing.splitlines():
        if "AVFoundation audio devices" in line:
            in_audio = True
        elif "AVFoundation video devices" in line:
            in_audio = False
        elif in_audio and (match := re.search(r"\[(\d+)\] (.+)$", line)):
            devices[match.group(1)] = match.group(2).strip()
    return devices


def device_listed(listing, device):
    # MIC_DEVICE is "video:audio" for avfoundation; ":0" means audio device 0, no video.
    audio = device.split(":", 1)[1] if ":" in device else ""
    devices = audio_devices(listing)
    return audio in devices or audio in devices.values() or (audio == "default" and bool(devices))


def enable_mic():
    """Called once by the hub process at start: allow recording and set the first mic status."""
    global ENABLED, MIC_OK
    ENABLED = True
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-f", "avfoundation",
           "-list_devices", "true", "-i", ""]
    try:
        # Listing devices does not record. ffmpeg prints the list on stderr and exits non-zero.
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        MIC_OK = device_listed(proc.stderr, mic_device())
    except (OSError, subprocess.TimeoutExpired):
        MIC_OK = False


def mic_ok():
    return MIC_OK


def record_clip(seconds):
    """Record `seconds` from the mic to a 16 kHz mono WAV in the system temp folder. Returns its path."""
    fd, path = tempfile.mkstemp(prefix="sino-listen-", suffix=".wav")
    os.close(fd)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
           "-f", "avfoundation", "-i", mic_device(), "-t", f"{seconds:g}",
           "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=seconds + 10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        Path(path).unlink(missing_ok=True)
        raise MicError(f"ffmpeg did not run ({type(exc).__name__})") from None
    if proc.returncode != 0 or Path(path).stat().st_size <= 44:  # 44 bytes = WAV header only
        Path(path).unlink(missing_ok=True)
        lines = proc.stderr.strip().splitlines()
        raise MicError(f"ffmpeg exited {proc.returncode}: {lines[-1] if lines else 'no audio'}")
    return path


def peak_dbfs(path):
    """Loudest sample of a 16-bit WAV in dBFS: 0 is full scale, -inf is all zeros."""
    with wave.open(str(path), "rb") as clip:
        if clip.getsampwidth() != 2:
            raise ValueError("expected a 16-bit PCM WAV")
        samples = array.array("h", clip.readframes(clip.getnframes()))
    if sys.byteorder == "big":
        samples.byteswap()  # WAV samples are little-endian
    peak = max(max(samples), -min(samples)) if samples else 0
    return 20 * math.log10(peak / 32768) if peak else float("-inf")


def _hint():
    # Known questions as Whisper's prompt (WHISPER_HINT=1 only). brain/ is on sys.path in the hub.
    try:
        from decide import load_seed
        entries = load_seed()
    except (ImportError, OSError, ValueError):
        return ""
    hint = ""
    for entry in entries:
        question = entry.get("question")
        if isinstance(question, str) and question.strip():
            if len(hint) + len(question.strip()) + 1 > HINT_CHARS:
                break
            hint = f"{hint} {question.strip()}".strip()
    return hint


def transcribe(path):
    """Send the clip to whisper-server and return its text, trimmed."""
    fields = {"response_format": "json", "temperature": "0.0"}
    if os.environ.get("WHISPER_HINT") == "1":
        fields["prompt"] = _hint()
    boundary = uuid.uuid4().hex
    body = b""
    for name, value in fields.items():
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
                 f"{value}\r\n").encode("utf-8")
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="clip.wav"'
             f"\r\nContent-Type: audio/wav\r\n\r\n").encode("utf-8")
    body += Path(path).read_bytes() + f"\r\n--{boundary}--\r\n".encode("utf-8")
    req = urllib.request.Request(WHISPER_INFERENCE, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req, timeout=WHISPER_TIMEOUT) as res:
        data = json.loads(res.read(1_000_000))
    text = data.get("text") if isinstance(data, dict) else ""
    return text.strip()[:MAX_TRANSCRIPT] if isinstance(text, str) else ""


def spoken(text):
    """The words only: Whisper's markers removed, spaces collapsed."""
    return " ".join(MARKERS.sub(" ", text or "").split())


def junk_reason(text, peak):
    """Return the locked drop_reason: too quiet, likely no speech, junk line, or "" for real speech."""
    if peak < quiet_dbfs():
        return "too quiet"
    words = spoken(text)
    if not re.search(r"[^\W_]", words):  # no letter or digit left
        return "likely no speech"
    line = " ".join(re.sub(r"[\W_]+", " ", words.lower()).split())
    for phrase in JUNK_LINES:
        line = re.sub(rf"\b{re.escape(phrase)}\b", " ", line)
    return "junk line" if not line.strip() else ""


async def listen_once(hub):
    """Record, transcribe, filter. Junk goes to backstage only; real speech goes to decide()."""
    global MIC_OK
    path, text = None, ""
    try:
        path = await asyncio.to_thread(record_clip, listen_seconds())
        peak = await asyncio.to_thread(peak_dbfs, path)
        # All zeros means the mic is muted or macOS blocked it; a real room is never that quiet.
        MIC_OK = peak > float("-inf")
        if peak >= quiet_dbfs():
            text = await asyncio.to_thread(transcribe, path)
    except MicError as exc:
        MIC_OK = False
        print(f"listen now: recording failed: {exc}", file=sys.stderr)
        return
    except Exception as exc:
        # Whisper down or a bad clip: nothing reaches Lola or the caregiver. Never print the words.
        print(f"listen now: transcription failed ({type(exc).__name__})", file=sys.stderr)
        return
    finally:
        if path:
            Path(path).unlink(missing_ok=True)  # no audio is kept
    reason = junk_reason(text, peak)
    if reason:
        await hub.send_to("backstage", {"event": "heard", "transcript": text,
                                        "dropped": True, "drop_reason": reason})
    else:
        await hub.submit(spoken(text))


def start_listen(hub):
    """POST /listen listen_now: start one capture in the background. Ignored if one is running."""
    global _task
    if not ENABLED or (_task is not None and not _task.done()):
        return
    _task = asyncio.create_task(listen_once(hub))
