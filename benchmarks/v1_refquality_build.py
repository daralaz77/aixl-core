"""Build quality cases for Option C: real (src, repeat) message pairs; questions whose answers sit INSIDE the pointed span. Ground truth is computed, not judged."""
import glob
import json
import random
import re

from aixl.refstore import _REF, RefStore

SECRET = re.compile(r"(?i)(api[_-]?key|token|passw|secret|sk-|eyJ|bearer|private key|authorization)")

def blocks(path):
    for l in open(path, errors="ignore"):
        try: o = json.loads(l)
        except Exception: continue
        m = o.get("message")
        if not isinstance(m, dict): continue
        c = m.get("content")
        if isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    x = b.get("content")
                    if isinstance(x, list): x = "\n".join(y.get("text", "") for y in x if isinstance(y, dict) and y.get("type") == "text")
                    if isinstance(x, str): yield x

random.seed(11)
files = glob.glob("/Users/darwingperez/.claude/projects/*/*.jsonl"); random.shuffle(files)
cases = []
for f in files:
    seen = []
    for x in blocks(f):
        if not (700 <= len(x) <= 3500) or SECRET.search(x): continue
        for src in seen[-40:]:
            rs = RefStore(); rs.encode(src); e = rs.encode(x)
            ms = list(_REF.finditer(e))
            if ms and len(e) < len(x) * 0.85 and rs.decode(e) == x:
                m = ms[0]; a, b = int(m.group(2)), int(m.group(3))
                # target line numbers (1-indexed) of message 1 covered by the first pointer
                before = e[:m.start()].count("\n"); first = before + 1
                span_lines = src.split("\n")[a:b + 1]
                cand = [(first + i, ln) for i, ln in enumerate(span_lines) if 25 <= len(ln.strip()) <= 160]
                if len(cand) >= 3:
                    k = random.sample(cand, 2)
                    cases.append({"src": src, "full": x, "enc": e, "qs": [{"line": n, "answer": ln} for n, ln in k]})
                    break
        seen.append(x)
        if len(cases) >= 60: break
    if len(cases) >= 60: break
random.shuffle(cases); cases = cases[:12]
json.dump(cases, open("/private/tmp/claude-501/refquality_cases.json", "w"))
print("cases", len(cases), "mean full chars", sum(len(c["full"]) for c in cases) // max(1, len(cases)), "mean enc chars", sum(len(c["enc"]) for c in cases) // max(1, len(cases)))
