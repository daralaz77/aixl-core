"""blind32: validate the three author files and freeze the code hashes (NEW = this tree, OLD = main commit 04e9574 extracted unchanged). Run once after the authors finish.
OLD: `git archive 04e9574 aixl | tar -x -C data/blind32/oldcode` (or set AIXL_OLD_CODE)."""
import collections
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
NEW = os.path.abspath(os.path.join(HERE, "..", ".."))
OLD = os.environ.get("AIXL_OLD_CODE", os.path.join(HERE, "oldcode"))
files = ["authors/authorK_opus.jsonl", "authors/authorL_sonnet.jsonl", "authors/authorM_haiku.jsonl"]
keys = {"id", "family", "language", "text_a", "text_b", "expected_equivalence", "what_differs"}
rows = []
for f in files:
    n = 0
    for line in open(os.path.join(HERE, f), encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            assert set(r) == keys, (f, set(r) ^ keys)
            rows.append(r)
            n += 1
    print(f, n)
assert len({r["id"] for r in rows}) == len(rows)
print(len(rows), dict(collections.Counter(r["expected_equivalence"] for r in rows)), dict(collections.Counter(r["language"] for r in rows)), dict(collections.Counter(r["family"] for r in rows)))
json.dump({os.path.basename(f): hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest() for f in files}, open(os.path.join(HERE, "MANIFEST.json"), "w"), indent=1)
code = ["aixl/semantic/__init__.py", "aixl/semantic/compare.py", "aixl/semantic/hybrid.py", "aixl/semantic/lexicon.py", "aixl/semantic/model.py", "aixl/semantic/parser.py",
        "aixl/hybrid_protocol.py", "aixl/arbiter.py", "aixl/resources/arbiter_rules_v1.txt"]
json.dump({"new": {f: hashlib.sha256(open(os.path.join(NEW, f), "rb").read()).hexdigest() for f in code},
           "old": {f: hashlib.sha256(open(os.path.join(OLD, f), "rb").read()).hexdigest() for f in code}}, open(os.path.join(HERE, "CODE_FREEZE.json"), "w"), indent=1)
print("frozen")
