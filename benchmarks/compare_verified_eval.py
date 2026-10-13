"""Does `compare_verified` remove false EQUIVALENT without destroying true paraphrases?  python -m benchmarks.compare_verified_eval
Same pairs through `aixl.compare` (core) and `aixl.api.service.compare_verified`. Positive = declared EQUIVALENT. No tunable parameter exists in
compare_verified, so evaluating on already-used sets (blind13/14, other authors) is not tuning."""
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def pairs():
    import benchmarks.dataset as d
    for n, lab in (("EQ", "SAME"), ("NEG_EQ", "SAME"), ("QTY_EQ", "SAME"), ("DATE_EQ", "SAME"),
                   ("DIFF", "DIFF"), ("NEG_NEQ", "DIFF"), ("QTY_NEQ", "DIFF"), ("DATE_NEQ", "DIFF")):
        for a, b in getattr(d, n):
            yield "dev set (own author)", lab, a, b
    for r in (json.loads(x) for x in open(ROOT / "data/arena/paraphrase_pairs.jsonl", encoding="utf-8")):
        yield "arena paraphrases (own author, written first)", "SAME" if r["expected"] == "SAME" else "DIFF", r["a"], r["b"]
    for d_ in ("blind13", "blind14"):
        for f in sorted((ROOT / "data" / d_).glob("author*.jsonl")):
            for r in (json.loads(x) for x in open(f, encoding="utf-8") if x.strip()):
                e = r["expected_equivalence"]
                if e in ("EQUIVALENT", "NOT_EQUIVALENT"):
                    yield f"{d_} (OTHER authors, Opus+Sonnet)", "SAME" if e == "EQUIVALENT" else "DIFF", r["text_a"], r["text_b"]


def main():
    import aixl
    from aixl.api.service import compare_verified
    c = collections.defaultdict(collections.Counter)
    for corpus, lab, a, b in pairs():
        try:
            core = aixl.compare(a, b).equivalent
            ver = compare_verified(a, b)["equivalent"]
        except Exception:
            continue
        c[corpus][(lab, "core", core)] += 1
        c[corpus][(lab, "verified", ver)] += 1
    print(f"{'corpus':50} {'SAME n':>6} | {'recall core':>11} {'recall verif':>12} | {'DIFF n':>6} {'false-EQ core':>13} {'false-EQ verif':>14}")
    for corpus, k in c.items():
        ns, nd = sum(v for (l, m, x), v in k.items() if l == "SAME" and m == "core"), sum(v for (l, m, x), v in k.items() if l == "DIFF" and m == "core")
        rc, rv = k[("SAME", "core", True)], k[("SAME", "verified", True)]
        fc, fv = k[("DIFF", "core", True)], k[("DIFF", "verified", True)]
        print(f"{corpus:50} {ns:>6} | {rc:>4} ({100*rc/max(ns,1):4.0f}%) {rv:>5} ({100*rv/max(ns,1):4.0f}%) | {nd:>6} {fc:>4} ({100*fc/max(nd,1):4.1f}%) {fv:>5} ({100*fv/max(nd,1):4.1f}%)")


if __name__ == "__main__":
    main()
