"""T5 pass/fail runner over brain/tests/cases.json.

Run from the worktree root: SINO_MODEL=stub python3 brain/tests/run_t5.py

Text only. TODO: audio path (no clip audio exists yet; do not synthesize it).
TODO: latency (speech to reply, model path) stays unknown until a real hub run.
"""

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from decide import decide  # noqa: E402

CASES = HERE / "cases.json"
COMFORT_MIN_RATIO = 0.8
MODES = {"": "stub", "stub": "stub", "ollama": "ollama"}
UNKNOWN = "TODO: unknown"


def run_mode():
    raw = os.environ.get("SINO_MODEL", "")
    if raw not in MODES:
        raise SystemExit(f"SINO_MODEL={raw!r} is not allowed (use stub or ollama)")
    return MODES[raw]


def is_model_path(decision):
    return "model" in decision["reason"]


def main():
    mode = run_mode()
    rows = json.loads(CASES.read_text(encoding="utf-8"))
    checked = [(row, decide(row["text"])) for row in rows]

    def bucket(name):
        return [(row, d) for row, d in checked if row["bucket"] == name]

    def passed(pairs):
        return sum(1 for row, d in pairs if d["action"] == row["expected"])

    def ratio(pairs):
        return f"{passed(pairs)}/{len(pairs)}"

    urgent, comfort, tv, new = bucket("urgent"), bucket("comfort"), bucket("tv"), bucket("new")
    tv_false = [row["id"] for row, d in tv if d["action"] != "silent"]
    model_ids = [row["id"] for row, d in checked if is_model_path(d)]
    failed_ids = [row["id"] for row, d in checked if d["action"] != row["expected"]]

    urgent_met = passed(urgent) == len(urgent)
    comfort_met = passed(comfort) >= COMFORT_MIN_RATIO * len(comfort)
    tv_met = not tv_false
    verdict = "PENDING (latency TODO: unknown)" if all((urgent_met, comfort_met, tv_met)) else "FAIL"

    model_count = str(len(model_ids)) if mode == "stub" else UNKNOWN

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
    print(f"model-path ids (reason contains 'model'): {', '.join(model_ids) or 'none'}")
    print(f"rows where action != expected: {', '.join(failed_ids) or 'none'}")
    print("TODO: audio path not run (text only).")


if __name__ == "__main__":
    main()
