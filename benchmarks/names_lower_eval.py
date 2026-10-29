"""Lowercase first names: why `NAME` misses them and which candidate detector is worth keeping. Independent set: data/names_lower/out.jsonl (a model wrote 60 lowercase person names
+ 60 lowercase common-noun recipients, 6 tricks, ES/EN/PT, without seeing the code). Acceptance bars FIXED BEFORE reading the data: false positives on the (non-trick) noun lines <= 5 %
AND recall on the name lines >= 50 %.   python -m benchmarks.names_lower_eval"""
import collections
import json
import os
import re

from aixl.core.lowername import by_gazetteer, by_position
from aixl.core.normalizer import strip_accents
from aixl.invariants import extract

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def known_vocab():
    d = json.load(open(os.path.join(ROOT, "aixl", "resources", "nouns_v1.json"), encoding="utf-8"))
    out = set()

    def walk(x):
        if isinstance(x, str):
            out.update(re.findall(r"[a-z]+", strip_accents(x).lower()))
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(k); walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(d)
    return frozenset(out)


def main():
    rows = [json.loads(line) for line in open(os.path.join(ROOT, "data", "names_lower", "out.jsonl"), encoding="utf-8")]
    kv = known_vocab()
    norm = lambda s: strip_accents(str(s)).lower().strip()         # noqa: E731
    det = {"current NAME": lambda t: frozenset(extract(t).get("NAME", ())),
           "gazetteer": by_gazetteer,
           "position": lambda t: by_position(t),
           "position - known words": lambda t: by_position(t, kv),
           "gazetteer + position - known": lambda t: by_gazetteer(t) | by_position(t, kv)}
    print(f"{len(rows)} lines; known-vocabulary words: {len(kv)}")
    print(f"{'detector':<30}{'recall(names)':>16}{'FP nouns (no trick)':>24}{'FP tricks':>12}   {'bars'}")
    for n, f in det.items():
        names = [r for r in rows if r["kind"] == "name"]
        nouns = [r for r in rows if r["kind"] == "noun" and not r.get("trick")]
        tricks = [r for r in rows if r["kind"] == "noun" and r.get("trick")]
        rec = sum(norm(r["target"]) in {norm(x) for x in f(r["text"])} for r in names)
        fp = sum(norm(r["target"]) in {norm(x) for x in f(r["text"])} for r in nouns)
        fpt = sum(norm(r["target"]) in {norm(x) for x in f(r["text"])} for r in tricks)
        ok = rec / len(names) >= 0.50 and fp / len(nouns) <= 0.05
        print(f"{n:<30}{rec:>6}/{len(names)} = {100 * rec / len(names):4.0f}%{fp:>10}/{len(nouns)} = {100 * fp / len(nouns):4.0f}%{fpt:>8}/{len(tricks)}   {'ACCEPT' if ok else 'reject'}")
    print("\nper language recall (gazetteer):")
    by = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r["kind"] == "name":
            by[r["lang"]][1] += 1
            by[r["lang"]][0] += norm(r["target"]) in {norm(x) for x in by_gazetteer(r["text"])}
    print("  " + "; ".join(f"{k} {v[0]}/{v[1]}" for k, v in sorted(by.items())))
    print("\nnames the gazetteer missed:", sorted(norm(r["target"]) for r in rows if r["kind"] == "name" and norm(r["target"]) not in {norm(x) for x in by_gazetteer(r["text"])}))
    print("nouns flagged by position - known words:", sorted({norm(r["target"]) for r in rows if r["kind"] == "noun" and not r.get("trick") and norm(r["target"]) in {norm(x) for x in by_position(r["text"], kv)}}))


if __name__ == "__main__":
    main()
