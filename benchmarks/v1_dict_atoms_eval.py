"""§10 adaptive dictionary + §21 vocabulary evolution: do they save tokens? (dev-set, own-author; proxy tokenizer)"""
import collections
import random
import statistics as st

import benchmarks.dataset as d
from aixl.gate import ABBR, compact, count_tokens, translate_gated
from aixl.serialization.aixl_codec import encode
from aixl.translators.natural_to_semantic import to_graph

texts = sorted({x for n in ["EQ","DIFF","QTY_EQ","DATE_EQ"] for a, b in getattr(d, n) for x in (a, b)})
comp = {t: compact(encode(to_graph(t))) for t in texts}

# ---- §10: session dictionary. Sessions = k messages sharing the same target (BEST case for a dictionary).
def dict_session(msgs):
    """Greedy: replace repeated whitespace-separated tags by D<i>; count definition cost. Returns (before, after)."""
    toks = [m.split() for m in msgs]
    cnt = collections.Counter(t for ts in toks for t in ts)
    before = sum(count_tokens(m) for m in msgs)
    defs, i, out = [], 1, toks
    for tag, n in cnt.most_common():
        gain = (n - 1) * count_tokens(tag) - n * count_tokens(f"D{i}") - count_tokens(f"D{i}={tag}") + count_tokens(tag) * 0
        # honest accounting: replace n uses, pay one definition line
        gain = n * count_tokens(tag) - (n * count_tokens(f"D{i}") + count_tokens(f"D{i}={tag}"))
        if gain > 0:
            out = [[f"D{i}" if t == tag else t for t in ts] for ts in out]
            defs.append(f"D{i}={tag}"); i += 1
    after = sum(count_tokens(" ".join(ts)) for ts in out) + sum(count_tokens(x) for x in defs)
    return before, after, len(defs)

random.seed(7)
by_target = collections.defaultdict(list)
for t in texts:
    tg = [p for p in comp[t].split() if p.startswith("E:")]
    by_target[tg[0] if tg else None].append(t)
res = {}
for k in (3, 5, 10, 20):
    gains = []
    for tg, ms in by_target.items():
        if tg is None or len(ms) < k: continue
        for _ in range(20):
            b, a, nd = dict_session([comp[m] for m in random.sample(ms, k)])
            gains.append(1 - a / b)
    res[k] = (round(st.mean(gains), 3), len(gains)) if gains else None
print("§10 dictionary on compact AIXL msgs, saving by session length (mean, n):", res)

# ---- §10b: dictionary applied to NATURAL text (what the prompt literally asks: D1=DOCUMENTO)
def nat_dict(msgs):
    words = collections.Counter(w for m in msgs for w in m.rstrip(".").split() if len(w) > 5)
    before = sum(count_tokens(m) for m in msgs); defs = []; ms = list(msgs); i = 1
    for w, n in words.most_common(5):
        gain = n * count_tokens(w) - (n * count_tokens(f"D{i}") + count_tokens(f"D{i}={w}"))
        if gain > 0:
            ms = [" ".join(f"D{i}" if x.rstrip('.') == w else x for x in m.split()) for m in ms]; defs.append(f"D{i}={w}"); i += 1
    return before, sum(count_tokens(m) for m in ms) + sum(count_tokens(x) for x in defs)
g = []
for tg, ms in by_target.items():
    if tg and len(ms) >= 10:
        b, a = nat_dict(random.sample(ms, 10)); g.append(1 - a / b)
print("§10b dictionary on NATURAL text, 10-msg sessions, mean saving:", round(st.mean(g), 3), "n=", len(g))

# ---- §21: evolve atoms = abbreviate the most frequent long tags; measure gate AIXL-rate and saving
import aixl.gate as G

base = [translate_gated(t) for t in texts]
freq = collections.Counter(p for c in comp.values() for p in c.split() if count_tokens(p) >= 2 and p not in ABBR)
print("most frequent unabbreviated tags:", freq.most_common(8))
new = {}
for p, _n in freq.most_common(12):
    k, v = p.split(":", 1)
    cand = k + ":" + v[:3].upper()
    if cand not in new.values() and cand not in G._REV: new[p] = cand
G.ABBR.update(new); G._REV.update({v: k for k, v in new.items()})
after = [translate_gated(t) for t in texts]
f = lambda R: (sum(r["mode"] == "AIXL" for r in R), round(st.mean([r["saving"] for r in R if r["mode"] == "AIXL"] or [0]), 3), sum(not r["roundtrip_fingerprint_ok"] for r in R))
print("gate base  (AIXL used, mean saving, fp failures):", f(base))
print("gate +12 evolved atoms                           :", f(after), "added:", new)
