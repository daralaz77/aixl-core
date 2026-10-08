"""Step 3: REAL Claude token counts (usage in the transcripts) + billing-weighted effect of pointers.
Cost units (relative to 1 fresh input token): cache write 1.25, cache read 0.10, output 5.0 (published Anthropic ratios; ASSUMPTION, prices change).
Pointer saving model per encoded block of d chars in call i of N: tokens = d*r ; cost saved = tokens*(1.25 + 0.10*(N-i))  (written once, then re-read every later call).
Ignores: cache TTL expiry, context compaction (both make the real saving different), thinking blocks."""
import collections
import json

from aixl.refstore import RefStore
from benchmarks._corpus import transcript_files

W = {"fresh": 1.0, "cw": 1.25, "cr": 0.10, "out": 5.0}

def parse(path):
    calls, seen, events = [], set(), []
    for l in open(path, errors="ignore"):
        try: o = json.loads(l)
        except Exception: continue
        m = o.get("message")
        if not isinstance(m, dict): continue
        u = m.get("usage")
        if o.get("type") == "assistant" and isinstance(u, dict):
            mid = m.get("id") or o.get("requestId")
            if mid not in seen:
                seen.add(mid); calls.append((u.get("input_tokens", 0), u.get("cache_creation_input_tokens", 0), u.get("cache_read_input_tokens", 0), u.get("output_tokens", 0), m.get("model", "")))
        c = m.get("content")
        if isinstance(c, list):
            for b in c:
                if not isinstance(b, dict): continue
                t = b.get("type")
                if t == "tool_result":
                    x = b.get("content")
                    if isinstance(x, list): x = "\n".join(y.get("text", "") for y in x if isinstance(y, dict) and y.get("type") == "text")
                    if isinstance(x, str): events.append((len(calls), x))
                elif t == "text" and o.get("type") == "user": events.append((len(calls), b.get("text", "")))
        elif isinstance(c, str) and o.get("type") == "user": events.append((len(calls), c))
    return calls, events


def step_ratio(calls, events):
    """context growth between consecutive calls (minus the previous output) vs chars of the text added in between; only big steps (>=2000 chars), no compaction (growth>0)."""
    by = collections.defaultdict(int)
    for i, x in events: by[i] += len(x)
    num = den = 0
    for k in range(len(calls) - 1):
        ctx0 = sum(calls[k][:3]); ctx1 = sum(calls[k + 1][:3]); ch = by.get(k + 1, 0)
        added = ctx1 - ctx0 - calls[k][3]
        if ch >= 2000 and added > 0 and added < ch * 2: num += added; den += ch
    return num, den
chars_all = new_tok = 0; rows = []; RN = RD = 0


if __name__ == "__main__":

    tot = collections.Counter(); fam = collections.defaultdict(collections.Counter)
    for f in transcript_files():
        calls, events = parse(f)
        if len(calls) < 5: continue
        N = len(calls); a_, b_ = step_ratio(calls, events); RN += a_; RD += b_
        cost = sum(a * W["fresh"] + b * W["cw"] + c * W["cr"] + d * W["out"] for a, b, c, d, _ in calls)
        for a, b, c, d, _ in calls:
            tot["fresh"] += a; tot["cw"] += b; tot["cr"] += c; tot["out"] += d
        new_tok += sum(a + b for a, b, c, d, _ in calls[1:])          # tokens that were NEW after the first call
        ev_chars = sum(len(x) for i, x in events if i >= 1)
        chars_all += ev_chars
        rs = RefStore(annotate=True); saved = [(i, len(x) - len(rs.encode(x))) for i, x in events if len(x) >= 400]
        model = calls[-1][4]
        rows.append((cost, saved, N, model, ev_chars, sum(a + b for a, b, c, d, _ in calls[1:])))
    r = RN / max(1, RD)                  # real tokens per char from per-step context growth
    print(f"sessions with >=5 calls: {len(rows)} | unique API calls: {sum(r_[2] for r_ in rows):,}")
    T = sum(tot.values()); print("token mix (real usage):", {k: f"{v:,} ({100*v/T:.1f}%)" for k, v in tot.items()})
    cu = {k: tot[k] * W[k] for k in W}; CT = sum(cu.values())
    print("COST mix (weighted):", {k: f"{100*v/CT:.1f}%" for k, v in cu.items()})
    print(f"calibration (per-step context growth): {RN:,} tokens / {RD:,} chars = {r:.3f} tok/char (tiktoken o200k on blocks was ~0.28-0.33)")
    for label, rr in (("calibrated r", r), ("tiktoken-like r=0.30", 0.30)):
        sv = 0.0; svs = collections.Counter(); costs = collections.Counter()
        for cost, saved, N, model, _, _ in rows:
            s = sum(d * rr * (W["cw"] + W["cr"] * (N - i)) for i, d in saved if d > 0)
            fam_ = "sonnet" if "sonnet" in model else "haiku" if "haiku" in model else "other"
            svs[fam_] += s; costs[fam_] += cost
        tot_s, tot_c = sum(svs.values()), sum(costs.values())
        print(f"[{label}] cost saved by pointers = {100*tot_s/tot_c:.1f}% of total session cost; by family:", {k: f"{100*svs[k]/costs[k]:.1f}% of {costs[k]/1e6:.0f}M units" for k in costs})
