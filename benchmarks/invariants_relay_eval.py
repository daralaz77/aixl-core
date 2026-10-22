"""Regime where critical-slot invariants are meant to work: NEAR-VERBATIM relays (copy, truncate, flip, inject) vs benign near-verbatim edits.
Corruptions = the arena's meaning-changing mutants; benign = deterministic formatting / politeness / contraction edits that keep the meaning.
Families are selected on the arena's OWN seeds and scored on the OTHER-AUTHOR seeds (which never saw the code).   python -m benchmarks.invariants_relay_eval"""
import collections
import random
import re

import aixl.invariants as I
from lab.arena import arena as A

BENIGN = [
    ("case", lambda t: t[:1].lower() + t[1:] if t[:1].isupper() else t),
    ("whitespace", lambda t: re.sub(r" ", "  ", t, count=2) + " "),
    ("newline", lambda t: t.replace(", ", ",\n", 1)),
    ("polite_en", lambda t: "Please " + t[0].lower() + t[1:] if t[:1].isalpha() else t),
    ("polite_es", lambda t: "Por favor, " + t[0].lower() + t[1:] if t[:1].isalpha() else t),
    ("contraction", lambda t: re.sub(r"\bdon't\b", "do not", t).replace("can't", "cannot").replace("do not", "don't") if "'" in t or "do not" in t else t),
    ("markdown", lambda t: "**" + t.rstrip(".") + "**."),
    ("quote", lambda t: "“" + t + "”"),
]


def mutants(seeds, reps=2):
    rng = random.Random(7)
    for name, kind, fn in A.NL_ATTACKERS:
        if kind != "META":
            continue
        for b in seeds:
            for _ in range(reps):
                try:
                    m = fn(b, random.Random(rng.randrange(1 << 30)))
                except Exception:
                    m = None
                if m and m != b:
                    yield name, b, m


def fire(a, b):
    return {v[0] for v in I.check(a, b)}


def measure(seeds):
    _det, n = collections.Counter(), 0
    fam_det = collections.Counter(); by_attack = collections.defaultdict(lambda: [0, 0])
    for name, b, m in mutants(seeds):
        n += 1
        f = fire(b, m)
        by_attack[name][1] += 1
        if f:
            by_attack[name][0] += 1
        for x in f:
            fam_det[x] += 1
    fa, nb = collections.Counter(), 0
    for b in seeds:
        for _bn, fn in BENIGN:
            t = fn(b)
            if t == b:
                continue
            nb += 1
            for x in fire(b, t):
                fa[x] += 1
    return n, fam_det, by_attack, nb, fa


def main():
    own = list(A.SEEDS); other = [t for _a, t in A.other_author_seeds()]
    n, fd, _, nb, fa = measure(own)
    chosen = sorted(f for f in fd if fa[f] / max(nb, 1) <= 0.005 and fd[f] >= 1)
    print(f"selection on OWN seeds: {n} corruptions, {nb} benign edits; rule: benign false-alarm rate <= 0.5 % and >= 1 detection")
    for f in sorted(fd, key=lambda x: -fd[x]):
        print(f"  own {f:16} detects {fd[f]:>4}/{n}  benign FA {fa[f]:>3}/{nb} {'<- chosen' if f in chosen else ''}")
    print("chosen:", chosen)
    n2, fd2, by_attack, nb2, fa2 = measure(other)
    for f in sorted(fd2, key=lambda x: -fd2[x]):
        print(f"  {f:18} detects {fd2[f]:>5}/{n2}  benign false alarms {fa2[f]:>4}/{nb2}")
    # scored: a pair is flagged if ANY chosen family fires
    flagged = tot = 0; ba = collections.defaultdict(lambda: [0, 0])
    for name, b, m in mutants(other):
        tot += 1; hit = bool(fire(b, m) & set(chosen)); flagged += hit; ba[name][0] += hit; ba[name][1] += 1
    fb = tb = 0
    for b in other:
        for _bn, fn in BENIGN:
            t = fn(b)
            if t == b:
                continue
            tb += 1; fb += bool(fire(b, t) & set(chosen))
    print(f"\nOTHER-AUTHOR seeds, chosen families {chosen}:\n  corruptions flagged {flagged}/{tot} = {flagged / tot:.1%}; benign edits flagged {fb}/{tb} = {fb / max(tb, 1):.1%}")
    for k, (h, t) in sorted(ba.items(), key=lambda kv: -kv[1][0] / kv[1][1]):
        print(f"    {k:15} {h:>4}/{t:<4} {h / t:5.0%}")


if __name__ == "__main__":
    main()
