from aixl.handoff import KINDS, handoff_check, present_kinds


def test_complete_instruction_is_ready():
    r = handoff_check("Send the report to Ana before Friday at 5 pm.", ["DATE", "NAME"])
    assert r["ok"] and r["state"] == "ready"


def test_missing_deadline_asks_the_sender():
    r = handoff_check("Send the report to Ana.", ["DATE", "NAME"])
    assert not r["ok"] and r["state"] == "input-required" and r["missing"] == ["DATE"]


def test_missing_everything():
    r = handoff_check("Send the report.", ["DATE", "NUMBER", "NAME"])
    assert r["missing"] == ["DATE", "NUMBER", "NAME"]


def test_unknown_kind_is_an_error_not_satisfied():
    r = handoff_check("Send the report to Ana.", ["DEADLINE"])
    assert not r["ok"] and r["state"] == "invalid-contract" and r["unknown_kinds"] == ["DEADLINE"]


def test_use_limit_and_condition_kinds():
    assert present_kinds("Confidential. Send it if the audit closes.") >= {"USE_LIMIT", "CONDITION"}


def test_empty_requirements_are_trivially_ready():
    assert handoff_check("anything", [])["state"] == "ready"


def test_kinds_are_closed():
    assert set(KINDS) == {"DATE", "NUMBER", "NAME", "CONDITION", "USE_LIMIT"}


def test_lowercase_name_is_not_seen_by_name__documented_limit():
    """A lower-case name is invisible to NAME (measured: 0 of 50 lower-case lines); the contract must not claim otherwise."""
    assert handoff_check("manda el informe a lucia", ["NAME"])["state"] == "input-required"
    assert handoff_check("Manda el informe a Lucia", ["NAME"])["ok"]
