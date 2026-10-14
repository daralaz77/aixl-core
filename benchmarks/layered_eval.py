"""Does putting the deterministic layers IN FRONT of the arbiter help, on stored judgments (no model is called)?
Sets with recorded judge outputs: blind17 (Sonnet, Haiku, Haiku-b), blind18 (Sonnet, Haiku). Labels come from the authors' files.
Arms: arbiter 2-of-2 alone | layered (deterministic first, arbiter for the abstained).   python -m benchmarks.layered_eval"""
import csv
import json
import os

from aixl.arbiter import layered_decide

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETS = {"blind17": ["judge_sonnet.tsv", "judge_haiku.tsv"], "blind18": ["judge_sonnet.tsv", "judge_haiku.tsv"]}


def load(set_name):
    d = os.path.join(ROOT, "data", set_name)
    labels = {}
    for f in os.listdir(d):
        if f.startswith("author") and f.endswith(".jsonl"):
            for line in open(os.path.join(d, f), encoding="utf-8"):
                r = json.loads(line)
                labels[r["id"]] = "SAME" if r["expected_equivalence"] == "EQUIVALENT" else "DIFF" if r["expected_equivalence"] == "NOT_EQUIVALENT" else None
    texts = {r["id"]: (r["a"], r["b"]) for r in map(json.loads, open(os.path.join(d, "judge_input.jsonl"), encoding="utf-8"))}
    judges = {}
    for jf in SETS[set_name]:
        votes = {}
        for row in csv.reader(open(os.path.join(d, jf), encoding="utf-8"), delimiter="\t"):
            if len(row) >= 2:
                votes[row[0].strip()] = row[1].strip().upper()
        judges[jf.replace(".tsv", "")] = votes
    return labels, texts, judges


def main():
    tot = dict(n=0, arb_same=0, arb_false=0, lay_same=0, lay_false=0, lay_det_same=0, lay_det_diff=0, lay_det_wrong=0, lay_unsure=0,
               lay_diff_ok=0, same_total=0, diff_total=0, arb_diff_ok=0)
    for s in SETS:
        labels, texts, votes = load(s)
        for i, (a, b) in texts.items():
            lab = labels.get(i)
            if lab is None:
                continue
            fns = {n: (lambda a_, b_, v=v, i=i: v.get(i, "")) for n, v in votes.items()}
            from aixl.arbiter import consensus
            arb = consensus({n: votes[n].get(i, "") for n in votes})["verdict"]
            lay = layered_decide(a, b, fns)
            tot["n"] += 1
            tot["same_total"] += lab == "SAME"; tot["diff_total"] += lab == "DIFF"
            tot["arb_same"] += arb == "SAME" and lab == "SAME"; tot["arb_false"] += arb == "SAME" and lab == "DIFF"
            tot["arb_diff_ok"] += arb == "DIFFERENT" and lab == "DIFF"
            tot["lay_same"] += lay.verdict == "SAME" and lab == "SAME"; tot["lay_false"] += lay.verdict == "SAME" and lab == "DIFF"
            tot["lay_diff_ok"] += lay.verdict == "DIFFERENT" and lab == "DIFF"
            tot["lay_unsure"] += lay.verdict == "UNSURE"
            if lay.source == "deterministic":
                tot["lay_det_same" if lay.verdict == "SAME" else "lay_det_diff"] += 1
                tot["lay_det_wrong"] += (lay.verdict == "SAME" and lab == "DIFF") or (lay.verdict == "DIFFERENT" and lab == "SAME")
    t = tot
    print(f"pairs {t['n']} (SAME {t['same_total']}, DIFF {t['diff_total']})")
    print(f"arbiter 2-of-2 alone : proven SAME {t['arb_same']}/{t['same_total']}, FALSE SAME {t['arb_false']}, DIFF found {t['arb_diff_ok']}/{t['diff_total']}")
    print(f"layered              : proven SAME {t['lay_same']}/{t['same_total']}, FALSE SAME {t['lay_false']}, DIFF found {t['lay_diff_ok']}/{t['diff_total']}, UNSURE {t['lay_unsure']}")
    print(f"  decided without a judge: {t['lay_det_same'] + t['lay_det_diff']} (SAME {t['lay_det_same']}, DIFFERENT {t['lay_det_diff']}); wrong among them: {t['lay_det_wrong']}")


if __name__ == "__main__":
    main()
