"""blind28: validate the three author files, freeze code + model hashes, build the anonymised shuffled judge batch. Run once after the authors finish."""
import collections
import hashlib
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(HERE, "..", ".."))
MODEL_DIR = os.environ.get("AIXL_QWEN_DIR", os.path.expanduser("~/Claude/aixl-models/qwen2.5-7b-instruct-q4_k_m"))
files = ["authors/authorO_opus.jsonl", "authors/authorS_sonnet.jsonl", "authors/authorH_haiku.jsonl"]
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
print(len(rows), dict(collections.Counter(r["expected_equivalence"] for r in rows)), dict(collections.Counter(r["language"] for r in rows)))
print(dict(collections.Counter(r["family"] for r in rows)))
json.dump({os.path.basename(f): hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest() for f in files}, open(os.path.join(HERE, "MANIFEST.json"), "w"), indent=1)
code = ["aixl/semantic/__init__.py", "aixl/semantic/compare.py", "aixl/semantic/hybrid.py", "aixl/semantic/lexicon.py", "aixl/semantic/model.py", "aixl/semantic/parser.py",
       "aixl/hybrid_protocol.py", "aixl/arbiter.py", "aixl/resources/arbiter_rules_v1.txt"]
freeze = {f: hashlib.sha256(open(os.path.join(R, f), "rb").read()).hexdigest() for f in code}
json.dump(freeze, open(os.path.join(HERE, "CODE_FREEZE.json"), "w"), indent=1)
random.Random(28).shuffle(rows)
key = {}
os.makedirs(os.path.join(HERE, "judge"), exist_ok=True)
with open(os.path.join(HERE, "judge", "batch.jsonl"), "w", encoding="utf-8") as f:
    for i, r in enumerate(rows, 1):
        q = f"Q{i:03d}"
        key[q] = r["id"]
        f.write(json.dumps({"id": q, "a": r["text_a"], "b": r["text_b"]}, ensure_ascii=False) + "\n")
json.dump(key, open(os.path.join(HERE, "judge_key.json"), "w"))
print("frozen; batch", len(rows))
