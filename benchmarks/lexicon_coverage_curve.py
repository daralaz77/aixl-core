"""How far can a hand-extended closed lexicon go? For K = 0..all, if the K most frequent UNACCOUNTED words of a selection corpus were all
known, what share of the held-out other-author seeds (data/arena/other_author_seeds.jsonl) would have no unaccounted word left?
(A ceiling: it ignores unreflected markers and every semantic mapping cost.)   python -m benchmarks.lexicon_coverage_curve"""
import collections
import glob
import json
import os

from aixl.core.completeness import check_completeness
from aixl.translators.auto import to_graph_auto
from lab.arena import arena as A

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = ("input_a", "input_b", "a", "b", "text", "base", "variant")


def selection_texts():
    out = []
    pats = ["data/dev200.jsonl", "data/golden_r/*.jsonl", "data/blind[0-9]*/*.jsonl"]
    for pat in pats:
        for f in glob.glob(os.path.join(ROOT, pat)):
            for line in open(f, encoding="utf-8"):
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                out += [o[k] for k in KEYS if isinstance(o.get(k), str) and len(o[k]) < 220]
    return list(dict.fromkeys(out))


def unaccounted(t):
    return set(check_completeness(t, to_graph_auto(t))["unaccounted"])


if __name__ == "__main__":
    sel = selection_texts()
    freq = collections.Counter()
    for t in sel:
        freq.update(unaccounted(t))
    ranked = [w for w, _ in freq.most_common()]
    ev = [unaccounted(t) for _a, t in A.other_author_seeds()]
    print(f"selection corpus: {len(sel)} texts, {len(ranked)} distinct unaccounted words; evaluation: {len(ev)} other-author seeds")
    for k in (0, 50, 100, 200, 400, 800, 1600, len(ranked)):
        s = set(ranked[:k])
        print(f"  top {k:>5} words known -> {100 * sum(1 for u in ev if u <= s) / len(ev):4.0f}% of seeds with nothing left unaccounted")
