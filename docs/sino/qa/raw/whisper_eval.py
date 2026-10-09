"""QA: replay each clip through the production listen path (minus the mic).

peak_dbfs -> whisper-server /inference -> junk_reason -> spoken -> decide() (SINO_MODEL=ollama).
Usage: whisper_eval.py <label> <whisper_url> <hint 0|1> <out.jsonl>
"""
import json
import os
import sys
import time
from pathlib import Path

REPO = Path("/Users/guest1/Desktop/Guest D/appsolutely")
sys.path.insert(0, str(REPO / "brain"))
sys.path.insert(1, str(REPO / "hub"))
os.environ["SINO_MODEL"] = "ollama"

import listen  # noqa: E402
from decide import decide, normalize  # noqa: E402

label, url, hint, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
listen.WHISPER_INFERENCE = url
os.environ["WHISPER_HINT"] = "1" if hint == "1" else "0"

QA = Path(__file__).resolve().parent
MANIFEST = REPO / "brain/tests/audio/lola/manifest.json"
clips = []
for c in json.loads(MANIFEST.read_text()):
    clips.append({"id": c["id"], "path": str(MANIFEST.parent / c["file"]), "ref": c["text"],
                  "category": c["category"], "expected": c["expected_action"], "source": "synthetic"})
# Donita's two real hub-mic recordings of "Nasaan si Nanay?" (docs/sino/hub-problems.md section 1)
for rid, p in (("r01", "~/sino/recordings/test-first.wav"), ("r02", "~/sino/recordings/nanay-donita.wav")):
    clips.append({"id": rid, "path": os.path.expanduser(p), "ref": "Nasaan si Nanay?",
                  "category": "comfort", "expected": "comfort", "source": "real (Donita, hub mic)"})
# Junk-filter probes made by make_junk.py
for jid, name in (("j01", "silence.wav"), ("j02", "room-hum.wav")):
    clips.append({"id": jid, "path": str(QA / name), "ref": "", "category": "junk",
                  "expected": "dropped", "source": "generated"})


def wer(ref, hyp):
    r, h = normalize(ref).split(), normalize(hyp).split()
    if not r:
        return 0.0 if not h else 1.0
    d = list(range(len(h) + 1))
    for i, rw in enumerate(r, 1):
        prev, d[0] = d[0], i
        for j, hw in enumerate(h, 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (rw != hw))
            prev, d[j] = d[j], cur
    return d[len(h)] / len(r)


rows = []
for c in clips:
    peak = listen.peak_dbfs(c["path"])
    text, asr_ms = "", 0
    if peak >= listen.quiet_dbfs():
        t0 = time.monotonic()
        text = listen.transcribe(c["path"])
        asr_ms = int((time.monotonic() - t0) * 1000)
    drop = listen.junk_reason(text, peak)
    if drop:
        action, source, reason, decide_ms = "dropped", "", drop, 0
    else:
        t0 = time.monotonic()
        d = decide(listen.spoken(text))
        decide_ms = int((time.monotonic() - t0) * 1000)
        action, source, reason = d["action"], d["source"], d["reason"]
    if c["category"] == "tv":
        ok = action in ("silent", "dropped")
    else:
        ok = action == c["expected"]
    row = {**c, "config": label, "transcript": text, "exact": normalize(text) == normalize(c["ref"]),
           "wer": round(wer(c["ref"], text), 3), "action": action, "source": source, "reason": reason,
           "correct": ok, "asr_ms": asr_ms, "decide_ms": decide_ms, "total_ms": asr_ms + decide_ms}
    rows.append(row)
    flag = "" if ok else "  <-- WRONG"
    print(f"{label} {c['id']:4} {c['category']:9} asr={asr_ms:5}ms dec={decide_ms:5}ms "
          f"{action:9} ({source or '-'}:{reason}) | {text!r}{flag}", flush=True)

Path(out).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
speech = [r for r in rows if r["category"] != "junk"]
print(f"SUMMARY {label}: decision right {sum(r['correct'] for r in rows)}/{len(rows)}, "
      f"exact transcript {sum(r['exact'] for r in speech)}/{len(speech)}, "
      f"mean WER {sum(r['wer'] for r in speech)/len(speech):.2f}")
