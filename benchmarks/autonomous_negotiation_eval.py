"""E-AUTONOMOUS: does negotiate_autonomous() still resolve the SAME real 21 cross-vendor disagreements
as the single-process negotiate() (benchmarks/negotiation_eval.py) — now via a genuinely separate
sender process (aixl/agents/sender_agent.py --aixl <sonnet's real encoding>) over real MCP stdio
JSON-RPC, with no shared memory and no human relaying a turn? Reuses the exact same E-INTEROP round-3
data (not synthetic examples).
usage: python -m benchmarks.autonomous_negotiation_eval"""
import json
import os
import re
import sys

from aixl.autonomous_negotiation import negotiate_autonomous
from aixl.core.comparator import compare_canonical
from aixl.serialization import aixl_codec

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(p):
    d = {}
    for l in open(p, encoding="utf-8"):
        m = re.match(r"^\s*(t\d{3})\s*::\s*(.+?)\s*$", l)
        if m: d[m.group(1)] = m.group(2).strip("`")
    return d


def run():
    texts = json.load(open(os.path.join(ROOT, "data", "interop", "texts_interop1.json"), encoding="utf-8"))
    sonnet = read(os.path.join(ROOT, "data", "interop", "sonnet_answers_round3.txt"))
    gemini = read(os.path.join(ROOT, "data", "interop", "gemini_answers_round3.txt"))
    rows = []
    for t in texts:
        tid = t["tid"]
        gs = aixl_codec.decode(sonnet[tid]); ge = aixl_codec.decode(gemini[tid])
        sc, gc = gs.canonical(), ge.canonical()
        r0 = compare_canonical(sc, gc)
        if r0.equivalent:
            continue
        n_diffs = len(r0.differences)
        sender_cmd = [sys.executable, "-m", "aixl.agents.sender_agent", "--aixl", sonnet[tid]]
        out = negotiate_autonomous(sender_cmd, gc, max_rounds=n_diffs)
        rows.append({"tid": tid, "text": t["text"], "diffs_before": n_diffs, "rounds": out.rounds,
                     "converged": out.converged, "dims": [c.dim for c in out.transcript if c.turn_type == "CLARIFY"]})
    n = len(rows)
    converged = sum(r["converged"] for r in rows)
    avg_rounds = round(sum(r["rounds"] for r in rows) / n, 3) if n else 0.0
    summary = {"disagreements": n, "converged": converged, "convergence_rate": round(converged / n, 4) if n else None,
               "avg_rounds": avg_rounds, "max_rounds_used": max((r["rounds"] for r in rows), default=0)}
    return summary, rows


if __name__ == "__main__":
    s, rows = run()
    print(json.dumps(s, ensure_ascii=False, indent=1))
