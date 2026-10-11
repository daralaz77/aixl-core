"""Paraphrase attack: pairs written BEFORE running, labelled SAME / DIFFERENT by construction (data/arena/paraphrase_pairs.jsonl).
Reports the rules route's confusion matrix. Critical defect = DIFFERENT pair judged EQUIVALENT (false-same)."""
import collections
import json
import sys
from pathlib import Path

from aixl.semantic.compare import compare_texts

P = Path(__file__).resolve().parents[2] / "data" / "arena" / "paraphrase_pairs.jsonl"

def run(path=P):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    cm, bad = collections.Counter(), []
    for r in rows:
        v = compare_texts(r["a"], r["b"]).verdict
        cm[(r["expected"], v)] += 1
        if r["expected"] == "DIFFERENT" and v == "EQUIVALENT": bad.append(r)
    return cm, bad, rows

if __name__ == "__main__":
    cm, bad, rows = run()
    for k, v in sorted(cm.items()): print(k, v)
    print("FALSE-SAME (critical):", len(bad))
    for r in bad: print("  ", r["a"], "|", r["b"])
    sys.exit(1 if bad else 0)
