"""Safety/benefit of the open-vocabulary rule (aixl/core/open_vocab.py). For every pair where the core says EQUIVALENT but a text is incomplete
(today: INCONCLUSIVE), does the rule rescue it, and is the rescued pair really SAME?   python -m benchmarks.open_vocab_eval
Mutants (arena, own seeds and other-author seeds) are ALL meaning-changing: any rescue there is a false EQUIVALENT."""
import collections
import random

import aixl
from aixl.core.open_vocab import residue_identical
from aixl.translators.auto import to_graph_auto
from benchmarks.compare_verified_eval import pairs
from lab.arena import arena as A


def judge(a, b):
    """-> 'n/a' (core not EQUIVALENT or both complete) | 'rescued' | 'still_abstain'"""
    from aixl.core.completeness import is_complete
    if not aixl.compare(a, b).equivalent:
        return "n/a"
    ga, gb = to_graph_auto(a), to_graph_auto(b)
    if is_complete(a, ga) and is_complete(b, gb):
        return "n/a"
    return "rescued" if residue_identical(a, ga, b, gb) else "still_abstain"


def main():
    c = collections.Counter()
    for corpus, lab, a, b in pairs():
        try:
            j = judge(a, b)
        except Exception:
            continue
        if j != "n/a":
            c[(corpus, lab, j)] += 1
    print("labelled pairs (core EQUIVALENT and incomplete):")
    for corpus in sorted({k[0] for k in c}):
        s = {j: c[(corpus, "SAME", j)] for j in ("rescued", "still_abstain")}
        d = {j: c[(corpus, "DIFF", j)] for j in ("rescued", "still_abstain")}
        print(f"  {corpus:50} SAME rescued {s['rescued']:>3} / abstain {s['still_abstain']:>3} | DIFF rescued (FALSE-EQ) {d['rescued']:>3} / abstain {d['still_abstain']:>3}")
    for name, seeds in (("arena own seeds", list(A.SEEDS)), ("other-author seeds", [t for _a, t in A.other_author_seeds()])):
        rng, n, resc, ex = random.Random(7), 0, 0, []
        for kind_name, kind, fn in A.NL_ATTACKERS:
            if kind != "META":
                continue
            for base in seeds:
                for _ in range(3):
                    try:
                        m = fn(base, random.Random(rng.randrange(1 << 30)))
                    except Exception:
                        m = None
                    if not m or m == base:
                        continue
                    n += 1
                    if judge(base, m) == "rescued":
                        resc += 1; ex.append((kind_name, base, m))
        print(f"  mutants, {name}: {n}; rescued = false EQUIVALENT: {resc}")
        for e in ex[:6]:
            print("     ", e)


if __name__ == "__main__":
    main()
