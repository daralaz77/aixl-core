"""Conditionals and comparators: labelled pairs (data/arena/logic_pairs.jsonl, written BEFORE the vocabulary extension of 2026-10-13).
   python -m benchmarks.logic_pairs_eval            # table + defects; exit 1 if the published layers claim sameness on a DIFF pair
SAME = same meaning, DIFF = different meaning. A defect is a DIFF pair that `compare_verified` calls EQUIVALENT or the envelope calls MATCH."""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def evaluate(path=ROOT / "data" / "arena" / "logic_pairs.jsonl"):
    import aixl
    from aixl.api.service import compare_verified
    from aixl.envelope import seal, verify
    rows = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
    c, bad = collections.defaultdict(collections.Counter), []
    for r in rows:
        a, b, lab, fam = r["a"], r["b"], r["label"], r["family"]
        v, e, core = compare_verified(a, b), verify(seal(a), b), aixl.compare(a, b).equivalent
        k = c[(fam, lab)]
        k["n"] += 1; k["core_EQ"] += core; k["verified_EQ"] += v["equivalent"]; k["complete"] += bool(v.get("complete")); k["env_" + e] += 1
        if lab == "DIFF" and (v["equivalent"] or e == "MATCH"):
            bad.append((fam, a, b, v["equivalent"], e))
    return c, bad


def main():
    c, bad = evaluate()
    print(f"{'family':12} {'label':5} {'n':>3} {'complete':>8} {'core EQ':>8} {'verified EQ':>11}  envelope MATCH/MISMATCH/UNVERIFIED")
    for (fam, lab), k in sorted(c.items()):
        print(f"{fam:12} {lab:5} {k['n']:>3} {k['complete']:>8} {k['core_EQ']:>8} {k['verified_EQ']:>11}  {k['env_MATCH']}/{k['env_MISMATCH']}/{k['env_UNVERIFIED']}")
    print(f"\nDEFECTS (DIFF pair declared the same by a published layer): {len(bad)}")
    for fam, a, b, ve, e in bad[:15]:
        print(f"  [{fam}] {a!r} vs {b!r}   verified_equiv={ve} envelope={e}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
