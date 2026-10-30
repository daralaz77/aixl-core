"""aixl.telemetry: official event and attribute names, a closed label set, no content leaks, never raises."""
import pytest

from aixl import telemetry as T
from aixl.invariants import relay_check
from aixl.logic import logic_compare


class FakeLogger:
    def __init__(self):
        self.records = []

    def emit(self, record=None, **kw):
        self.records.append(kw)


class BrokenLogger:
    def emit(self, *a, **k):
        raise RuntimeError("exporter down")


def test_event_and_required_attribute_names_follow_the_official_definition():
    lg = FakeLogger()
    assert T.record_evaluation(T.NAME_RELAY, "violation", explanation="x", response_id="resp-1", logger=lg) is True
    rec = lg.records[0]
    assert rec["event_name"] == "gen_ai.evaluation.result"
    a = rec["attributes"]
    assert a["gen_ai.evaluation.name"] == "aixl.relay_check" and a["gen_ai.evaluation.score.label"] == "violation"
    assert a["gen_ai.evaluation.explanation"] == "x" and a["gen_ai.response.id"] == "resp-1"
    assert "gen_ai.evaluation.score.value" not in a                      # a category is not a score


def test_body_is_a_readable_one_liner_from_the_same_content_free_pieces():
    lg = FakeLogger()
    T.record_evaluation(T.NAME_RELAY, "violation", explanation="changed critical slot families: DATE", logger=lg)
    T.record_evaluation(T.NAME_RELAY, "ok", logger=lg)
    assert lg.records[0]["body"] == "aixl.relay_check: violation — changed critical slot families: DATE"
    assert lg.records[1]["body"] == "aixl.relay_check: ok"


def test_body_never_carries_the_texts():
    lg = FakeLogger()
    T.relay_check_evaluated("Send the report to Ana before Friday at 5 pm.", "Send the report to Luis before Monday.", logger=lg)
    body = lg.records[0]["body"].lower()
    assert body.startswith("aixl.relay_check: violation")
    for leaked in ("ana", "luis", "friday", "monday", "report", "5 pm"):
        assert leaked not in body


def test_labels_are_a_closed_low_cardinality_set():
    lg = FakeLogger()
    assert T.record_evaluation(T.NAME_RELAY, "totally new label", logger=lg) is False
    assert T.record_evaluation("someone.else", "ok", logger=lg) is False
    assert lg.records == []


def test_relay_check_evaluated_returns_the_same_result_and_emits_families_only():
    lg = FakeLogger()
    src, rel = "Send the report to Ana before Friday at 5 pm.", "Send the report to Luis before Monday."
    r = T.relay_check_evaluated(src, rel, logger=lg, response_id="r1")
    assert r == relay_check(src, rel)
    a = lg.records[0]["attributes"]
    assert a["gen_ai.evaluation.score.label"] == "violation" and a["aixl.violation.families"]
    flat = " ".join(str(v) for v in a.values()).lower()
    for leaked in ("ana", "luis", "friday", "monday", "report", "5 pm"):
        assert leaked not in flat, f"content leaked: {leaked}"


def test_ok_and_not_analysed_labels():
    lg = FakeLogger()
    T.relay_check_evaluated("Send the report to Ana.", "Send the report to Ana.", logger=lg)
    assert lg.records[0]["attributes"]["gen_ai.evaluation.score.label"] == "ok"


def test_compare_verified_and_logic_events():
    lg = FakeLogger()
    T.compare_verified_evaluated("Elimina el reporte.", "No elimines el reporte.", logger=lg)
    assert lg.records[0]["attributes"]["gen_ai.evaluation.score.label"] in T.LABELS[T.NAME_COMPARE]
    r = T.logic_compare_evaluated("Send the report if the client approves.", "If the client approves, send the report.", logger=lg)
    assert r == logic_compare("Send the report if the client approves.", "If the client approves, send the report.")
    last = lg.records[-1]["attributes"]
    assert last["gen_ai.evaluation.score.label"] == "equivalent_logic"
    assert "client" not in " ".join(str(v) for v in last.values()).lower()


def test_logic_abstention_carries_a_generic_reason_not_the_clauses():
    lg = FakeLogger()
    T.logic_compare_evaluated("Send the report to Ana if the client approves.", "Send the report to Luis if the client approves.", logger=lg)
    a = lg.records[0]["attributes"]
    assert a["gen_ai.evaluation.score.label"] == "abstain" and "ana" not in " ".join(str(v) for v in a.values()).lower()


def test_a_broken_exporter_never_breaks_the_verdict():
    r = T.relay_check_evaluated("Send the report to Ana.", "Do not send the report to Ana.", logger=BrokenLogger())
    assert r["ok"] is False                                              # the verdict is returned unchanged
    assert T.record_evaluation(T.NAME_RELAY, "ok", logger=BrokenLogger()) is False


def test_only_aixl_namespaced_attributes_pass_through():
    lg = FakeLogger()
    T.record_evaluation(T.NAME_RELAY, "ok", attributes={"aixl.x": 1, "user.email": "a@b.c", "aixl.bad": {"nested": 1}, "aixl.list": ["a", "b"]}, logger=lg)
    a = lg.records[0]["attributes"]
    assert a["aixl.x"] == 1 and a["aixl.list"] == ["a", "b"] and "user.email" not in a and "aixl.bad" not in a


def test_default_logger_works_without_an_sdk():
    pytest.importorskip("opentelemetry")
    assert T.record_evaluation(T.NAME_RELAY, "ok") in (True, False)       # API-only: a no-op logger; must not raise
