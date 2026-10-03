"""AIXL 0.5 arbiter audit layer (ADR-018): rules identity, consensus, judge-output validation, decision memo. No model is ever called."""
import hashlib
import json
import os

import pytest

from aixl import arbiter as A

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_rules_are_the_ones_used_in_every_experiment():
    a = open(os.path.join(ROOT, "data", "arbiter", "rules_v1.txt"), "rb").read()
    b = open(os.path.join(ROOT, "data", "blind10", "arb_rules.txt"), "rb").read()
    assert a == b                                              # the experiment copy and the packaged copy cannot drift
    assert A.rules_id() == hashlib.sha256(a).hexdigest()[:16]
    assert "Be strict" in A.rules_text()


@pytest.mark.parametrize("v,expected_verdict,ok", [
    ({"s": "SAME", "h": "SAME"}, "SAME", True),
    ({"s": "SAME", "h": "DIFFERENT"}, "DIFFERENT", True),      # the measured safe direction: one dissent blocks "same"
    ({"s": "DIFFERENT", "h": "DIFFERENT"}, "DIFFERENT", True),
    ({"s": "SAME", "h": "UNSURE"}, "UNSURE", True),
    ({"s": "SAME"}, "UNSURE", False),                         # a single judge is never enough for ok
    ({"s": "same ", "h": " Same"}, "SAME", True),             # tolerant of case/whitespace
    ({"s": "SAME", "h": "maybe"}, "UNSURE", False),           # garbage is invalid, never a verdict
    ({"s": "DIFFERENT", "h": "maybe"}, "DIFFERENT", False),   # still blocks "same", but not ok
])
def test_consensus_truth_table(v, expected_verdict, ok):
    c = A.consensus(v)
    assert (c["verdict"], c["ok"]) == (expected_verdict, ok)


def test_parse_judge_lines_reports_missing_invalid_and_unexpected():
    out = "a1\tSAME\tok\na2\tmaybe\twhat\nzz\tSAME\tnot asked\n"
    r = A.parse_judge_lines(out, ["a1", "a2", "a3"])
    assert r["verdicts"] == {"a1": "SAME"} and r["invalid"] == ["a2"] and r["missing"] == ["a3"] and r["unexpected"] == ["zz"]


def test_pair_key_is_stable_ordered_and_sensitive_to_raw_text_rules_and_judges():
    k = A.pair_key("Send the report", "Envía el informe", ["haiku", "sonnet"])
    assert k == A.pair_key("Send the report", "Envía el informe", ["sonnet", "haiku"])          # judge order irrelevant
    assert k != A.pair_key("Envía el informe", "Send the report", ["haiku", "sonnet"])          # pair order matters (symmetry not measured)
    assert k != A.pair_key("Send the report", "Envía el informe", ["haiku"])
    assert k != A.pair_key("Send the report", "Envía el informe", ["haiku", "sonnet"], rules="other")
    assert A.pair_key("not", "x", ["j"]) != A.pair_key("n​ot", "x", ["j"])                   # a zero-width variant is a different pair


def _judge(counter, answer):
    def f(a, b):
        counter.append(1)
        return answer
    return f


def test_decision_is_stored_and_reused_without_calling_the_judges(tmp_path):
    memo = A.DecisionMemo(str(tmp_path / "memo.jsonl"))
    calls = []
    judges = {"s": _judge(calls, "SAME"), "h": _judge(calls, "SAME")}
    d1 = A.decide("Send the report to Ana", "Envía el informe a Ana", judges, memo)
    assert (d1.verdict, d1.ok, d1.from_memo, len(calls)) == ("SAME", True, False, 2)
    d2 = A.decide("Send the report to Ana", "Envía el informe a Ana", judges, memo)
    assert (d2.verdict, d2.from_memo, len(calls)) == ("SAME", True, 2)                          # judges not called again
    # a new process reading the same file sees it too
    assert A.DecisionMemo(str(tmp_path / "memo.jsonl")).get(d1.key)["verdict"] == "SAME"


def test_memo_stores_hashes_not_texts_by_default(tmp_path):
    p = tmp_path / "m.jsonl"
    A.decide("secret instruction", "another one", {"s": lambda a, b: "DIFFERENT", "h": lambda a, b: "DIFFERENT"}, A.DecisionMemo(str(p)))
    raw = p.read_text(encoding="utf-8")
    assert "secret instruction" not in raw and "a_sha256" in raw
    p2 = tmp_path / "m2.jsonl"
    A.decide("secret instruction", "another one", {"s": lambda a, b: "DIFFERENT"}, A.DecisionMemo(str(p2), store_texts=True))
    assert "secret instruction" in p2.read_text(encoding="utf-8")


def test_invalid_judge_output_is_retried_then_becomes_unsure_never_same():
    seq = iter(["garbage", "SAME"])
    d = A.decide("a", "b", {"s": lambda a, b: next(seq), "h": lambda a, b: "SAME"}, retries=1)
    assert d.verdict == "SAME" and d.retries == 1
    d = A.decide("a", "b", {"s": lambda a, b: "garbage", "h": lambda a, b: "SAME"}, retries=1)
    assert d.verdict == "UNSURE" and not d.ok and d.per_judge["s"] == "INVALID"


def test_a_failing_judge_is_an_invalid_answer_not_a_crash():
    def boom(a, b):
        raise RuntimeError("api down")
    d = A.decide("a", "b", {"s": boom, "h": lambda a, b: "SAME"}, retries=0)
    assert d.verdict == "UNSURE" and not d.ok


def test_obfuscation_is_recorded_for_audit_but_does_not_change_the_verdict():
    lookalike = "Do n" + chr(0x043E) + "t send it"                                               # Cyrillic 'o' inside 'not'
    d = A.decide("Do not send it", lookalike, {"s": lambda a, b: "SAME", "h": lambda a, b: "SAME"})
    assert d.verdict == "SAME" and d.obfuscation == ["MIXED_SCRIPT_HOMOGLYPHS"]                  # recorded, not decided on (ADR-018)
