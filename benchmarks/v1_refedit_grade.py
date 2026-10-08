"""Grades step 4 (edit / extract / chain). Answers are extracted programmatically from each subagent's final hand-back into /private/tmp/claude-501/rr/s4_<model>_<cond>.json."""
import json, os
truth = json.load(open("/private/tmp/claude-501/refs4_truth.json"))
def grade(d):
    edit_exact = sum(a == b for a, b in zip(d["edit"], truth["edit"]))
    ls = []
    for a, b in zip(d["edit"], truth["edit"]):
        A, B = a.split("\n"), b.split("\n"); ls.append(sum(x == y for x, y in zip(A, B)) / max(len(A), len(B)))
    ext_exact = sum(a == b for a, b in zip(d["extract"], truth["extract"]))
    ch = sum(x == y for a, b in zip(d["chain"], truth["chain"]) for x, y in zip(a, b))
    return edit_exact, round(100 * sum(ls) / len(ls)), ext_exact, ch
print(f"{'run':16} {'edit exact':>10} {'edit lines%':>11} {'extract exact':>13} {'chain lines':>11}")
for model in ("sonnet", "opus", "haiku"):
    for cond in ("full", "ptr"):
        p = f"/private/tmp/claude-501/rr/s4_{model}_{cond}.json"
        if os.path.exists(p):
            e, l, x, c = grade(json.load(open(p))); print(f"{model+' '+cond:16} {e:>7}/10 {l:>10}% {x:>10}/10 {c:>8}/20")
        else: print(f"{model+' '+cond:16}  (no valid result)")
