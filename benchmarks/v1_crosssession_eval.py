"""Step 5 potential: how much MORE do pointers save if the store spans sessions? Scopes: session | same project | all projects.
Sessions are replayed in chronological order (first record timestamp). Also: cost-weighted estimate for sessions with usage data (same model as v1_billing_eval).
CAVEAT measured here is only the CHARS that could be pointed at; a fresh session does not contain earlier sessions, so every pointer needs an expand tool."""
import collections
import json
import os

from aixl.refstore import RefStore
from benchmarks._corpus import transcript_files
from benchmarks.v1_billing_eval import W, parse  # noqa  (the module prints its report on import; fine)


def first_ts(p):
    for l in open(p, errors="ignore"):
        try: t = json.loads(l).get("timestamp")
        except Exception: continue
        if t: return t
    return "0"
proj = {}; glob_store = RefStore(annotate=True)
tot = 0; saved = collections.Counter(); per_proj = collections.defaultdict(lambda: collections.Counter())
cost_saved = {"session": 0.0, "project": 0.0, "global": 0.0}; cost_total = 0.0


if __name__ == "__main__":
    files = sorted(transcript_files(), key=first_ts)
    for f in files:
        calls, events = parse(f)
        pd = os.path.basename(os.path.dirname(f))
        ss = RefStore(annotate=True); ps = proj.setdefault(pd, RefStore(annotate=True))
        N = len(calls); has_usage = N >= 5
        if has_usage: cost_total += sum(a * W["fresh"] + b * W["cw"] + c * W["cr"] + d * W["out"] for a, b, c, d, _ in calls)
        for i, x in events:
            n = len(x); tot += n
            if n < 400:
                for st in (ss, ps, glob_store): st._add(x.split("\n"))
                continue
            es, ep, eg = ss.encode(x), ps.encode(x), glob_store.encode(x)
            for name, e in (("session", es), ("project", ep), ("global", eg)):
                d = n - len(e); saved[name] += max(0, d); per_proj[pd][name] += max(0, d)
                if has_usage and d > 0: cost_saved[name] += d * 0.30 * (W["cw"] + W["cr"] * (N - i))
    print(f"\nsessions={len(files)} projects={len(proj)} text chars={tot:,}")
    for k in ("session", "project", "global"):
        print(f"  scope {k:8} saved {100*saved[k]/tot:5.1f}% of chars   cost-weighted (0.30 tok/char) {100*cost_saved[k]/max(1,cost_total):5.1f}% of session cost")
    print(f"  extra from crossing sessions inside a project: +{100*(saved['project']-saved['session'])/tot:.1f} pts; extra from crossing projects: +{100*(saved['global']-saved['project'])/tot:.1f} pts")
    top = sorted(per_proj.items(), key=lambda kv: -kv[1]["global"])[:5]
    for p, c in top: print("   ", p[-52:], {k: f"{v:,}" for k, v in c.items()})
