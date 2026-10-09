"""The iPad's mic: Lola's screen records short clips and uploads them to POST /listen/audio.

Multipart form: `audio` (a .wav .m4a .mp4 .webm .ogg or .aac file, at most 2 MB) and an
optional `source` (one word, e.g. "ipad", used only to name the clip in log lines).
Answer: 202 with an empty body, or 400 {"error": "..."} for bad input.

The upload is saved to the system temp folder and converted by ffmpeg to the 16 kHz mono
16-bit WAV Whisper wants; the upload is deleted at once. Then the WAV takes the same steps
as listen now and always-listening (listen.process_clip: peak level, Whisper, junk filter,
WAV deleted, backstage drop or decide()). Results arrive on /ws exactly as before.
A clip that overlaps a deaf window (hub/always.py: the iPad playing a family reply, or the
hub's urgent chime) is dropped with no event. One clip is transcribed at a time; a newer
clip replaces one still waiting. Audio and transcripts are never printed or kept.
"""

import asyncio
import os
import re
import subprocess
import tempfile
import time
import wave
from pathlib import Path

from starlette.datastructures import UploadFile
from starlette.responses import JSONResponse, Response

import always  # hub/always.py: the deaf windows after play_reply and after the chime
import listen  # hub/listen.py: process_clip (Whisper, junk filter, decide)

AUDIO_EXTS = (".wav", ".m4a", ".mp4", ".webm", ".ogg", ".aac")
MAX_BYTES = 2 * 1024 * 1024  # about 8 s of audio from the iPad
MAX_SECONDS = 10  # longer audio is cut here, so a small file can't become minutes of Whisper work
FFMPEG_TIMEOUT = 10
# ffmpeg may open only these containers (the extensions above: mov covers .m4a/.mp4,
# matroska covers .webm) and only local files, so a crafted upload can't make it read
# other files or fetch URLs.
FORMATS = "wav,mov,matroska,ogg,aac"
SOURCE = re.compile(r"[a-z0-9-]{1,20}")

_waiting = None  # newest converted clip not transcribed yet: (WAV path, log label)
_worker = None  # the task that transcribes clips one at a time (kept so it isn't lost)


class BadUpload(ValueError):
    """Input we refuse. Sent back as HTTP 400 {"error": message}."""


def check_audio(filename, data):
    """The client's file name and bytes are untrusted. Returns the extension (only that is used)."""
    ext = Path(filename).suffix.lower()
    if ext not in AUDIO_EXTS:
        raise BadUpload("audio must be .wav .m4a .mp4 .webm .ogg or .aac")
    if not data:
        raise BadUpload("audio is empty")
    if len(data) > MAX_BYTES:
        raise BadUpload("audio is over 2 MB")
    return ext


def source_label(value):
    """The optional source ("ipad") names the clip in log lines. Anything else is "upload"."""
    value = value.strip().lower() if isinstance(value, str) else ""
    return value if SOURCE.fullmatch(value) else "upload"


def convert(data, ext):
    """Save the upload, convert it to a 16 kHz mono 16-bit WAV, delete the upload.

    Returns (WAV path, seconds of audio). Both files are in the system temp folder, never
    the repo. If ffmpeg can't read it, nothing is kept and BadUpload is raised.
    """
    fd, raw = tempfile.mkstemp(prefix="sino-upload-", suffix=ext)
    out_fd, path = tempfile.mkstemp(prefix="sino-upload-", suffix=".wav")
    os.close(out_fd)
    keep, seconds = False, 0.0
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        cmd = ["ffmpeg", "-v", "error", "-nostdin", "-y",
               "-protocol_whitelist", "file", "-format_whitelist", FORMATS, "-i", raw,
               "-t", str(MAX_SECONDS), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", path]
        # Output is thrown away (never printed); check=True turns a failed run into an error.
        subprocess.run(cmd, capture_output=True, timeout=FFMPEG_TIMEOUT, check=True)
        with wave.open(path, "rb") as clip:
            seconds = clip.getnframes() / clip.getframerate()
        keep = seconds > 0
    except (OSError, subprocess.SubprocessError, wave.Error, EOFError):
        pass
    finally:
        Path(raw).unlink(missing_ok=True)  # the upload itself is never kept
        if not keep:
            Path(path).unlink(missing_ok=True)
    if not keep:
        raise BadUpload("audio could not be read")
    return path, seconds


def offer(hub, path, label):
    """Queue a clip. Newest wins: a clip still waiting is older, so it is deleted (no event)."""
    global _waiting, _worker
    if _waiting:
        Path(_waiting[0]).unlink(missing_ok=True)
    _waiting = (path, label)
    if _worker is None or _worker.done():
        _worker = asyncio.create_task(_drain(hub))


async def _drain(hub):
    """Transcribe waiting clips one at a time until none is left, then stop."""
    global _waiting
    try:
        while _waiting:
            (path, label), _waiting = _waiting, None
            # hub_mic=False: a clip from the iPad says nothing about the hub's own mic light.
            await listen.process_clip(hub, path, label, hub_mic=False)
    finally:
        if _waiting:  # server stopping: no audio is left behind
            Path(_waiting[0]).unlink(missing_ok=True)
            _waiting = None


async def receive_clip(hub, request):
    """POST /listen/audio: check and convert the upload, queue it, answer 202 at once.

    Whisper runs in the background, so the iPad never waits for it.
    """
    arrived = time.monotonic()
    try:
        async with request.form() as form:
            part = form.get("audio")
            label = f"{source_label(form.get('source'))} clip"
            if not isinstance(part, UploadFile) or not part.filename:
                raise BadUpload("audio is required")
            data = await part.read(MAX_BYTES + 1)
            ext = check_audio(part.filename, data)
        path, seconds = await asyncio.to_thread(convert, data, ext)
    except BadUpload as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    except Exception:
        return JSONResponse({"error": "bad upload"}, status_code=400)  # e.g. a broken form
    # The clip holds the `seconds` just before it arrived. If any of that overlaps a deaf
    # window, the iPad mic was hearing the family reply or the chime: drop it, no event.
    if always.deaf(arrived - seconds, arrived):
        Path(path).unlink(missing_ok=True)
    else:
        offer(hub, path, label)
    return Response(status_code=202)
