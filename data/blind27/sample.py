"""blind27 sampler (see PREREG.md). Deterministic, seed 27, automatic filters only. Prints counts, not texts."""
import collections
import glob
import hashlib
import json
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(HERE, "..", ".."))
rng = random.Random(27)
nw = lambda s: len(s.split())

pairs = []
# ---- PAWS-X es test
px = []
for f in sorted(glob.glob(os.path.join(HERE, "raw_pawsx", "rows_*.json")), key=lambda p: int(re.findall(r"rows_(\d+)", p)[0])):
    for x in json.load(open(f, encoding="utf-8"))["rows"]:
        r = x["row"]
        if 4 <= nw(r["sentence1"]) <= 45 and 4 <= nw(r["sentence2"]) <= 45:
            px.append(r)
for lab, name in ((1, "EQUIVALENT"), (0, "NOT_EQUIVALENT")):
    pool = [r for r in px if r["label"] == lab]
    for r in rng.sample(pool, 30):
        pairs.append(dict(src="pawsx_es", sub="pawsx_" + name.lower(), ref=f"pawsx-es-test-{r['id']}", a=r["sentence1"], b=r["sentence2"], label=name))

# ---- CondaQA dev
rows = [json.loads(l) for l in open(os.path.join(HERE, "raw", "condaqa_dev.json"), encoding="utf-8") if l.strip()]
by = collections.defaultdict(dict)
for r in rows:
    by[r["PassageID"]].setdefault(r["PassageEditID"], r["sentence1"])
split = lambda p: [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", p.strip()) if s.strip()]


def candidate(pid, edit):
    d = by[pid]
    if 0 not in d or edit not in d:
        return None
    so, se = split(d[0]), split(d[edit])
    co, ce = collections.Counter(so), collections.Counter(se)
    ao = [s for s in so if co[s] > ce[s]]
    ae = [s for s in se if ce[s] > co[s]]
    if not (1 <= len(ao) <= 3 and 1 <= len(ae) <= 3):
        return None
    a, b = " ".join(ao), " ".join(ae)
    return (a, b) if nw(a) <= 60 and nw(b) <= 60 and a != b else None


used = set()
pids = sorted(by)
for edit, n, label in ((1, 20, "EQUIVALENT"), (2, 10, "NOT_EQUIVALENT"), (3, 10, "NOT_EQUIVALENT")):
    pool = [(p, candidate(p, edit)) for p in pids if p not in used]
    pool = [(p, c) for p, c in pool if c]
    chosen = rng.sample(pool, min(n, len(pool)))
    for p, (a, b) in chosen:
        used.add(p)
        pairs.append(dict(src="condaqa", sub=f"condaqa_edit{edit}", ref=f"condaqa-dev-{p}-edit{edit}", a=a, b=b, label=label))

for i, p in enumerate(pairs):
    p["id"] = f"X{i + 1:03d}"
json.dump(pairs, open(os.path.join(HERE, "pairs.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("pairs", len(pairs), dict(collections.Counter(p["sub"] for p in pairs)), dict(collections.Counter(p["label"] for p in pairs)))

# ---- anonymised shuffled judge batch + key
order = list(range(len(pairs)))
random.Random(2727).shuffle(order)
key = {}
os.makedirs(os.path.join(HERE, "judge"), exist_ok=True)
with open(os.path.join(HERE, "judge", "batch.jsonl"), "w", encoding="utf-8") as f:
    for j, i in enumerate(order, 1):
        q = f"Q{j:03d}"
        key[q] = pairs[i]["id"]
        f.write(json.dumps({"id": q, "a": pairs[i]["a"], "b": pairs[i]["b"]}, ensure_ascii=False) + "\n")
json.dump(key, open(os.path.join(HERE, "judge_key.json"), "w"))

# ---- freeze: data + code
json.dump({"pairs.json": hashlib.sha256(open(os.path.join(HERE, "pairs.json"), "rb").read()).hexdigest()}, open(os.path.join(HERE, "MANIFEST.json"), "w"), indent=1)
files = ["aixl/semantic/__init__.py", "aixl/semantic/compare.py", "aixl/semantic/hybrid.py", "aixl/semantic/lexicon.py", "aixl/semantic/model.py",
         "aixl/semantic/parser.py", "aixl/hybrid_protocol.py", "aixl/arbiter.py", "aixl/resources/arbiter_rules_v1.txt"]
json.dump({f: hashlib.sha256(open(os.path.join(R, f), "rb").read()).hexdigest() for f in files}, open(os.path.join(HERE, "CODE_FREEZE.json"), "w"), indent=1)
print("frozen; lengths (words) a/b mean:", round(sum(nw(p["a"]) for p in pairs) / len(pairs), 1), round(sum(nw(p["b"]) for p in pairs) / len(pairs), 1))
