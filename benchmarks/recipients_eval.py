"""handoff_check(required=[RECIPIENT]) on a fresh independent set (data/recipients/out.jsonl: a model wrote 160 short instructions, half with a recipient — lowercase and capitalised names,
departments, roles, tools — and half WITHOUT one but with date/time/quantity/place/infinitive decoys after prepositions). Bars FIXED BEFORE reading: recipient detected on >= 80 % of the
has-recipient lines AND `present` claimed on <= 15 % of the no-recipient lines. Baseline: NAME alone (what the contract could see before).   python -m benchmarks.recipients_eval"""
import collections
import json
import os

from aixl.handoff import present_kinds
from aixl.invariants import extract

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    rows = [json.loads(line) for line in open(os.path.join(ROOT, "data", "recipients", "out.jsonl"), encoding="utf-8")]
    pos = [r for r in rows if r["has_recipient"]]
    neg = [r for r in rows if not r["has_recipient"]]
    cap = lambda t: t != t.lower()                                           # noqa: E731
    arms = {"NAME only (before)": lambda t: bool(extract(t).get("NAME")), "RECIPIENT (now)": lambda t: "RECIPIENT" in present_kinds(t)}
    print(f"{len(rows)} lines: {len(pos)} with recipient, {len(neg)} without")
    for n, f in arms.items():
        tp = sum(f(r["text"]) for r in pos)
        fp = sum(f(r["text"]) for r in neg)
        lo = [r for r in pos if not cap(r["text"])]
        lo_tp = sum(f(r["text"]) for r in lo)
        by = collections.defaultdict(lambda: [0, 0])
        for r in pos:
            by[r["lang"]][1] += 1; by[r["lang"]][0] += f(r["text"])
        ok = tp / len(pos) >= 0.80 and fp / len(neg) <= 0.15
        print(f"{n:<22} detected {tp}/{len(pos)} = {100 * tp / len(pos):.0f}%  (lowercase-only lines {lo_tp}/{len(lo)})  false 'present' {fp}/{len(neg)} = {100 * fp / len(neg):.0f}%  "
              f"per lang {dict((k, f'{v[0]}/{v[1]}') for k, v in sorted(by.items()))}  {'ACCEPT' if ok else 'reject'}")
    f = arms["RECIPIENT (now)"]
    print("\nmissed recipients:")
    for r in pos:
        if not f(r["text"]):
            print("  ", r["lang"], "|", r["text"], "|", r.get("recipient"))
    print("\nfalse 'present':")
    for r in neg:
        if f(r["text"]):
            print("  ", r["lang"], "|", r["text"])


if __name__ == "__main__":
    main()
