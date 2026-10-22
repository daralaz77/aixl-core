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


_PRON_SWAP = {"he": "she", "she": "he", "his": "her", "her": "his", "him": "her", "él": "ella", "ella": "él", "ele": "ela", "ela": "ele",
              "ellos": "ellas", "ellas": "ellos", "eles": "elas", "elas": "eles", "su": "mi", "sua": "minha", "their": "his", "his ": "their "}


def _role_swap(t, r):
    ms = list(re.finditer(r"(?<![\w@#])(@[A-Za-z0-9_.]+|[A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1][\w\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1]{2,})", t))
    ms = [m for m in ms if m.start() > 0 and t[:m.start()].rstrip()[-1:] not in (".", "!", "?")]
    names = sorted({m.group(0) for m in ms})
    if len(names) < 2:
        return None
    a, b = r.sample(names, 2)
    return re.sub(re.escape(a) + "|" + re.escape(b), lambda m: b if m.group(0) == a else a, t)


def _pronoun_flip(t, r):
    ws = [m for m in re.finditer(r"\b\w+\b", t) if m.group(0).lower() in _PRON_SWAP and m.group(0).lower() not in ("su", "sua", "his ", "their")]
    if not ws:
        return None
    m = r.choice(ws)
    rep = _PRON_SWAP[m.group(0).lower()]
    return t[:m.start()] + (rep.capitalize() if m.group(0)[0].isupper() else rep) + t[m.end():]


def mutants(seeds, reps=2):
    rng = random.Random(7)
    for name, fn in (("role_swap", _role_swap), ("pronoun_flip", _pronoun_flip)):
        for b in seeds:
            m = fn(b, random.Random(rng.randrange(1 << 30)))
            if m and m != b:
                yield name, b, m
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
