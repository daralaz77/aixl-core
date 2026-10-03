"""Evaluate the §39 adversarial suite. Per attack: detected = NOT equivalent (the manipulation did not pass as
the same meaning); critical = drift level CRITICAL_DRIFT (for families whose ground truth is 'critical');
payload_ambiguity additionally counts as detected if detect_ambiguity(manipulated) fires.
Controls: false alarm = a benign restatement flagged as different.
usage: python -m benchmarks.sil_security_eval [--show N]"""
import json, os, argparse, collections
from aixl import compare, detect_drift, detect_ambiguity

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAMILIES = ["negation_removal", "constraint_removal", "permission_escalation", "reference_substitution",
            "instruction_injection", "scope_widening", "quantity_tamper", "time_tamper", "payload_ambiguity"]


def load(fam):
    with open(os.path.join(ROOT, "data", "sil_security", fam + ".jsonl"), encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def judge(row):
    r = compare(row["a"], row["b"])
    d = detect_drift(row["a"], row["b"])
    blocking = any(w.get("severity") == "BLOCKING" for w in r.warnings)      # "cannot verify" is a flag, never a pass
    detected = (not r.equivalent) or blocking or (row.get("check_ambiguity") and detect_ambiguity(row["b"]).ambiguous)
    return {**row, "detected": bool(detected), "critical_flag": d.critical, "level": d.level,
            "fields": sorted({x.field for x in r.differences})}


def run():
    return {fam: [judge(r) for r in load(fam)] for fam in FAMILIES + ["control", "hard"]}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--show", type=int, default=0)
    args = ap.parse_args()
    res = run()
    print(f"{'family':24s} n   detected  critical(of those expected critical)")
    tot_d = tot_n = 0
    for fam in FAMILIES:
        rows = res[fam]
        det = sum(r["detected"] for r in rows)
        exp = [r for r in rows if r.get("critical")]                 # ground truth: manipulation removes a protection
        crit = sum(1 for r in exp if r["critical_flag"]) if exp else None
        tot_d += det; tot_n += len(rows)
        print(f"{fam:24s} {len(rows):3d} {det:4d}/{len(rows):<3d}  " + (f"{crit}/{len(exp)}" if exp else "n/a"))
    print(f"ALL ATTACKS DETECTED {tot_d}/{tot_n} = {100*tot_d/tot_n:.1f}%  (undetected = judged same meaning: {tot_n-tot_d})")
    hard = res["hard"]
    print(f"\nHARD tier (hand-written natural phrasings): n={len(hard)}")
    by = collections.defaultdict(list)
    for r in hard:
        by[r["family"]].append(r)
    for fam, rows in by.items():
        print(f"  {fam:24s} detected {sum(r['detected'] for r in rows)}/{len(rows)}   critical {sum(r['critical_flag'] for r in rows)}/{len(rows)}")
    print(f"  HARD detected {sum(r['detected'] for r in hard)}/{len(hard)}, critical {sum(r['critical_flag'] for r in hard)}/{len(hard)}")
    ctr = res["control"]
    fa = sum(r["detected"] for r in ctr)
    print(f"controls: false alarms {fa}/{len(ctr)}")
    if args.show:
        for fam in FAMILIES:
            for r in [x for x in res[fam] if not x["detected"]][:args.show]:
                print("MISSED", fam, "|", r["a"], "=>", r["b"])
            for r in [x for x in res[fam] if x.get("critical") and not x["critical_flag"]][:args.show]:
                print("NOT-CRITICAL", fam, r["level"], "|", r["a"], "=>", r["b"], r["fields"])
        for r in [x for x in hard if not x["detected"] or not x["critical_flag"]][:args.show * 12]:
            print("HARD-" + ("MISSED" if not r["detected"] else "NOT-CRITICAL"), r["family"], "|", r["a"], "=>", r["b"])
        for r in [x for x in ctr if x["detected"]][:args.show]:
            print("FALSE-ALARM |", r["a"], "=>", r["b"])


if __name__ == "__main__":
    main()
