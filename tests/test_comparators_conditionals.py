"""Comparators (CMP=) and conditional connectives (COND=) are modelled, not just detected: a flipped bound or connective must change the
graph, and spelling variants of the same bound must not. Guarded end-to-end by benchmarks/logic_pairs_eval.py over data/arena/logic_pairs.jsonl."""
import json
import os

import pytest

import aixl
from aixl.translators.auto import to_graph_auto as tg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cons(text):
    return {c for c in tg(text).canonical()["constraints"]}


@pytest.mark.parametrize("text,expect", [
    ("Archive tickets with more than 5 attachments.", "CMP=GT:5"),
    ("Archiva tickets con al menos 5 adjuntos.", "CMP=GE:5"),
    ("Archive tickets with fewer than 5 attachments.", "CMP=LT:5"),
    ("Archive tickets with no more than 5 attachments.", "CMP=LE:5"),
])
def test_comparator_emitted(text, expect):
    assert any(expect in c for c in cons(text)), cons(text)


def test_comparator_bounds_differ():
    assert cons("Archive tickets with more than 5 attachments.") != cons("Archive tickets with at least 5 attachments.")


def test_no_fewer_than_is_single_comparator():
    c = [x for x in cons("Archive tickets with no fewer than 3 attachments.") if "CMP=" in x]
    assert len(c) == 1 and "CMP=GE:3" in c[0]


def test_number_spelling_is_canonical():
    assert cons("Keep scores >= .9") == cons("Keep scores >= 0.90")


def test_condition_connectives():
    assert any("COND=UNLESS" in c for c in cons("Notify the team unless the report is approved."))
    assert cons("Notify the team if the report is approved.") != cons("Notify the team unless the report is approved.")


def test_affirmation_and_question_are_not_conditions():
    assert not any("COND=" in c for c in cons("Si, muestrame las ventas."))


def test_logic_pairs_have_no_defects():
    import benchmarks.logic_pairs_eval as L
    rows = [json.loads(x) for x in open(os.path.join(ROOT, "data", "arena", "logic_pairs.jsonl"), encoding="utf-8") if x.strip()]
    bad = []
    for r in rows:
        if r["label"] != "DIFF":
            continue
        v = aixl.compare_verified(r["a"], r["b"])
        if v.get("verdict") == "EQUIVALENT" and v.get("verified"):
            bad.append((r["a"], r["b"]))
    assert not bad, bad
    assert L  # module imports cleanly


def test_noun_extension_represents_objects_and_never_drops_them():
    """aixl/resources/nouns_v1.json: an object noun must reach the graph (previously 'Delete the backups' == 'Delete the files' == 'Delete')."""
    import json
    assert aixl.compare("Delete the backups.", "Delete the files.").equivalent is False
    assert aixl.compare("Borra los respaldos.", "Delete the backups.").equivalent
    ents = json.load(open(os.path.join(ROOT, "aixl", "resources", "nouns_v1.json"), encoding="utf-8"))["entities"]
    assert "INVOICE" not in ents      # reserved: out-of-lexicon exemplar of the silent-loss benchmark and of the extension guide
