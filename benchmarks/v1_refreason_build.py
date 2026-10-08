"""Option C reasoning test: questions that need the WHOLE message 1 (incl. the span a pointer replaces). Ground truth computed from the full text."""
import json
import random
import re

from aixl.refstore import _REF, RefStore
from benchmarks._corpus import tool_results, transcript_files
from benchmarks.v1_refquality_build import SECRET

cases = []
LEG = "Note: in a message, a line of the form ⟦=M:A-B⟧ is a pointer meaning 'lines A through B (0-indexed, inclusive) of message M, repeated verbatim here'. All line numbers and counts below refer to the COMPLETE message, as if every pointer were replaced by the lines it points to.\n\n"
HEAD = ("You will see 20 independent cases. Each has MESSAGE 0 and MESSAGE 1 and 3 questions about MESSAGE 1 (the lines are 1-indexed):\n"
        " Q1: on how many lines does the word WORD appear (case-sensitive substring)?\n Q2: what is the number of the FIRST line containing WORD?\n Q3: which line is the LONGEST (most characters)? give its line number.\n"
        "Answer ONLY by reading; do not run any program or tool to expand, search or count. Reply with a JSON list of {\"case\":i,\"q\":1|2|3,\"answer\":<integer>} (60 objects) and nothing else.\n\n")


if __name__ == "__main__":

    random.seed(21)
    files = transcript_files(); random.shuffle(files)
    for f in files:
        seen = []
        for x in tool_results(f):
            if not (800 <= len(x) <= 3500) or SECRET.search(x): continue
            for src in seen[-40:]:
                rs = RefStore(); rs.encode(src); e = rs.encode(x)
                ms = list(_REF.finditer(e))
                if not ms or len(e) > len(x) * 0.85 or rs.decode(e) != x: continue
                lines = x.split("\n"); lens = [len(l) for l in lines]
                if lens.count(max(lens)) != 1: continue
                # a word (>=5 letters) occurring on 2..6 distinct lines, at least one inside a pointed region
                first = e[:ms[0].start()].count("\n"); a, b = int(ms[0].group(2)), int(ms[0].group(3))
                inside = set(range(first, first + (b - a + 1)))
                words = {}
                for i, l in enumerate(lines):
                    for w in sorted(set(re.findall(r"[A-Za-z_]{5,}", l))): words.setdefault(w, []).append(i)   # sorted: set order depends on PYTHONHASHSEED, which made the builder non-reproducible
                cand = [(w, v) for w, v in words.items() if 2 <= len(v) <= 6 and any(i in inside for i in v)]
                if not cand: continue
                w, v = random.choice(cand)
                cases.append({"src": src, "full": x, "enc": e, "word": w,
                              "truth": [len(v), v[0] + 1, lens.index(max(lens)) + 1]})
                break
            seen.append(x)
            if len(cases) >= 40: break
        if len(cases) >= 40: break
    random.shuffle(cases); cases = cases[:20]
    json.dump(cases, open("/private/tmp/claude-501/refreason_cases.json", "w"))
    for kind in ["full", "ptr_legend", "ptr_nolegend"]:
        out = HEAD + (LEG if kind == "ptr_legend" else "")
        for i, c in enumerate(cases):
            out += f"=== CASE {i} (WORD = \"{c['word']}\") ===\n--- MESSAGE 0 ---\n{c['src']}\n--- MESSAGE 1 ---\n{c['full'] if kind == 'full' else c['enc']}\n\n"
        open(f"/private/tmp/claude-501/refr_{kind}.txt", "w").write(out); print(kind, len(out))
    print("cases", len(cases), "mean full", sum(len(c["full"]) for c in cases) // len(cases), "mean enc", sum(len(c["enc"]) for c in cases) // len(cases))
