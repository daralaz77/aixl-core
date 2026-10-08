"""Evaluate the rule-based pipeline on blind case sets written by OTHER models (no access to the repo).
Same predict() as sil5x100_eval. usage: python -m benchmarks.blind10_eval FILE.jsonl [--show N]"""
import collections
import json
import sys

from benchmarks.sil5x100_eval import LABELS, predict


def main():
    path = sys.argv[1]; show = int(sys.argv[sys.argv.index("--show") + 1]) if "--show" in sys.argv else 0
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    for r in rows:
        r["pred"] = predict(r)
        if r["label"] == "AMBIGUOUS" and r["pred"] == "UNAMBIGUOUS": pass
    conf = collections.defaultdict(collections.Counter)
    for r in rows: conf[r["label"]][r["pred"]] += 1
    tot = 0
    for lab in LABELS:
        n = sum(conf[lab].values()); ok = conf[lab][lab]; tot += ok
        print(f"{lab:22s} {ok:3d}/{n}  " + ", ".join(f"{k}={v}" for k, v in conf[lab].most_common() if k != lab))
    print(f"overall {tot}/{len(rows)} = {100*tot/len(rows):.1f}%")
    if show:
        for r in rows:
            if r["pred"] != r["label"]:
                print(f'[{r["label"]}->{r["pred"]}] {r["a"]} || {r.get("b","")}'); show -= 1
                if not show: break


if __name__ == "__main__":

    main()
