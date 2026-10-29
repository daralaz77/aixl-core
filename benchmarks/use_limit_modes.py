"""The two audience modes side by side on any dataset directory (data/use_limits_v5 or use_limits_v8): DEFAULT (closed audience list) vs OPEN (a strong audience verb + any group, opt-in) vs the v4 code.
Fields: kind open_audience / decoy, source, faithful_light, limit_drop.   python -m benchmarks.use_limit_modes use_limits_v8"""
import collections
import glob
import json
import os
import sys

from aixl.invariants import RELAY_FAMILIES, RELAY_FAMILIES_OPEN, check

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(d):
    rows = [json.loads(line) for p in sorted(glob.glob(os.path.join(ROOT, "data", d, "out_*.jsonl"))) for line in open(p, encoding="utf-8")]
    res = collections.defaultdict(collections.Counter)
    for r in rows:
        for arm, fams in (("default", RELAY_FAMILIES), ("open", RELAY_FAMILIES_OPEN)):
            drop = {v[0] for v in check(r["source"], r["limit_drop"], fams)}
            light = {v[0] for v in check(r["source"], r["faithful_light"], fams)}
            c = res[(r["kind"], arm)]
            c["n"] += 1
            c["drop_flag"] += bool(drop)
            c["drop_use"] += bool(drop & {"USE_LIMIT", "USE_LIMIT_OPEN"})
            c["light_use"] += bool(light & {"USE_LIMIT", "USE_LIMIT_OPEN"}) and light <= {"USE_LIMIT", "USE_LIMIT_OPEN"}
    for k in ("open_audience", "decoy"):
        for arm in ("default", "open"):
            c = res[(k, arm)]
            print(f"{k:<14}{arm:<8} drop flagged {c['drop_flag']}/{c['n']} = {100 * c['drop_flag'] / c['n']:.1f} %   by the use-limit families {c['drop_use']}/{c['n']} = {100 * c['drop_use'] / c['n']:.1f} %   "
                  f"faithful_light by them alone {c['light_use']}/{c['n']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "use_limits_v8")
