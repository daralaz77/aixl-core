"""One pass of the improvement loop: the numbers that decide whether a change is safe, in one command.   python -m benchmarks.loop_pass [--residue]
  1. labelled pairs (dev, arena paraphrases, blind13/14): core and published recall / false-EQUIVALENT
  2. meaning-changing mutants (own seeds + other-author seeds): core-EQUIVALENT per family, and the DEFECT counters of the published layers
Exit 1 when any published layer declares a meaning change the same."""
import collections
import random
import sys

import aixl
from aixl.api.service import compare_verified
from benchmarks.compare_verified_eval import pairs
from lab.arena import arena as A


def labelled():
    c = collections.defaultdict(collections.Counter)
    for corpus, lab, a, b in pairs():
        try:
            core, ver = aixl.compare(a, b).equivalent, compare_verified(a, b)["equivalent"]
        except Exception:
            continue
        c[corpus][(lab, "core", core)] += 1; c[corpus][(lab, "ver", ver)] += 1
    bad = 0
    for corpus, k in c.items():
        ns = k[("SAME", "core", True)] + k[("SAME", "core", False)]
        nd = k[("DIFF", "core", True)] + k[("DIFF", "core", False)]
        print(f"  {corpus[:44]:44} SAME core {k[('SAME', 'core', True)]:>3}/{ns:<3} verified {k[('SAME', 'ver', True)]:>3} | DIFF core-EQ {k[('DIFF', 'core', True)]:>3}/{nd:<3} verified-EQ {k[('DIFF', 'ver', True)]:>3}")
        bad += k[("DIFF", "ver", True)]
    return bad


def mutants(residue=False):
    bad = 0
    for name, seeds in (("own seeds", list(A.SEEDS)), ("other-author seeds", [t for _a, t in A.other_author_seeds()])):
        rng, fam, n, ver_eq = random.Random(7), collections.Counter(), 0, 0
        ex = collections.defaultdict(dict)
        for kname, kind, fn in A.NL_ATTACKERS:
            if kind != "META":
                continue
            for base in seeds:
                for _ in range(2):
                    try:
                        m = fn(base, random.Random(rng.randrange(1 << 30)))
                    except Exception:
                        m = None
                    if not m or m == base:
                        continue
                    n += 1
                    if aixl.compare(base, m).equivalent:
                        fam[kname] += 1; ex[kname][(base, m)] = 1
                    if compare_verified(base, m)["equivalent"]:
                        ver_eq += 1
        print(f"  {name}: {n} mutants; core-EQUIVALENT {sum(fam.values())} {dict(fam.most_common())}; published verified-EQUIVALENT {ver_eq}")
        bad += ver_eq
        if residue:
            for k, d in ex.items():
                for b, m in list(d)[:3]:
                    print(f"      [{k}] {b[:75]!r} -> {m[:75]!r}")
    return bad


if __name__ == "__main__":
    print("labelled pairs:"); b1 = labelled()
    print("mutants:"); b2 = mutants("--residue" in sys.argv)
    sys.exit(1 if b1 or b2 else 0)
