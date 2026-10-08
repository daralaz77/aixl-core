"""Grades Option C reasoning test (cases from v1_refreason_build.py, seed 21). Answers = subagent replies transcribed in /private/tmp/claude-501/rr/*.txt (60 ints each: case0 q1..q3, case1 ...)."""
import json, os
cases = json.load(open("/private/tmp/claude-501/refreason_cases.json"))
truth = [t for c in cases for t in c["truth"]]
QN = {0: "Q1 count lines with WORD", 1: "Q2 first line with WORD", 2: "Q3 longest line"}
for model in ("sonnet", "opus", "haiku"):
    for cond in ("full", "legend", "nolegend", "annot"):
        p = f"/private/tmp/claude-501/rr/{model}_{cond}.txt"
        if not os.path.exists(p): continue
        a = list(map(int, open(p).read().split()))
        ok = [x == y for x, y in zip(a, truth)]
        per = [sum(ok[i::3]) for i in range(3)]
        print(f"{model:7} {cond:9} {sum(ok):2}/60   Q1 {per[0]}/20  Q2 {per[1]}/20  Q3 {per[2]}/20")
