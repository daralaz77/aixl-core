"""Step 4: pointers on EDIT, EXTRACT and CHAINED pointers. Ground truth computed from the full text. Cases = the 20 real pairs of the reasoning test (seed 21)."""
import json
import random

from aixl.refstore import RefStore

cases = json.load(open("/private/tmp/claude-501/refreason_cases.json"))
random.seed(5)
sel = cases[:10]
LEG = ("Note: a line of the form ⟦=M:A-B (N lines)⟧ is a pointer meaning 'lines A through B (0-indexed, inclusive) of message M, N lines in total, repeated verbatim here'. "
       "Message M is the COMPLETE original message M, even if message M is shown to you with pointers itself. Treat every pointer as if it were replaced by the N lines it points to.\n\n")
HEAD = ("Three tasks. Do not run any program or tool to expand, search or count; answer purely by reading. Reply with ONE JSON object and nothing else:\n"
        ' {"edit":[10 strings],"extract":[10 lists of strings],"chain":[10 lists of 2 strings]}\n'
        " TASK EDIT (cases E0-E9): output MESSAGE 1 in full, exactly as it would read with every pointer expanded, but with every occurrence of WORD replaced by ZZZ. Keep all other characters and line breaks. One string per case.\n"
        " TASK EXTRACT (cases X0-X9): output, in order, the complete lines of MESSAGE 1 (pointers expanded) that contain WORD (case-sensitive substring), exactly. One list of strings per case.\n"
        " TASK CHAIN (cases C0-C9): MESSAGE 2 repeats MESSAGE 1 and adds lines at the end. Output the exact text of the two requested lines of MESSAGE 2 (1-indexed, pointers expanded).\n\n")
truth = {"edit": [], "extract": [], "chain": []}
def build(ptr):
    out = HEAD + (LEG if ptr else "")
    for i, c in enumerate(sel):
        rs = RefStore(annotate=True); rs.encode(c["src"]); e = rs.encode(c["full"]); m1 = e if ptr else c["full"]
        out += f"=== E{i} (WORD = \"{c['word']}\") ===\n--- MESSAGE 0 ---\n{c['src']}\n--- MESSAGE 1 ---\n{m1}\n\n"
        out += f"=== X{i} (WORD = \"{c['word']}\") === same MESSAGE 0 and MESSAGE 1 as E{i}\n\n"
        if not ptr:
            truth["edit"].append(c["full"].replace(c["word"], "ZZZ"))
            truth["extract"].append([l for l in c["full"].split("\n") if c["word"] in l])
    for i, c in enumerate(sel):
        rs = RefStore(annotate=True); rs.encode(c["src"]); e1 = rs.encode(c["full"])
        full2 = c["full"] + "\nappended line alpha for the chain test\nappended line beta for the chain test"
        e2 = rs.encode(full2)
        lines = c["full"].split("\n"); cand = [(n + 1, l) for n, l in enumerate(lines) if 25 <= len(l.strip()) <= 160]
        pick = random.sample(cand, 2) if len(cand) >= 2 else cand * 2
        if not ptr: truth["chain"].append([l for _, l in pick]); truth.setdefault("chain_n", []).append([n for n, _ in pick])
        else:
            pick = [(n, l) for n, l in zip(truth["chain_n"][i], truth["chain"][i])]
        m1c, m2c = (e1, e2) if ptr else (c["full"], full2)
        out += f"=== C{i} ===\n--- MESSAGE 0 ---\n{c['src']}\n--- MESSAGE 1 ---\n{m1c}\n--- MESSAGE 2 ---\n{m2c}\n--- QUESTION --- lines {pick[0][0]} and {pick[1][0]} of MESSAGE 2\n\n"
    return out
for ptr, name in ((False, "full"), (True, "ptr")):
    t = build(ptr); open(f"/private/tmp/claude-501/refs4_{name}.txt", "w").write(t); print(name, len(t))
json.dump(truth, open("/private/tmp/claude-501/refs4_truth.json", "w"))
