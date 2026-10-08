"""Evaluate the code on the BLIND dataset (authors never saw the code). Positive class = EQUIVALENT.
usage: python -m benchmarks.blind_eval [--out results.json]"""
import json, os, time, argparse
from aixl import compare, detect_ambiguity, detect_contradiction
from aixl.translators.natural_to_semantic import to_graph
from aixl.serialization import aixl_codec
from benchmarks.metrics import prf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRIT_DIMS = {"NEGATION", "QUANTITY", "TIME", "CONSTRAINTS", "CONDITIONS", "REFERENCES", "MODIFIERS"}
CRIT_CATS = {"NEGATION", "QUANTITY", "TIME", "CONSTRAINT", "CONDITION", "REFERENCE"}
PRESERVE = {"negation": "negation", "quantity": "quantities", "time": "time", "constraint": "constraints", "condition": "conditions", "reference": "references"}


def load(name, folder="blind"):
    with open(os.path.join(ROOT, "data", folder, name), encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def run(round_=1):
    if round_ == 1:
        pairs = load("pairs_A.jsonl") + load("pairs_B.jsonl")
        items = load("items_C.jsonl")
    elif round_ == 2:
        pairs = load("pairs_A2.jsonl", "blind2") + load("pairs_B2.jsonl", "blind2")
        items = []
    elif round_ == 3:
        pairs = load("pairs_A3.jsonl", "blind3") + load("pairs_B3.jsonl", "blind3")
        items = []
    else:
        pairs = load("pairs_A4.jsonl", "blind4") + load("pairs_B4.jsonl", "blind4")
        items = []
    rows, t0 = [], time.perf_counter()
    for p in pairs:
        r = compare(p["a"], p["b"])
        rows.append({**p, "pred_equivalent": r.equivalent, "drift_level": r.drift_level, "fields": sorted({d.field for d in r.differences}),
                     "similarity": round(r.similarity, 3)})
    lat = (time.perf_counter() - t0) / len(pairs) * 1000
    tp = sum(1 for r in rows if r["label"] == "EQUIVALENT" and r["pred_equivalent"])
    fn = sum(1 for r in rows if r["label"] == "EQUIVALENT" and not r["pred_equivalent"])
    fp = sum(1 for r in rows if r["label"] == "NOT_EQUIVALENT" and r["pred_equivalent"])
    tn = sum(1 for r in rows if r["label"] == "NOT_EQUIVALENT" and not r["pred_equivalent"])
    eq = prf(tp, fp, fn, tn)
    # S2: drift detection on the critical subset of NOT_EQUIVALENT pairs
    crit = [r for r in rows if r["label"] == "NOT_EQUIVALENT" and r["category"] in CRIT_CATS]
    det = [r for r in crit if (not r["pred_equivalent"]) and r["drift_level"] in ("MAJOR_DRIFT", "CRITICAL_DRIFT")]
    drift = {"critical_pairs": len(crit), "detected": len(det), "rate": round(len(det) / len(crit), 4) if crit else None}
    # S3: preservation through text -> graph -> AIXL -> graph, per element, on every blind text
    pres = {k: [0, 0] for k in PRESERVE.values()}
    for p in pairs:
        for t in (p["a"], p["b"]):
            g = to_graph(t); back = aixl_codec.decode(aixl_codec.encode(g))
            c1, c2 = g.canonical(), back.canonical()
            for dim in pres:
                if c1[dim]:
                    pres[dim][1] += 1; pres[dim][0] += (c1[dim] == c2[dim])
    preservation = {k: {"preserved": v[0], "with_element": v[1], "rate": round(v[0] / v[1], 4) if v[1] else None} for k, v in pres.items()}
    tot = [sum(v[0] for v in pres.values()), sum(v[1] for v in pres.values())]
    preservation["overall"] = round(tot[0] / tot[1], 4) if tot[1] else None
    full = sum(1 for p in pairs for t in (p["a"], p["b"]) if to_graph(t).canonical() == aixl_codec.decode(aixl_codec.encode(to_graph(t))).canonical())
    preservation["full_canonical_roundtrip"] = round(full / (2 * len(pairs)), 4)
    # dimension attribution on minimal pairs that the code separated
    # S4: ambiguity + contradiction
    amb = [i for i in items if "label" in i and i["label"] in ("AMBIGUOUS", "NOT_AMBIGUOUS")]
    con = [i for i in items if i.get("label") in ("CONTRADICTION", "NO_CONTRADICTION")]
    amb_rows = [{**i, "pred": detect_ambiguity(i["text"]).ambiguous} for i in amb]
    con_rows = [{**i, "pred": detect_contradiction(i["a"], i["b"]).contradiction} for i in con]
    ambm = prf(sum(1 for r in amb_rows if r["label"] == "AMBIGUOUS" and r["pred"]), sum(1 for r in amb_rows if r["label"] == "NOT_AMBIGUOUS" and r["pred"]),
               sum(1 for r in amb_rows if r["label"] == "AMBIGUOUS" and not r["pred"]), sum(1 for r in amb_rows if r["label"] == "NOT_AMBIGUOUS" and not r["pred"]))
    conm = prf(sum(1 for r in con_rows if r["label"] == "CONTRADICTION" and r["pred"]), sum(1 for r in con_rows if r["label"] == "NO_CONTRADICTION" and r["pred"]),
               sum(1 for r in con_rows if r["label"] == "CONTRADICTION" and not r["pred"]), sum(1 for r in con_rows if r["label"] == "NO_CONTRADICTION" and not r["pred"]))
    by_cat = {}
    for r in rows:
        k = r["category"]; b = by_cat.setdefault(k, [0, 0]); b[1] += 1
        b[0] += ((r["label"] == "EQUIVALENT") == r["pred_equivalent"])
    if not items:
        ambm = conm = None
    return {"equivalence": eq, "drift_critical": drift, "preservation": preservation, "ambiguity": ambm, "contradiction": conm,
            "accuracy_by_category": {k: {"correct": v[0], "n": v[1], "acc": round(v[0] / v[1], 3)} for k, v in sorted(by_cat.items())},
            "latency_ms_per_compare": round(lat, 3)}, rows, amb_rows, con_rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out"); ap.add_argument("--round", type=int, default=1); a = ap.parse_args()
    summary, rows, amb_rows, con_rows = run(a.round)
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    if a.out:
        json.dump({"summary": summary, "pairs": rows, "ambiguity": amb_rows, "contradiction": con_rows}, open(a.out, "w"), ensure_ascii=False, indent=1)
