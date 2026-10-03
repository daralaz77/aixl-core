"""ADR-017 adversarial experiment. Pairs: red-team set by Opus (70 ATK NOT_EQUIVALENT designed to fool an LLM arbiter + 40 CTL EQUIVALENT that look
suspicious), plus the project's own sil_security HARD (57, must be flagged) and CONTROL (31, benign restatements).
Arms per pair: ARB = 2-of-2 consensus of the full-text arbiter (Sonnet, Haiku); AIXL = rules route with INCONCLUSIVE on (EQUIVALENT only if proven);
VETO = ARB says SAME and AIXL gives no SEPARATING evidence (verdict NOT_EQUIVALENT, contradiction, or input-obfuscation findings) -> still SAME;
STRICT = ARB says SAME and AIXL proves EQUIVALENT.  False-SAME on ATK/HARD is the dangerous error; SAME on controls is recall.
usage: python -m benchmarks.adversarial_eval DIR"""
import json, glob, sys, os, collections
from aixl import compare, detect_contradiction
from aixl.core.ontology import load_config
from aixl.core.normalizer import sanitize_input

def verdicts(d, model):
    v = {}
    for p in glob.glob(os.path.join(d, f"adv_out_{model}_*.tsv")):
        for l in open(p, encoding="utf-8"):
            f = l.rstrip("\n").split("\t")
            if len(f) >= 2: v[f[0]] = f[1].strip().upper()
    return v

def main():
    d = sys.argv[1]
    pairs = json.load(open("data/blind10/adv_pairs.json"))
    cfg = dict(load_config()); cfg["inconclusive"] = True
    J = {m: verdicts(d, m) for m in ("sonnet", "haiku")}
    tab = collections.defaultdict(collections.Counter)
    miss = []
    for p in pairs:
        s, h = J["sonnet"].get(p["jid"], "MISSING"), J["haiku"].get(p["jid"], "MISSING")
        arb = "SAME" if s == h == "SAME" else "NOT_SAME"
        r = compare(p["a"], p["b"], cfg)
        sep = (r.verdict == "NOT_EQUIVALENT") or detect_contradiction(p["a"], p["b"]).contradiction \
              or bool(sanitize_input(p["a"])[1]) or bool(sanitize_input(p["b"])[1])
        arms = {"sonnet alone": s == "SAME", "haiku alone": h == "SAME", "ARB consensus": arb == "SAME",
                "AIXL rules only": r.verdict == "EQUIVALENT", "ARB + AIXL veto": arb == "SAME" and not sep,
                "ARB + AIXL strict": arb == "SAME" and r.verdict == "EQUIVALENT"}
        grp = p["group"]
        for name, said_same in arms.items():
            tab[name][(grp, said_same)] += 1
        if p["label"] == "NOT_EQUIVALENT" and arb == "SAME": miss.append((p["group"], p["a"][:80], p["b"][:80]))
    groups = sorted({p["group"] for p in pairs})
    print(f"{'arm':20s} " + " | ".join(f"{g}: SAME/{sum(c for (gg, _), c in tab['ARB consensus'].items() if gg == g)}" for g in groups))
    for name, c in tab.items():
        print(f"{name:20s} " + " | ".join(f"{g}: {c[(g, True)]}" for g in groups))
    print("\nARB consensus false-SAME on non-equivalent pairs:")
    for m in miss: print("  ", m)
main()
