"""Evaluate the LLM wrapper with abstention (aixl.atoms.llm_extract) on blind3. No model calls: reads stored responses.
New runs (resp_blind3_{sonnet,opus}_{1,2}.txt, produced from build_prompt) are the two 'calls'; the OLD annotations
(annot_blind3_S / annot_blind3_O, read the guide from disk) are independent references.  python benchmarks/atoms_wrapper_eval.py"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atoms_gold import D, load

from aixl.atoms import fidelity
from aixl.atoms import llm_extract as LX


def load_set(SET):
    cases = json.load(open(os.path.join(D, f"{SET}_cases.json"), encoding="utf-8"))
    ids = [c["id"] for c in cases]; texts = {c["id"]: c["text"] for c in cases}
    def resp(model):
        p = LX.Parsed()
        for h in (1, 2):
            part_ids = ids[:75] if h == 1 else ids[75:]
            f = os.path.join(D, "llm", f"resp_{SET}_{model}_{h}.txt")
            r = LX.parse_response(open(f, encoding="utf-8").read(), part_ids, texts) if os.path.exists(f) else LX.Parsed(errors={i: ["NO_FILE"] for i in part_ids})
            p.graphs.update(r.graphs); p.errors.update(r.errors)
        return p
    OS, _ = load(f"annot_{SET}_S", f"{SET}_cases.json"); OO, _ = load(f"annot_{SET}_O", f"{SET}_cases.json")
    return ids, resp("sonnet"), resp("opus"), OS, OO


def merge(parts):
    ids, NS, NO, OS, OO = [], LX.Parsed(), LX.Parsed(), {}, {}
    for i_, a, b, c, d in parts:
        ids += i_; NS.graphs.update(a.graphs); NS.errors.update(a.errors); NO.graphs.update(b.graphs); NO.errors.update(b.errors); OS.update(c); OO.update(d)
    return ids, NS, NO, OS, OO


def agg(pairs):
    sc = [fidelity.score(r, g) for r, g in pairs]
    if not sc: return "-"
    a = fidelity.aggregate(sc)
    return f"exact {a['exact_graph']:.3f} | F1 {a['overall']['f1']:.3f} | core {a['core']['f1']:.3f}" if a.get("core") else f"exact {a['exact_graph']:.3f}"


def report(title, ids, NS, NO, OS, OO, norm=False):
    n = len(ids)
    if norm:
        f = LX.normalize_graph
        NS = LX.Parsed({i: f(g) for i, g in NS.graphs.items()}, NS.errors); NO = LX.Parsed({i: f(g) for i, g in NO.graphs.items()}, NO.errors)
        OS = {i: f(g) for i, g in OS.items()}; OO = {i: f(g) for i, g in OO.items()}
    refs = {"old-Sonnet": OS, "old-Opus": OO}
    fp = lambda g: g.fingerprint(include_unrepresented=False)
    print(f"# {title}\n")
    print(f"prompt id `{LX.prompt_id()}` (guide + registry {LX.R.REGISTRY_VERSION}); {n} unseen texts; two independent calls per text (Sonnet, Opus).\n")
    print(f"Parse/validation of the NEW calls: Sonnet valid {len(NS.graphs)}/{n}, Opus valid {len(NO.graphs)}/{n} (invalid or missing: {len(NS.errors)} / {len(NO.errors)}).\n")
    print("## Single call vs references (agreement with an independent annotation of the same text; mean over the two references)\n| call | valid n | agreement with references |\n|---|---|---|")
    for nm, P in (("new Sonnet", NS), ("new Opus", NO)):
        print(f"| {nm} | {len(P.graphs)} | {agg([(R_[i], g) for i, g in P.graphs.items() for R_ in refs.values() if i in R_])} |")
    for pol in ("exact", "core"):
        acc, abst, inv = [], [], []
        for i in ids:
            if i not in NS.graphs or i not in NO.graphs: inv.append(i); continue
            r = LX.decide([NS.graphs[i], NO.graphs[i]], pol)
            (acc if r.status == "ACCEPT" else abst).append((i, r))
        print(f"\n## Wrapper, policy `{pol}`: ACCEPT {len(acc)} / {n} ({len(acc)/n:.1%}), ABSTAIN {len(abst)}, invalid-call {len(inv)}")
        print("| subset | n | agreement of the accepted/first graph with references |\n|---|---|---|")
        for nm, S_ in (("accepted", acc), ("abstained (first call's graph, for contrast)", abst)):
            print(f"| {nm} | {len(S_)} | {agg([(R_[i], (r.graph or NS.graphs[i])) for i, r in S_ for R_ in refs.values() if i in R_])} |")
        both = [(i, r) for i, r in acc if i in OS and i in OO and fp(OS[i]) == fp(OO[i])]
        ok = sum(1 for i, r in acc if fp(r.graph) in (fp(OS[i]), fp(OO[i])))
        print(f"\nAccepted graphs identical to at least one reference: {ok}/{len(acc)} ({ok/max(len(acc),1):.1%}); identical to BOTH references where the references agree: {sum(1 for i, r in both if fp(r.graph) == fp(OS[i]))}/{len(both)}.")
        if pol == "core": print(f"Accepted by core agreement only (auxiliary links differ): {sum(1 for i, r in acc if r.agreement == 'core')}")
    print(f"\nContext: the two references agree with each other at: {agg([(OO[i], OS[i]) for i in ids if i in OS and i in OO])}")


if __name__ == "__main__":
    NORM = "--norm" in sys.argv
    sys.argv = [a for a in sys.argv if a != "--norm"]
    SET = sys.argv[1] if len(sys.argv) > 1 else "blind3"          # blind3 | blind4 | pooled
    if SET == "pooled":
        report("AIXL 0.4 LLM wrapper with abstention — pooled blind3 + blind4 (benchmarks/atoms_wrapper_eval.py pooled)", *merge([load_set("blind3"), load_set("blind4")]), norm=NORM)
    else:
        report(f"AIXL 0.4 LLM wrapper with abstention — evidence on {SET} (generated by benchmarks/atoms_wrapper_eval.py {SET})", *load_set(SET), norm=NORM)
