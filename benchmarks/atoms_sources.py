"""Uniform access to every stored annotation/LLM response set: sources[(set)][name] = {id: AtomGraph}.
dev sets (rules may be mined from them): blind1v3, blind2, blind3.  Held-out: blind4 (never mined)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atoms_gold import D, load

from aixl.atoms import llm_extract as LX

DEV = ("blind1v3", "blind2", "blind3")
HELD = ("blind4",)
_CASES = {"blind1v3": "blind1_cases.json", "blind2": "blind2_cases.json", "blind3": "blind3_cases.json", "blind4": "blind4_cases.json", "blind5": "blind5_cases.json"}
_PREFIX = {"blind1v3": "annot_b1v3", "blind2": "annot_blind2", "blind3": "annot_blind3", "blind4": "annot_blind4", "blind5": "annot_blind5"}


def texts(s):
    return {c["id"]: c["text"] for c in json.load(open(os.path.join(D, _CASES[s]), encoding="utf-8"))}


def sources(s):
    out = {}
    for tag in ("S", "O"):
        if os.path.exists(os.path.join(D, f"{_PREFIX[s]}_{tag}_1.jsonl")):
            out["ann-" + tag], _ = load(f"{_PREFIX[s]}_{tag}", _CASES[s])
    ids = list(texts(s))
    for m in ("sonnet", "opus"):
        p = LX.Parsed()
        for h in (1, 2):
            f = os.path.join(D, "llm", f"resp_{s}_{m}_{h}.txt")
            if os.path.exists(f):
                r = LX.parse_response(open(f, encoding="utf-8").read(), ids[:75] if h == 1 else ids[75:], texts(s)); p.graphs.update(r.graphs)
        if p.graphs: out["llm-" + m] = p.graphs
    return out
