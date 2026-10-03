"""GBNF grammar for AIXL 0.3 output, derived from the training targets (never from blind5), for llama.cpp's
grammar-constrained decoding. It makes every syntactic failure seen in the distilled model impossible by construction
(invented atoms like `C:`/`X:`/`System:`, `V:AIXL-1.0`, spaces after commas, duplicated atoms, unquoted garbage) and
closes the vocabularies that the card itself closes (intent, action, D, E, priority, goal, output formats):
only values observed in the validated corpora are allowed; open-ended atoms (T, L, H, Y, N, K, F) keep a safe
free-token shape. Atoms appear at most once and in the codec's canonical order.

usage: python distill/aixl_grammar.py [--out distill/aixl.gbnf]
"""
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aixl.legacy02.protocol.atoms import ORDER  # noqa: E402

MIN_COUNT = 2


def lit(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    out = os.path.join(ROOT, "distill", "aixl.gbnf")
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    seen = {k: collections.Counter() for k in "IADEPGO"}
    for name in ("corpus_merged.jsonl", "corpus_paraphrase.jsonl"):
        for line in open(os.path.join(ROOT, "distill", name), encoding="utf-8"):
            if not line.strip():
                continue
            for tok in json.loads(line)["aixl"].split()[1:]:
                k, _, v = tok.partition(":")
                if k in seen:
                    for item in v.split(","):
                        seen[k][item] += 1
    vocab = {k: sorted(i for i, c in seen[k].items() if c >= MIN_COUNT and i and '"' not in i and "=" not in i)
             for k in seen}

    rules = ['root ::= "V:AIXL-0.3"' + "".join(f' ({lit(" " + L + ":")} {L.lower()}val)?' for L in ORDER[1:])]
    for L in ORDER[1:]:
        name = L.lower() + "val"
        if L in vocab:
            alts = " | ".join(lit(x) for x in vocab[L])
            rules.append(f"{name} ::= {L.lower()}item ({lit(',')} {L.lower()}item)*")
            rules.append(f"{L.lower()}item ::= {alts}")
        else:
            rules.append(f"{name} ::= item ({lit(',')} item)*")
    rules.append('item ::= bare | quoted')
    rules.append('bare ::= [A-Za-z0-9_#@=.:<>/+*!?%-]+')
    rules.append('quoted ::= "\\"" [^"\\\\\\n]* "\\""')
    open(out, "w", encoding="utf-8").write("\n".join(rules) + "\n")
    print("vocab sizes:", {k: len(v) for k, v in vocab.items()})
    print("written", out)


if __name__ == "__main__":
    main()
