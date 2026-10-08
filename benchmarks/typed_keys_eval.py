"""ADR-017 option 2 experiment: an LLM emits, per text and independently, {verbs, terms, markers, typed} with English lemmas;
the Core VERIFIES deterministically and compares the keys. Verification (no LLM involved):
  V1 every declared surface word is a token of the text;   V2 every content token of the text is covered (verbs|terms|typed|lexicon|function words);
  V3 every declared marker has textual evidence, and every marker the deterministic extractor finds is declared (alias ALL~EVERY).
A side failing any check is INVALID -> the pair is INCONCLUSIVE.  Keys equal -> EQUIVALENT; opposed markers -> NOT_EQUIVALENT; else DIFFERENT.
usage: python -m benchmarks.typed_keys_eval 'data/blind10/ex2_out_*.jsonl'"""
import json, glob, sys, collections
from aixl.core.completeness import extract_markers, MARKERS, SHORT_FUNCTION, _CLOSED, marker_conflicts, _norm, _ALLTOK
from aixl.core.lexicon_gaps import FUNCTION_WORDS, _known, _forms
from aixl.core.normalizer import STOP

ALIAS = {"ALL": {"ALL", "EVERY"}, "EVERY": {"ALL", "EVERY"}}
EXTRA_EVIDENCE = {"ALL": "all every each cada todos todas todo toda tudo whole entire".split(), "NEG": "not no never nunca nao without sin sem nor neither ni dont doesnt cannot prohibido forbidden prohibited proibido unpaid unable".split()}

def evidence_ok(m, toks):
    words = set(w for w in MARKERS.get(m, []) if " " not in w) | set(EXTRA_EVIDENCE.get(m, []))
    phrases = [p for p in MARKERS.get(m, []) if " " in p]
    s = " ".join(toks)
    return bool(words & set(toks)) or any(p in s for p in phrases)

def verify(text, rec):
    toks = _ALLTOK.findall(_norm(text))
    keys = {_norm(k).strip() for d in (rec.get("verbs", {}), rec.get("terms", {})) for k in d}
    for k in keys:
        if not all(t in toks for t in _ALLTOK.findall(k)):
            return False, "V1:" + k
    typed_txt = _norm(" ".join(rec.get("typed", [])))
    covered = set(t for k in keys for t in _ALLTOK.findall(k))
    marker_words = set(w for ws in MARKERS.values() for w in ws if " " not in w) | set(w for ws in EXTRA_EVIDENCE.values() for w in ws)
    for t in toks:
        if t in covered or t in marker_words or t in FUNCTION_WORDS or t in STOP or t in SHORT_FUNCTION or t in _CLOSED:
            continue
        if t[0].isdigit() and t in typed_txt: continue
        if any((f in typed_txt) if f[0].isdigit() else _known(f) for f in _forms(t)): continue
        return False, "V2:" + t
    declared = set(rec.get("markers", []))
    for m in declared:
        if m not in MARKERS or not evidence_ok(m, toks):
            return False, "V3-evidence:" + m
    found = extract_markers(text)
    for m in found:
        if not (ALIAS.get(m, {m}) & declared):
            return False, "V3-omitted:" + m
    return True, ""

def key_of(rec):
    return (frozenset(rec.get("verbs", {}).values()), frozenset(rec.get("terms", {}).values()),
            frozenset(m if m != "EVERY" else "ALL" for m in rec.get("markers", [])), frozenset(rec.get("typed", [])))

def main():
    T = json.load(open("data/blind10/ex2_texts.json")); txt = {t["tid"]: t["text"] for t in T}
    gold = {}
    for s in ("opus", "haiku"):
        for l in open(f"data/blind10/{s}.jsonl"):
            r = json.loads(l); gold[r["id"]] = r
    recs = {}
    for p in glob.glob(sys.argv[1]):
        for l in open(p):
            l = l.strip()
            if not l.startswith("{"): continue
            try: r = json.loads(l); recs[r["id"]] = r
            except Exception: pass
    by = {}
    for t in T: by.setdefault(t["id"], {})[t["side"]] = t["tid"]
    ok = {}; why = collections.Counter(); invalid_sides = 0
    for tid, r in recs.items():
        v, w = verify(txt[tid], r); ok[tid] = v
        if not v: why[w.split(":")[0] + ":" + w.split(":", 1)[1][:0]] += 1; invalid_sides += 1
    res = collections.Counter(); false_eq = []
    for pid, s in by.items():
        a, b = s["a"], s["b"]
        if a not in recs or b not in recs: res[(gold[pid]["label"], "MISSING")] += 1; continue
        if not (ok[a] and ok[b]): v = "INCONCLUSIVE"
        else:
            ma, mb = set(recs[a].get("markers", [])), set(recs[b].get("markers", []))
            ma = {"ALL" if x == "EVERY" else x for x in ma}; mb = {"ALL" if x == "EVERY" else x for x in mb}
            if marker_conflicts(ma, mb)[0]: v = "NOT_EQUIVALENT"
            else: v = "EQUIVALENT" if key_of(recs[a]) == key_of(recs[b]) else "DIFFERENT"
        res[(gold[pid]["label"], v)] += 1
        if v == "EQUIVALENT" and gold[pid]["label"] != "EQUIVALENT": false_eq.append((pid, txt[a][:60], txt[b][:60]))
    n = lambda lab: sum(c for (l, _), c in res.items() if l == lab)
    for lab in ("EQUIVALENT", "NOT_EQUIVALENT", "PARTIALLY_EQUIVALENT", "CONTRADICTORY"):
        print(f"{lab:21s} n={n(lab):3d}  EQUIVALENT {res[(lab,'EQUIVALENT')]:3d} | DIFFERENT/NOT {res[(lab,'DIFFERENT')]+res[(lab,'NOT_EQUIVALENT')]:3d} | INCONCLUSIVE {res[(lab,'INCONCLUSIVE')]:3d} | missing {res[(lab,'MISSING')]}")
    ne = sum(n(l) for l in ("NOT_EQUIVALENT", "PARTIALLY_EQUIVALENT", "CONTRADICTORY"))
    fe = sum(res[(l, "EQUIVALENT")] for l in ("NOT_EQUIVALENT", "PARTIALLY_EQUIVALENT", "CONTRADICTORY"))
    print(f"FALSE-EQUIVALENT {fe}/{ne} = {100*fe/max(1,ne):.1f}% | EQUIVALENT proven {res[('EQUIVALENT','EQUIVALENT')]}/{n('EQUIVALENT')} = {100*res[('EQUIVALENT','EQUIVALENT')]/max(1,n('EQUIVALENT')):.1f}% | invalid sides {invalid_sides}/{len(recs)}")
    print("invalid reasons:", why.most_common(8))
    for f in false_eq[:12]: print("  false-EQ:", f)

main()
