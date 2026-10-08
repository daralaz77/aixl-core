"""Equivalence / ambiguity / contradiction metrics on the 200-case DEV dataset (DEMO set: same author as the code)."""
import json, time
from aixl import compare, detect_ambiguity, detect_contradiction
from benchmarks.dataset import load
from benchmarks.metrics import prf


def run(cases=None):
    cases = cases or load()
    pairs = [c for c in cases if "expected_equivalent" in c]
    rows, t0 = [], time.perf_counter()
    for c in pairs:
        r = compare(c["input_a"], c["input_b"])
        rows.append({**c, "pred": r.equivalent, "level": r.drift_level, "fields": sorted({d.field for d in r.differences})})
    lat = (time.perf_counter() - t0) / len(pairs) * 1000
    tp = sum(1 for r in rows if r["expected_equivalent"] and r["pred"]); fn = sum(1 for r in rows if r["expected_equivalent"] and not r["pred"])
    fp = sum(1 for r in rows if not r["expected_equivalent"] and r["pred"]); tn = sum(1 for r in rows if not r["expected_equivalent"] and not r["pred"])
    eq = prf(tp, fp, fn, tn)
    crit = [r for r in rows if r.get("expected_critical")]
    det = [r for r in crit if not r["pred"] and r["level"] in ("MAJOR_DRIFT", "CRITICAL_DRIFT")]
    amb = [{**c, "pred": detect_ambiguity(c["input_a"]).ambiguous} for c in cases if "expected_ambiguous" in c]
    con = [{**c, "pred": detect_contradiction(c["input_a"], c["input_b"]).contradiction} for c in cases if "expected_contradiction" in c]
    acc = lambda rs, key: round(sum(1 for r in rs if r[key] == r["pred"]) / len(rs), 4) if rs else None
    by_cat = {}
    for r in rows:
        b = by_cat.setdefault(r["expected_category"], [0, 0]); b[1] += 1; b[0] += (r["expected_equivalent"] == r["pred"])
    total_ok = sum(1 for r in rows if r["expected_equivalent"] == r["pred"]) + sum(1 for r in amb if r["expected_ambiguous"] == r["pred"]) + sum(1 for r in con if r["expected_contradiction"] == r["pred"])
    total = len(rows) + len(amb) + len(con)
    return {"equivalence": eq, "drift_detection_critical": {"n": len(crit), "detected": len(det), "rate": round(len(det) / len(crit), 4) if crit else None},
            "ambiguity_accuracy": acc(amb, "expected_ambiguous"), "contradiction_accuracy": acc(con, "expected_contradiction"),
            "semantic_accuracy_overall": round(total_ok / total, 4), "accuracy_by_category": {k: {"correct": v[0], "n": v[1]} for k, v in sorted(by_cat.items())},
            "latency_ms_per_compare": round(lat, 3), "n_cases": len(cases)}, rows, amb, con


if __name__ == "__main__":
    summary, rows, amb, con = run()
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    for r in rows:
        if r["expected_equivalent"] != r["pred"]:
            print("FAIL", r["id"], r["input_a"], "|", r["input_b"], "expected", r["expected_equivalent"], r["fields"])
    for r in amb:
        if r["expected_ambiguous"] != r["pred"]: print("FAIL", r["id"], r["input_a"], "expected ambiguous", r["expected_ambiguous"])
    for r in con:
        if r["expected_contradiction"] != r["pred"]: print("FAIL", r["id"], r["input_a"], "|", r["input_b"], "expected contradiction", r["expected_contradiction"])
