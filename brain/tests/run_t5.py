"""T5 pass/fail runner over brain/tests/cases.json.

Run from the worktree root: SINO_MODEL=stub python3 brain/tests/run_t5.py

Text gate is the default. --audio reads brain/tests/audio/lola/manifest.json.
Those clips are synthetic ElevenLabs speech from PR #18, and they are cleaner
than real elderly speech, so a pass on them is not a pass on Lola.
If WHISPER_BIN and WHISPER_MODEL are both real files, each clip is transcribed
with whisper.cpp -l tl -nt. Otherwise the manifest text is the transcript and
the row is asr=skipped.
TODO: latency (speech to reply, model path) stays unknown until a real hub run.
"""

import argparse
import json
import math
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import decide as decide_mod  # noqa: E402
from decide import decide  # noqa: E402

CASES = HERE / "cases.json"
MANIFEST = HERE / "audio" / "lola" / "manifest.json"
COMFORT_MIN_RATIO = 0.8
RED = "\033[31m"
RESET = "\033[0m"
MODES = {"": "stub", "stub": "stub", "ollama": "ollama"}
UNKNOWN = "TODO: unknown"


def run_mode():
    raw = os.environ.get("SINO_MODEL", "")
    if raw not in MODES:
        raise SystemExit(f"SINO_MODEL={raw!r} is not allowed (use stub or ollama)")
    return MODES[raw]


def is_model_path(decision):
    # source, not reason: in ollama mode Qwen writes its own reason (QA D-11).
    return decision.get("source") == "model"


def _show_ms(value):
    if isinstance(value, float) and not value.is_integer():
        return f"{value:g}"
    return str(int(value))


def _p90(values):
    ordered = sorted(values)
    rank = math.ceil(0.9 * len(ordered))
    return ordered[rank - 1]


def _transcribe(wav_path):
    bin_path = os.environ.get("WHISPER_BIN", "")
    model_path = os.environ.get("WHISPER_MODEL", "")
    if not bin_path or not model_path:
        return None, 0, "skipped"
    if not Path(bin_path).is_file() or not Path(model_path).is_file():
        return None, 0, "skipped"
    started = time.monotonic()
    proc = subprocess.run(
        [bin_path, "-m", model_path, "-l", "tl", "-nt", "-f", str(wav_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    asr_ms = int((time.monotonic() - started) * 1000)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise SystemExit(f"whisper failed on {wav_path.name}: {detail}")
    transcript = " ".join(line.strip() for line in proc.stdout.splitlines() if line.strip())
    return transcript, asr_ms, "whisper"


def _audio_row(clip):
    wav_path = MANIFEST.parent / clip["file"]
    transcript, asr_ms, asr = _transcribe(wav_path)
    if asr == "skipped":
        transcript = clip["text"]
    started = time.monotonic()
    decision = decide(transcript)
    decide_ms = int((time.monotonic() - started) * 1000)
    action = decision["action"]
    missed_urgent = clip["category"] == "urgent" and action != "urgent"
    tv_heard = clip["category"] == "tv" and action != "silent"
    return {
        "id": clip["id"],
        "category": clip["category"],
        "transcript": transcript,
        "expected_action": clip["expected_action"],
        "action": action,
        "result": "PASS" if action == clip["expected_action"] else "FAIL",
        "asr": asr,
        "asr_ms": asr_ms,
        "decide_ms": decide_ms,
        "total_ms": asr_ms + decide_ms,
        "missed_urgent": missed_urgent,
        "tv_heard": tv_heard,
    }


def _print_audio_row(row):
    line = (
        f"{row['id']} {row['category']} {row['transcript']!r} "
        f"{row['expected_action']} {row['action']} {row['result']} "
        f"asr={row['asr']} asr_ms={row['asr_ms']} decide_ms={row['decide_ms']} total_ms={row['total_ms']}"
    )
    if row["missed_urgent"] or row["tv_heard"]:
        print(f"{RED}{line}{RESET}")
        return
    print(line)


def run_audio(out_path):
    mode = run_mode()
    clips = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = [_audio_row(clip) for clip in clips]
    print(f"mode: {mode}")
    print(f"clips: {len(rows)} ({MANIFEST.relative_to(HERE.parent.parent)})")
    print()
    for row in rows:
        _print_audio_row(row)

    totals = {}
    passed = {}
    for row in rows:
        totals[row["category"]] = totals.get(row["category"], 0) + 1
        if row["result"] == "PASS":
            passed[row["category"]] = passed.get(row["category"], 0) + 1
    urgent = [row for row in rows if row["category"] == "urgent"]
    urgent_hit = sum(1 for row in urgent if row["action"] == "urgent")
    tv = [row for row in rows if row["category"] == "tv"]
    tv_silent = sum(1 for row in tv if row["action"] == "silent")
    totals_ms = [row["total_ms"] for row in rows]

    print()
    print("pass by category:")
    for category, count in totals.items():
        print(f"  {category} {passed.get(category, 0)}/{count}")
    print(f"urgent recall: {urgent_hit}/{len(urgent)}")
    print(f"TV silence rate: {tv_silent}/{len(tv)}")
    print(f"median total_ms: {_show_ms(statistics.median(totals_ms))}")
    print(f"p90 total_ms: {_show_ms(_p90(totals_ms))}")

    for row in rows:
        if row["missed_urgent"]:
            print(f"{RED}MISSED URGENT {row['id']}: {row['transcript']!r} -> {row['action']}{RESET}")
        if row["tv_heard"]:
            print(f"{RED}TV NOT SILENT {row['id']}: {row['transcript']!r} -> {row['action']}{RESET}")

    if out_path:
        dest = Path(out_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("w", encoding="utf-8") as handle:
            for row in rows:
                public = {key: value for key, value in row.items() if key not in ("missed_urgent", "tv_heard")}
                handle.write(json.dumps(public, ensure_ascii=False) + "\n")

    if urgent_hit < len(urgent) or tv_silent < len(tv):
        return 1
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", action="store_true")
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    if args.audio:
        return run_audio(args.out)
    run_text()
    return 0


def _stub_model_checks():
    probes = (
        ("m-urgent", {"action": "urgent", "confidence": 1.0, "reason": "model urgent"}, "caregiver"),
        ("m-silent", {"action": "silent", "confidence": 0.85, "reason": "model silent"}, "caregiver"),
    )
    saved = decide_mod.classify
    found = []
    try:
        for case_id, output, expected in probes:
            decide_mod.classify = lambda _text, output=output: output
            row = {"id": case_id, "bucket": "new", "text": "hello there", "expected": expected}
            found.append((row, decide("hello there")))
    finally:
        decide_mod.classify = saved
    return found


def run_text():
    mode = run_mode()
    rows = json.loads(CASES.read_text(encoding="utf-8"))
    checked = [(row, decide(row["text"])) for row in rows]
    if mode == "stub":
        checked.extend(_stub_model_checks())

    def bucket(name):
        return [(row, d) for row, d in checked if row["bucket"] == name]

    def matches(row, decision):
        # also_ok: a second right answer, e.g. chatter may be silent (README safety rule 3, QA D-12).
        if decision["action"] != row["expected"] and decision["action"] not in row.get("also_ok", ()):
            return False
        if "reply_id" in row and decision["reply_id"] != row["reply_id"]:
            return False
        if "reason" in row and decision["reason"] != row["reason"]:
            return False
        return True

    def passed(pairs):
        return sum(1 for row, decision in pairs if matches(row, decision))

    def ratio(pairs):
        return f"{passed(pairs)}/{len(pairs)}"

    urgent, comfort, tv, new = bucket("urgent"), bucket("comfort"), bucket("tv"), bucket("new")
    tv_false = [row["id"] for row, d in tv if d["action"] != "silent"]
    model_ids = [row["id"] for row, d in checked if is_model_path(d)]
    failed_ids = [row["id"] for row, decision in checked if not matches(row, decision)]

    urgent_met = passed(urgent) == len(urgent)
    comfort_met = passed(comfort) >= COMFORT_MIN_RATIO * len(comfort)
    tv_met = not tv_false
    verdict = "PENDING (latency TODO: unknown)" if all((urgent_met, comfort_met, tv_met)) else "FAIL"

    model_count = str(len(model_ids))

    print(f"mode: {mode}")
    print(f"rows: {len(rows)} ({CASES.relative_to(HERE.parent.parent)})")
    print()
    print("| Check | Result | Gate (docs/sino/mvp-plan.md) | Met |")
    print("|---|---|---|---|")
    print(f"| urgent pass/total | {ratio(urgent)} | 10/10 | {'yes' if urgent_met else 'no'} |")
    print(f"| comfort pass/total | {ratio(comfort)} | >= 8/10 | {'yes' if comfort_met else 'no'} |")
    print(f"| TV false triggers | {len(tv_false)} | 0 | {'yes' if tv_met else 'no'} |")
    print(f"| TV pass/total (expected label) | {ratio(tv)} | n/a | n/a |")
    print(f"| new pass/total | {ratio(new)} | n/a | n/a |")
    print(f"| model-path rows | {model_count} | n/a | n/a |")
    print(f"| speech to reply, known question | {UNKNOWN} | <= 3 s | {UNKNOWN} |")
    print(f"| model-path latency | {UNKNOWN} | 4 to 5 s, to verify | {UNKNOWN} |")
    print(f"| verdict | {verdict} | | |")
    print()
    print(f"TV false trigger ids: {', '.join(tv_false) or 'none'}")
    print(f"model-path ids (source model): {', '.join(model_ids) or 'none'}")
    print(f"rows where action != expected: {', '.join(failed_ids) or 'none'}")
    print("TODO: audio path not run (text only).")


if __name__ == "__main__":
    sys.exit(main())
