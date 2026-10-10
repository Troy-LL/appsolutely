"""Urgent chime (D6): the hub speaker plays macOS's Glass sound 5 times when the decision is urgent.

Spec: docs/sino/hub-chime.md. brain/server.py calls play_chime() at the moment the `alert`
goes to /caregiver. /lola never gets a chime. Only brain/server.py main() calls
enable_chime(), so tests that import the app never make a sound.

Off by default (Donita, Sat ~8:05 AM): the urgent alarm now rings on the caregiver iPhone.
CHIME=1 turns this laptop chime back on as a backup.
"""

import os
import subprocess
import sys

TIMES = 5  # plays per alarm: one Glass was too easy to miss (Donita's test, Sat ~4:10 AM)
# Silence between plays. 0 = back to back, no gap (Donita, Sat ~4:20 AM).
# Glass is 1.65 s (afinfo), so one alarm is about 8.25 s (5 x 1.65).
GAP_SECONDS = 0

# One alarm is one shell line: "afplay ...; afplay ...", 5 plays one after another.
# With a gap above 0 it would add "sleep <gap>;" between plays; with 0 there is no sleep at all.
# It is built only from the constants above, never from user input. -v 1 is afplay's full scale.
_PLAY_ONCE = "afplay -v 1 /System/Library/Sounds/Glass.aiff"
_BETWEEN = f"; sleep {GAP_SECONDS}; " if GAP_SECONDS else "; "
COMMAND = ["sh", "-c", _BETWEEN.join([_PLAY_ONCE] * TIMES)]

# Set only by brain/server.py main(), the same way as enable_mic() in hub/listen.py.
ENABLED = False

# The alarm now playing (a process), or None. Used so two urgent lines don't pile up sounds.
_alarm = None


def enable_chime():
    """Called once by the hub process at start: allow the chime to play."""
    global ENABLED
    ENABLED = True


def _start(cmd):
    # Start the alarm and return at once (no waiting for the sound to end). Output is thrown away.
    return subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)


def play_chime():
    """Start one alarm without blocking. Never raises: a sound problem must not stop the alert."""
    global _alarm
    # Plays only when the hub process enabled it AND CHIME is exactly "1" (off when unset).
    if not ENABLED or os.environ.get("CHIME") != "1":
        return
    try:
        # poll() is None while the process is still running: that alarm is still sounding, skip.
        if _alarm is not None and _alarm.poll() is None:
            return
        _alarm = _start(COMMAND)
    except Exception as exc:
        print(f"chime: afplay did not start ({type(exc).__name__})", file=sys.stderr)


def stop_chime():
    """Stop the alarm if it is still playing. Never raises."""
    global _alarm
    alarm = _alarm
    _alarm = None
    if alarm is None:
        return
    try:
        if alarm.poll() is None:
            alarm.terminate()
    except Exception as exc:
        print(f"chime: could not stop ({type(exc).__name__})", file=sys.stderr)
