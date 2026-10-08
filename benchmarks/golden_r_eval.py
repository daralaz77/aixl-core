"""Score a system against the 0.3-R golden set (data/golden_r). Reports SAFETY first (false-equivalent), then utility.
usage: python -m benchmarks.golden_r_eval [--inconclusive] [--show]
A system is any fn(text_a, text_b) -> 'EQUIVALENT' | 'NOT_EQUIVALENT' | 'INCONCLUSIVE'; default = aixl.compare."""
import collections
import json
import os
import sys

D = os.path.join(os.path.dirname(__file__), "..", "data", "golden_r")


def load():
    texts = {r["id"]: r for r in map(json.loads, open(os.path.join(D, "texts.jsonl"), encoding="utf-8"))}
    pairs = [json.loads(l) for l in open(os.path.join(D, "pairs.jsonl"), encoding="utf-8")]
    return texts, pairs


def outcome(expected, got):
    if got == "EQUIVALENT":
        return "ok" if expected == "EQUIVALENT" else "FALSE_EQUIVALENT"
    if got == "NOT_EQUIVALENT":
        return {"NOT_EQUIVALENT": "ok", "EQUIVALENT": "FALSE_REJECT", "UNDECIDABLE": "over_decided"}[expected]
    return "ok" if expected == "UNDECIDABLE" else "inconclusive"     # INCONCLUSIVE: safe but unproven


def run(system, show=False):
    texts, pairs = load()
    res, by_cat = collections.Counter(), collections.defaultdict(collections.Counter)
    for p in pairs:
        got = system(texts[p["text_a"]]["source_text"], texts[p["text_b"]]["source_text"])
        o = outcome(p["expected_equivalence"], got)
        res[o] += 1; by_cat[p["category"]][o] += 1
        if p["expected_equivalence"] == "EQUIVALENT" and got == "EQUIVALENT": res["_proven"] += 1
        if p["expected_equivalence"] == "UNDECIDABLE" and got == "INCONCLUSIVE": res["_undecidable_flagged"] += 1
        if show and o not in ("ok", "inconclusive"):
            print(f'  {o:17} {p["id"]} {p["category"]:26} exp={p["expected_equivalence"]:14} got={got:14} {texts[p["text_a"]]["source_text"]!r} | {texts[p["text_b"]]["source_text"]!r}')
    return res, by_cat, pairs


def summary(res, pairs):
    n_neq = sum(p["expected_equivalence"] != "EQUIVALENT" for p in pairs)
    n_eq = sum(p["expected_equivalence"] == "EQUIVALENT" for p in pairs)
    fe = res["FALSE_EQUIVALENT"]
    return dict(false_equivalent=f"{fe}/{n_neq} ({100*fe/n_neq:.1f}%)", proven_equivalent=f"{res['_proven']}/{n_eq}", undecidable_flagged=res["_undecidable_flagged"],
                counts={k: v for k, v in res.items() if not k.startswith("_")}, n_pairs=len(pairs), n_expected_equivalent=n_eq)


if __name__ == "__main__":
    import aixl
    from aixl.core.ontology import load_config
    cfg = dict(load_config()); cfg["inconclusive"] = "--inconclusive" in sys.argv
    if "--semantic" in sys.argv:
        from aixl.semantic import compare_texts
        system = lambda a, b: compare_texts(a, b).verdict
    else:
        system = lambda a, b: aixl.compare(a, b, config=cfg).verdict
    res, by_cat, pairs = run(system, show="--show" in sys.argv)
    print(json.dumps(summary(res, pairs), ensure_ascii=False, indent=1))
    for c, v in sorted(by_cat.items()):
        print(f"{c:28}", dict(v))
