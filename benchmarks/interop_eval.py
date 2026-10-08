"""E-INTEROP: cross-vendor ENCODING consistency (not judge accuracy). Two independent encoders
(Sonnet, Gemini) each encode the SAME 100 standalone texts with the SAME frozen card; for each text
we compare their two AIXL outputs to each other. No gold label is involved -- this measures whether
two vendors converge, not whether either is "right"."""
import json
import os
import re
from collections import Counter

from aixl.core.comparator import compare_graphs
from aixl.serialization import aixl_codec

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    d = {}
    for l in open(path, encoding="utf-8"):
        m = re.match(r"^\s*(t\d{3})\s*::\s*(.+?)\s*$", l)
        if m: d[m.group(1)] = m.group(2).strip("`")
    return d


def run():
    texts = json.load(open(os.path.join(ROOT, "data", "interop", "texts_interop1.json"), encoding="utf-8"))
    sonnet = read(os.path.join(ROOT, "data", "interop", "sonnet_answers.txt"))
    gemini = read(os.path.join(ROOT, "data", "interop", "gemini_answers_raw.txt"))
    rows, perr = [], Counter()
    for t in texts:
        tid = t["tid"]
        gs = ge = None
        try: gs = aixl_codec.decode(sonnet[tid])
        except Exception: perr["sonnet"] += 1
        try: ge = aixl_codec.decode(gemini[tid])
        except Exception: perr["gemini"] += 1
        if gs is None or ge is None:
            rows.append({**t, "consistent": False, "level": "PARSE_ERROR", "diff_fields": ["PARSE_ERROR"]})
            continue
        r = compare_graphs(gs, ge)
        rows.append({**t, "consistent": r.equivalent, "level": r.drift_level,
                     "diff_fields": sorted({d.field for d in r.differences})})
    n = len(rows)
    consistent = sum(r["consistent"] for r in rows)
    field_counts = Counter(f for r in rows for f in r["diff_fields"])
    level_counts = Counter(r["level"] for r in rows if not r["consistent"])
    summary = {
        "n": n, "consistent": consistent, "consistency_rate": round(consistent / n, 4),
        "parse_failures": dict(perr),
        "disagreement_drift_levels": dict(level_counts),
        "disagreement_fields": dict(field_counts.most_common()),
    }
    return summary, rows


if __name__ == "__main__":
    s, rows = run()
    print(json.dumps(s, ensure_ascii=False, indent=1))
