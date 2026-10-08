"""Real user messages (local Claude Code transcripts, never leave the machine) + real BPE tokenizer (tiktoken o200k_base,
NOT Claude's tokenizer). Question: does the AIXL gate ever pick AIXL, and how much does it save?"""
import glob, json, re, statistics as st, collections, sys
import tiktoken
import aixl.gate as G
enc = tiktoken.get_encoding("o200k_base")
G.count_tokens = lambda s: len(enc.encode(s))
msgs = set()
for f in glob.glob("/Users/darwingperez/.claude/projects/*/*.jsonl"):
    for line in open(f, errors="ignore"):
        try: o = json.loads(line)
        except Exception: continue
        if o.get("type") != "user" or o.get("isMeta"): continue
        c = o.get("message", {}).get("content")
        if not isinstance(c, str): continue
        c = c.strip()
        if not c or c.startswith("<") or "system-reminder" in c or "pasted_content" in c or c.startswith("[") or c.startswith("/"): continue
        msgs.add(c)
msgs = sorted(msgs)
print("unique real user messages:", len(msgs))
buckets = {"<=15 tok": (0, 15), "16-60": (16, 60), "61-250": (61, 250), ">250": (251, 10**9)}
rows = []
for m in msgs:
    try: r = G.translate_gated(m)
    except Exception as e: rows.append({"mode": "ERROR", "reason": type(e).__name__, "tokens_natural": len(enc.encode(m)), "saving": 0}); continue
    rows.append(r)
print("mode:", collections.Counter(r["mode"] for r in rows))
print("reason:", collections.Counter(r["reason"] for r in rows).most_common())
for b, (lo, hi) in buckets.items():
    s = [r for r in rows if lo <= r["tokens_natural"] <= hi]
    a = [r for r in s if r["mode"] == "AIXL"]
    print(f"{b:9} n={len(s):4} AIXL={len(a):3} meansave_when_AIXL={round(st.mean([r['saving'] for r in a]),3) if a else '-'}")
fpf = sum(1 for r in rows if r["mode"] == "AIXL" and not r["roundtrip_fingerprint_ok"]); print("AIXL with fp failure:", fpf)
json.dump([{"nat": r["tokens_natural"], "aix": r.get("tokens_aixl"), "mode": r["mode"], "reason": r["reason"]} for r in rows], open("/private/tmp/claude-501/real_eval.json", "w"))
