"""Always-listening (D4): the hub mic listens all the time and cuts a clip when someone speaks.

Off by default. Only brain/server.py main() calls enable_always(), and only ALWAYS_LISTEN=1
turns it on, so tests that import the app never open the mic. One ffmpeg reads MIC_DEVICE as
raw 16 kHz mono 16-bit PCM. A loudness gate (class Gate) cuts the clips; whisper-server's
Silero VAD (--vad) then checks there is real speech. Each clip goes through listen now's steps
(listen.process_clip: Whisper, junk filter, clip deleted, backstage drop or decide()).
Audio and transcripts are never printed or kept. Docs: docs/sino/architecture.md.
"""

import array
import asyncio
import collections
import contextlib
import math
import os
import sys
import tempfile
import time
import wave
from pathlib import Path

import listen  # hub/listen.py: mic device, MIC_OK health flag, process_clip, capturing

SAMPLE_RATE = 16000
FRAME_SECONDS = 0.03  # the gate looks at 30 ms of audio at a time
FRAME_BYTES = 960  # one frame: 480 samples x 2 bytes
SILENT_FRAME = bytes(FRAME_BYTES)  # exact zeros: a muted or blocked mic
LEVEL_MIN = -100.0  # an all-zero frame counts as -100 dBFS so the noise floor stays a number

# Defaults. GATE_MARGIN_DB, SILENCE_SECONDS, MAX_CLIP_SECONDS, REPLY_DEAF_SECONDS and
# CHIME_DEAF_SECONDS can be overridden by an environment variable of the same name.
GATE_MARGIN_DB = 12  # speech starts when a frame is this many dB louder than the noise floor
PRE_ROLL_SECONDS = 0.3  # audio kept from just before speech starts, so the first sound is not cut
SILENCE_SECONDS = 0.8  # this much quiet in a row ends the clip
MAX_CLIP_SECONDS = 8  # the clip is cut here even if the sound goes on
MIN_SPEECH_SECONDS = 0.5  # shorter sounds (a cough, a cup put down) are thrown away
WARMUP_SECONDS = 1.0  # after ffmpeg starts, only learn how loud the room is
REPLY_DEAF_SECONDS = 12  # after play_reply the iPad speaks the family's reply: don't transcribe it
CHIME_DEAF_SECONDS = 9  # the urgent chime is Glass x 5, about 8.25 s (hub/chime.py)
RESTART_SECONDS = 3  # wait this long before starting ffmpeg again after it stopped
READ_TIMEOUT = 5  # no audio for this long means ffmpeg is stuck: restart it
# The noise floor follows quieter frames fast and louder frames slowly (share of the gap per
# frame), so words barely move it but a fan that stays on becomes the new "quiet" in seconds.
FLOOR_FALL = 0.1
FLOOR_RISE = 0.005

ENABLED = False  # set only by enable_always() (brain/server.py main) when ALWAYS_LISTEN=1
_deaf_from = 0.0  # the current deaf window, in time.monotonic() seconds
_deaf_until = 0.0
_waiting = None  # newest finished clip (a temp WAV path) not processed yet
_ready = None  # asyncio.Event, set when _waiting holds a clip


def frame_dbfs(frame):
    """Loudness (RMS) of 16-bit little-endian PCM in dBFS: 0 is full scale, -inf is all zeros."""
    samples = array.array("h", frame)
    if sys.byteorder == "big":
        samples.byteswap()
    power = sum(s * s for s in samples) / len(samples) if samples else 0
    return 10 * math.log10(power / 32768**2) if power else float("-inf")


def _frames(seconds):
    return max(1, round(seconds / FRAME_SECONDS))


def _fixed_threshold():
    # GATE_DBFS set to a number from -100 to 0: a fixed level instead of noise floor + margin.
    try:
        value = float(os.environ.get("GATE_DBFS", ""))
    except ValueError:
        return None
    return value if -100 <= value <= 0 else None


class Gate:
    """Cuts clips out of a stream of 30 ms frames by loudness alone (no new packages).

    feed(frame) returns a finished clip as raw PCM bytes, or None.
    """

    def __init__(self):
        self.margin = listen._env_float("GATE_MARGIN_DB", GATE_MARGIN_DB, 1, 60)
        self.fixed = _fixed_threshold()
        self.silence_frames = _frames(listen._env_float("SILENCE_SECONDS", SILENCE_SECONDS, 0.1, 5))
        self.max_frames = _frames(listen._env_float("MAX_CLIP_SECONDS", MAX_CLIP_SECONDS, 1, 30))
        self.min_frames = _frames(MIN_SPEECH_SECONDS)
        self.warmup = _frames(WARMUP_SECONDS)
        self.seen = 0  # frames fed so far
        self.floor = None  # noise floor in dBFS
        # The last frames heard: the pre-roll plus the current frame.
        self.recent = collections.deque(maxlen=_frames(PRE_ROLL_SECONDS) + 1)
        self.clip = None  # frames of the clip being cut, or None while waiting for speech
        self.speech = 0  # frames from the first loud frame to the last loud one
        self.quiet = 0  # quiet frames in a row since the last loud one

    def feed(self, frame):
        level = max(frame_dbfs(frame), LEVEL_MIN)
        self.recent.append(frame)
        self.seen += 1
        if self.floor is None:
            self.floor = level
        if self.seen <= self.warmup:  # first second: only learn the room, never start a clip
            self.floor += (level - self.floor) * FLOOR_FALL
            return None
        loud = level > (self.fixed if self.fixed is not None else self.floor + self.margin)
        rate = FLOOR_FALL if level < self.floor else FLOOR_RISE
        self.floor += (level - self.floor) * rate
        if self.clip is None:
            if loud:  # speech starts: keep the pre-roll too
                self.clip, self.speech, self.quiet = list(self.recent), 1, 0
            return None
        self.clip.append(frame)
        if loud:
            self.speech += self.quiet + 1  # a short pause between words counts as speech
            self.quiet = 0
        else:
            self.quiet += 1
        if self.quiet < self.silence_frames and len(self.clip) < self.max_frames:
            return None
        clip, self.clip = self.clip, None
        return b"".join(clip) if self.speech >= self.min_frames else None


def _deafen(seconds):
    global _deaf_from, _deaf_until
    now = time.monotonic()
    if now >= _deaf_until:
        _deaf_from = now
    _deaf_until = max(_deaf_until, now + seconds)


def deafen_for_reply():
    """brain/server.py calls this when it sends play_reply: the iPad is about to speak."""
    _deafen(listen._env_float("REPLY_DEAF_SECONDS", REPLY_DEAF_SECONDS, 0, 60))


def deafen_for_chime():
    """brain/server.py calls this when it starts the urgent chime on the hub speaker."""
    _deafen(listen._env_float("CHIME_DEAF_SECONDS", CHIME_DEAF_SECONDS, 0, 60))


def deaf(start, end):
    """True when a clip from `start` to `end` (monotonic seconds) overlaps the deaf window."""
    return start < _deaf_until and end > _deaf_from


def write_wav(pcm):
    """Save raw PCM as a 16 kHz mono WAV in the system temp folder. Returns its path."""
    fd, path = tempfile.mkstemp(prefix="sino-always-", suffix=".wav")
    os.close(fd)
    with wave.open(path, "wb") as clip:
        clip.setnchannels(1)
        clip.setsampwidth(2)
        clip.setframerate(SAMPLE_RATE)
        clip.writeframes(pcm)
    return path


def offer(path):
    """Queue a clip. Newest wins: a clip still waiting is older, so it is deleted (no event)."""
    global _waiting
    if _waiting:
        Path(_waiting).unlink(missing_ok=True)
    _waiting = path
    _ready.set()


def clip_done(pcm):
    """The gate cut a clip. Drop it (nothing saved, no event) while the hub must not listen."""
    end = time.monotonic()
    start = end - len(pcm) / (SAMPLE_RATE * 2)
    if deaf(start, end) or listen.capturing():
        return
    offer(write_wav(pcm))


async def _process(hub):
    """One clip at a time through listen now's steps; the newest waiting clip goes next."""
    global _waiting
    try:
        while True:
            await _ready.wait()
            _ready.clear()
            path, _waiting = _waiting, None
            await listen.process_clip(hub, path, "always-listening")
    finally:
        if _waiting:  # server stopping: no audio is left behind
            Path(_waiting).unlink(missing_ok=True)
            _waiting = None


def capture_command():
    """ffmpeg reads the mic and writes raw 16 kHz mono 16-bit PCM to stdout until stopped."""
    return ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-f", "avfoundation",
            "-i", listen.mic_device(), "-ar", str(SAMPLE_RATE), "-ac", "1", "-f", "s16le", "-"]


async def _capture():
    """Read the mic for as long as the hub runs. If ffmpeg stops, wait and start it again."""
    warned = False  # print the failure once, not on every retry
    while True:
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *capture_command(), stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            gate, zeros = Gate(), 0
            while True:
                frame = await asyncio.wait_for(proc.stdout.readexactly(FRAME_BYTES), READ_TIMEOUT)
                # Health light "mic": false after a full second of exact zeros (muted or blocked).
                zeros = zeros + 1 if frame == SILENT_FRAME else 0
                listen.MIC_OK = zeros < _frames(1.0)
                warned = False
                pcm = gate.feed(frame)
                if pcm:
                    clip_done(pcm)
        except Exception as exc:  # ffmpeg missing, ended, or stuck (a server stop is not caught)
            listen.MIC_OK = False
            if not warned:
                print(f"always-listening: mic capture stopped ({type(exc).__name__}), "
                      f"retrying every {RESTART_SECONDS} s", file=sys.stderr)
                warned = True
        finally:
            if proc is not None and proc.returncode is None:
                with contextlib.suppress(ProcessLookupError):
                    proc.kill()
                await proc.wait()
        await asyncio.sleep(RESTART_SECONDS)


def enable_always():
    """Called once by brain/server.py main(): on only when ALWAYS_LISTEN=1."""
    global ENABLED
    ENABLED = os.environ.get("ALWAYS_LISTEN") == "1"
    print(f"always-listening: {'on' if ENABLED else 'off'}", flush=True)


def start_always(hub):
    """Called by the server lifespan: the mic reader and the clip worker, or [] when off."""
    global _ready
    if not ENABLED:
        return []
    _ready = asyncio.Event()
    return [asyncio.create_task(_capture()), asyncio.create_task(_process(hub))]
