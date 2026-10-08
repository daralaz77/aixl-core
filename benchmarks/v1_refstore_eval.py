"""Option C on REAL agent traffic: all text blocks (user, assistant text, tool results) of local Claude Code sessions, in order, one RefStore per session."""
import collections
import glob
import json
import random
import time

import tiktoken

from aixl.refstore import RefStore

enc = tiktoken.get_encoding("o200k_base")

def blocks(path):
    for l in open(path, errors="ignore"):
        try: o = json.loads(l)
        except Exception: continue
        m = o.get("message")
        if not isinstance(m, dict): continue
        c, role = m.get("content"), o.get("type")
        if isinstance(c, str): yield "user_text" if role == "user" else "assistant_text", c
        elif isinstance(c, list):
            for b in c:
                if not isinstance(b, dict): continue
                t = b.get("type")
                if t == "text": yield ("user_text" if role == "user" else "assistant_text"), b.get("text", "")
                elif t == "tool_result":
                    x = b.get("content")
                    if isinstance(x, list): x = "\n".join(y.get("text", "") for y in x if isinstance(y, dict) and y.get("type") == "text")
                    if isinstance(x, str): yield "tool_result", x

files = sorted(glob.glob("/Users/darwingperez/.claude/projects/*/*.jsonl"))
tot = collections.Counter(); sav = collections.Counter(); nref = 0; fails = 0; per = []
sample = []                                   # (original, encoded) pairs for exact token counting
t0 = time.time()
for f in files:
    rs = RefStore(); s_tot = s_sav = 0
    for kind, text in blocks(f):
        if not text or len(text) < 400: 
            tot[kind] += len(text or ""); continue
        e = rs.encode(text)
        tot[kind] += len(text); d = len(text) - len(e)
        if d > 0:
            sav[kind] += d; nref += 1; s_sav += d
            if len(sample) < 3000 and random.random() < 0.2: sample.append((text, e))
        s_tot += len(text)
    per.append((s_tot, s_sav))
T, S = sum(tot.values()), sum(sav.values())
print(f"sessions={len(files)} chars={T:,} saved={S:,} ({100*S/T:.1f}%) encoded_blocks={nref} elapsed={time.time()-t0:.0f}s")
for k in tot: print(f"  {k:15} chars={tot[k]:>13,} share={100*tot[k]/T:5.1f}%  saved={100*sav[k]/max(1,tot[k]):5.1f}% of its own")
# exact tokens on a sample of encoded blocks (pointer text itself costs tokens)
a = sum(len(enc.encode(o, disallowed_special=())) for o, _ in sample); b = sum(len(enc.encode(e, disallowed_special=())) for _, e in sample)
print(f"exact o200k tokens on {len(sample)} encoded blocks: {a:,} -> {b:,}  ({100*(1-b/a):.1f}% fewer)")
big = sorted(per, reverse=True)[:5]; print("top sessions (chars, saved%):", [(c, round(100*s/c)) for c, s in big])
