"""Integrity of the 0.3-R golden set (NOT a test of AIXL accuracy): schema, references, label logic, frozen hashes."""
import hashlib, json, os
from collections import Counter

D = os.path.join(os.path.dirname(__file__), "..", "data", "golden_r")
rd = lambda n: [json.loads(l) for l in open(os.path.join(D, n), encoding="utf-8")]
TEXTS, PAIRS = rd("texts.jsonl"), rd("pairs.jsonl")
BY = {t["id"]: t for t in TEXTS}


def test_hashes_frozen():
    man = json.load(open(os.path.join(D, "MANIFEST.json")))
    for n, h in man.items():
        assert hashlib.sha256(open(os.path.join(D, n), "rb").read()).hexdigest() == h, f"{n} changed: re-freeze deliberately"


def test_required_fields_and_ids():
    need = {"id", "language", "source_text", "canonical_meaning", "expected_semantic_graph", "ambiguities", "forbidden_inferences"}
    assert all(need <= set(t) for t in TEXTS)
    assert len({t["id"] for t in TEXTS}) == len(TEXTS) and len({p["id"] for p in PAIRS}) == len(PAIRS)
    assert len({t["source_text"] for t in TEXTS}) == len(TEXTS)


def test_pair_references_and_label_logic():
    for p in PAIRS:
        assert p["text_a"] in BY and p["text_b"] in BY
        assert p["expected_equivalence"] in ("EQUIVALENT", "NOT_EQUIVALENT", "UNDECIDABLE")
        if p["expected_equivalence"] == "NOT_EQUIVALENT":
            assert p["expected_diff"], p["id"]
            for d in p["expected_diff"]:
                assert d["difference_type"] in ("LOSS", "DISTORTION", "ADDITION", "SUBSTITUTION", "CONTRADICTION")
                assert d["severity"] in ("MINOR", "MODERATE", "MAJOR", "CRITICAL")
        else:
            assert not p["expected_diff"], p["id"]


def test_undecidable_pairs_declare_ambiguity():
    for p in PAIRS:
        if p["expected_equivalence"] == "UNDECIDABLE":
            assert BY[p["text_a"]]["ambiguities"] or BY[p["text_b"]]["ambiguities"], p["id"]


def test_balance_all_categories_and_both_label_classes():
    cats = Counter(p["category"] for p in PAIRS)
    assert len(cats) == 10 and min(cats.values()) >= 6
    lab = Counter(p["expected_equivalence"] for p in PAIRS)
    assert lab["EQUIVALENT"] >= 15 and lab["UNDECIDABLE"] >= 5      # guards against a set that rewards "always reject"


def test_not_equivalent_pairs_really_differ_in_meaning():
    for p in PAIRS:
        if p["expected_equivalence"] == "NOT_EQUIVALENT":
            assert BY[p["text_a"]]["canonical_meaning"] != BY[p["text_b"]]["canonical_meaning"], p["id"]
