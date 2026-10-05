"""Mine normal-form rules from DEV disagreements only (never from the held-out set).
  alias : in a text where two independent extractions differ in exactly one concept of the same atom type (one each), that pair is a candidate alias.
          Accepted when it is seen in >= MIN_TEXTS distinct texts. Canonical = the registry id if any, else the most frequent concept in dev.
  python benchmarks/atoms_mine.py alias [--min 2] [--write]"""
import sys, os, json, collections, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atoms_sources import *
from atoms_norm_eval import PAIRS
from aixl.atoms.normalize import lemma, load_tables
from aixl.atoms import registry as R

TYPES = ("ENTITY", "ACTION", "PROPERTY", "LOCATION", "FORMAT")


def concepts(g, t):
    return collections.Counter(lemma(a.concept) for a in g.atoms if a.type == t and a.concept)


def mine_alias(min_texts=2):
    pair_texts = collections.defaultdict(set); freq = collections.Counter()
    for s in DEV:
        src = sources(s)
        for name, G in src.items():
            for g in G.values():
                for t in TYPES:
                    for c, n in concepts(g, t).items(): freq[(t, c)] += n
        for a, b in PAIRS:
            if a in src and b in src:
                for i in src[a]:
                    if i not in src[b]: continue
                    for t in TYPES:
                        ca, cb = concepts(src[a][i], t), concepts(src[b][i], t)
                        ua, ub = ca - cb, cb - ca
                        if len(ua) == 1 and len(ub) == 1:
                            x, y = next(iter(ua)), next(iter(ub))
                            pair_texts[(t, tuple(sorted((x, y))))].add((s, i))
    cands = {k: v for k, v in pair_texts.items() if len(v) >= min_texts}
    return cands, freq


def build_aliases(cands, freq):
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for (t, (x, y)), _ in cands.items(): parent[find((t, x))] = find((t, y))
    groups = collections.defaultdict(list)
    for node in list(parent): groups[find(node)].append(node)
    aliases, report = {}, []
    for root, nodes in groups.items():
        t = nodes[0][0]
        members = [c for _, c in nodes]
        reg = [c for c in members if not c.startswith("x:")]
        canon = reg[0] if reg else max(members, key=lambda c: (freq[(t, c)], c))
        if len(reg) > 1: continue                      # two different registry concepts: never merge (needs a human)
        for c in members:
            if c != canon: aliases[f"{t}:{c}"] = canon
        report.append((t, canon, [c for c in members if c != canon]))
    return aliases, report


LIGHT = {"x:have", "x:do", "x:make", "x:get", "x:be", "x:take", "x:give"}     # light verbs: carry no stable concept (NO GUESS)
PREFIX = {"ENTITY": "ENT", "ACTION": "ACT", "PROPERTY": "PRP"}


def mine_promotions(min_texts=3):
    """x: concepts (after lemma+alias normalization) that appear in >= min_texts DEV texts, each time from >= 2 independent sources."""
    from aixl.atoms.normalize import Normalizer
    n = Normalizer(load_tables(), ("lemma", "alias"))
    seen = collections.defaultdict(lambda: collections.defaultdict(set))
    for s in DEV:
        for name, G in sources(s).items():
            for i, g in G.items():
                for a in n(g).atoms:
                    if a.concept and a.concept.startswith("x:") and a.type in PREFIX and a.concept not in LIGHT: seen[(a.type, a.concept)][(s, i)].add(name)
    out = []
    for (t, c), tx in seen.items():
        good = [k for k, v in tx.items() if len(v) >= 2]
        if len(good) >= min_texts:
            cid = f"{PREFIX[t]}.{c[2:].upper()}"
            if R.concept(cid) is not None and not R.concept(cid).get("learned"): continue
            out.append(dict(id=cid, type=t, lemma=c[2:], definition=f"learned from data (not curated): {c[2:].replace('_', ' ')}; seen in {len(good)} dev texts by >=2 independent sources",
                            evidence=dict(texts=len(good), sources="ann-S/ann-O/llm", mined_from="blind1v3+blind2+blind3", rule=f">= {min_texts} texts")))
    return sorted(out, key=lambda r: (r["type"], r["id"]))


if __name__ == "__main__":
    mn = int(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 2
    if sys.argv[1] == "promote":
        recs = mine_promotions(mn)
        print(f"promotion candidates (>= {mn} dev texts, >= 2 sources each): {len(recs)}", collections.Counter(r['type'] for r in recs))
        print("  " + ", ".join(r["id"] for r in recs))
        if "--write" in sys.argv:
            json.dump(recs, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aixl", "atoms", "data", "learned_concepts.json"), "w"), indent=1, ensure_ascii=False); print("written")
    if sys.argv[1] == "alias":
        cands, freq = mine_alias(mn)
        aliases, report = build_aliases(cands, freq)
        print(f"candidate pairs (>= {mn} texts): {len(cands)}; alias groups: {len(report)}; aliases: {len(aliases)}")
        for t, canon, rest in sorted(report, key=lambda x: -len(x[2])): print(f"  {t:9s} {canon:28s} <- {', '.join(rest)}")
        if "--write" in sys.argv:
            t = load_tables(); t["aliases"] = aliases
            t["alias_evidence"] = {f"{k[0]}:{k[1][0]}~{k[1][1]}": sorted(f"{s}:{i}" for s, i in v) for k, v in cands.items()}
            json.dump(t, open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "aixl", "atoms", "data", "aliases.json"), "w"), indent=1, ensure_ascii=False); print("written")
