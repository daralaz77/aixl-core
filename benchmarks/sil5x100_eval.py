"""Evaluate the rule-based pipeline on the 5x100 benchmark (benchmarks/sil5x100_gen.py).
Prediction mapping (declared up front): pair -> CONTRADICTORY if detect_contradiction; else EQUIVALENT if
compare().equivalent; else PARTIALLY_EQUIVALENT if ALL differences are 'added' (or all 'removed') and none is NEGATION
(v1.1: a mix of removed+added is a replacement, not a subset -> NOT_EQUIVALENT; v1 accepted the mix);
else NOT_EQUIVALENT. Single text -> AMBIGUOUS if detect_ambiguity, else (not a class of its own) UNAMBIGUOUS.
Also reports the ambiguity FALSE-POSITIVE rate on the unambiguous A-sides of the EQUIVALENT set.
usage: python -m benchmarks.sil5x100_eval [--out results.json] [--show N]"""
import json, os, sys, argparse, collections
from aixl import compare, detect_ambiguity, detect_contradiction

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABELS = ["EQUIVALENT", "NOT_EQUIVALENT", "PARTIALLY_EQUIVALENT", "AMBIGUOUS", "CONTRADICTORY"]


def load(lab):
    with open(os.path.join(ROOT, "data", "sil5x100", lab + ".jsonl"), encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def predict(row):
    if "b" not in row:
        return "AMBIGUOUS" if detect_ambiguity(row["a"]).ambiguous else "UNAMBIGUOUS"
    a, b = row["a"], row["b"]
    if detect_contradiction(a, b).contradiction:
        return "CONTRADICTORY"
    r = compare(a, b)
    if r.equivalent:
        return "EQUIVALENT"
    kinds = {d.kind for d in r.differences}
    if r.differences and len(kinds) == 1 and kinds <= {"added", "removed"} and all(d.field != "NEGATION" for d in r.differences):
        return "PARTIALLY_EQUIVALENT"
    return "NOT_EQUIVALENT"


INVOICE = ("invoice", "factura", "fatura")      # the one benchmark object deliberately outside the lexicon (ground truth by construction)


def silent_loss(rows):
    """Rows whose text uses an out-of-lexicon object, split into (warned, total). §66: loss must never be silent."""
    from aixl import to_semantic
    hit = [r for r in rows if any(w in (r["a"] + " " + r.get("b", "")).lower() for w in INVOICE)]
    def warned(r):
        texts = [r["a"]] + ([r["b"]] if "b" in r else [])
        return all(not any(w in t.lower() for w in INVOICE) or to_semantic(t).meta.get("unrecognized") for t in texts)
    return sum(1 for r in hit if warned(r)), len(hit)


def run():
    rows = []
    for lab in LABELS:
        for r in load(lab):
            rows.append({**r, "pred": predict(r)})
    return rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out"); ap.add_argument("--show", type=int, default=0)
    args = ap.parse_args()
    rows = run()
    conf = collections.defaultdict(collections.Counter)
    for r in rows:
        conf[r["label"]][r["pred"]] += 1
    print("per-class accuracy (class recall) and confusion:")
    tot = 0
    for lab in LABELS:
        ok = conf[lab][lab]; tot += ok
        print(f"  {lab:22s} {ok:3d}/100   " + ", ".join(f"{k}={v}" for k, v in conf[lab].most_common() if k != lab))
    print(f"overall 5-way: {tot}/500 = {tot/5:.1f}%")
    by_kind = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        by_kind[r["kind"]][1] += 1; by_kind[r["kind"]][0] += r["pred"] == r["label"]
    print("by kind:")
    for k, (ok, n) in sorted(by_kind.items()):
        print(f"  {k:28s} {ok}/{n}")
    by_lang = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        key = "mono-" + r["langs"][0] if len(set(r["langs"])) == 1 else "cross"
        by_lang[key][1] += 1; by_lang[key][0] += r["pred"] == r["label"]
    print("by language: " + ", ".join(f"{k} {ok}/{n}" for k, (ok, n) in sorted(by_lang.items())))
    eq = load("EQUIVALENT")
    fp = sum(detect_ambiguity(r["a"]).ambiguous for r in eq)
    print(f"ambiguity false positives on {len(eq)} unambiguous texts: {fp} ({fp}%)")
    w, n = silent_loss(rows)
    print(f"out-of-lexicon object (invoice/factura/fatura) reported as UNRECOGNIZED_TERMS: {w}/{n}")
    wrong = [r for r in rows if r["pred"] != r["label"]]
    print(f"misses: {len(wrong)}, of which carry a transparency warning: {sum(1 for r in wrong if silent_loss([r])[0])}")
    if args.show:
        bad = [r for r in rows if r["pred"] != r["label"]]
        for r in bad[:args.show]:
            print(r["label"], "->", r["pred"], "|", r["a"], "|", r.get("b", ""))
    if args.out:
        json.dump(rows, open(args.out, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
