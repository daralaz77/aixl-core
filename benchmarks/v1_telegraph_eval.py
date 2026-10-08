"""Validate Option A: (1) fingerprint round-trip telegraph->graph on dev set; (2) real tokenizer saving; (3) real traffic."""
import collections
import statistics as st

import tiktoken

import benchmarks.dataset as d
from aixl.core.completeness import is_complete
from aixl.core.fingerprint import fingerprint_graph as fp
from aixl.gate import compact
from aixl.serialization.aixl_codec import decode, encode
from aixl.telegraph import from_telegraph, to_telegraph
from aixl.translators.natural_to_semantic import to_graph
from benchmarks._corpus import real_user_messages

enc = tiktoken.get_encoding("o200k_base"); T = lambda s: len(enc.encode(s))

def run(texts, label):
    c = collections.Counter(); sav = []; bad = []
    for t in texts:
        g = to_graph(t); tg = None
        try:
            w = compact(encode(g)); tg = to_telegraph(w)
            ok = fp(decode(from_telegraph(tg))) == fp(g)
        except Exception as e:
            c["codec_fail:" + type(e).__name__] += 1; continue
        if not ok: c["fp_mismatch"] += 1; bad.append((t, tg)); continue
        complete = is_complete(t, g)
        if not complete: c["incomplete"] += 1; continue
        if T(tg) < T(t): c["AIXL_TELEGRAPH"] += 1; sav.append(1 - T(tg) / T(t))
        else: c["no_saving"] += 1
    print(f"== {label}: n={len(texts)}", dict(c), "| mean saving when used:", round(st.mean(sav), 3) if sav else "-")
    return bad
ms = set()


if __name__ == "__main__":

    dev = sorted({x for n in ["EQ", "DIFF", "QTY_EQ", "DATE_EQ", "NEG_EQ", "NEG_NEQ", "QTY_NEQ", "DATE_NEQ"] for a, b in getattr(d, n) for x in (a, b)})
    bad = run(dev, "dev set")
    for t, tg in bad[:8]: print("   MISMATCH:", t, "=>", tg)
    ms = real_user_messages()
    run(sorted(ms), "real traffic")
