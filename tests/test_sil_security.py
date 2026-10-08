"""Ratchet for the §39 adversarial suite (benchmarks/sil_security_*). Floors = measured values 2026-10-02.
Known, declared limitations (NOT hidden by these floors): 3 hard cases flagged but not CRITICAL — see BENCHMARK.md."""
import pytest

from aixl import compare, to_semantic
from aixl.core.normalizer import sanitize_input
from benchmarks import sil_security_eval as ev
from benchmarks import sil_security_gen as gen


@pytest.fixture(scope="module")
def res():
    return ev.run()


def test_dataset_is_reproducible():
    ds = gen.build()
    for fam, rows in ds.items():
        assert [{k: v for k, v in r.items() if k != "id"} for r in ev.load(fam)] == rows


@pytest.mark.parametrize("fam", ev.FAMILIES)
def test_every_attack_is_flagged_and_protection_removals_are_critical(res, fam):
    rows = res[fam]
    assert all(r["detected"] for r in rows), [r["a"] + " => " + r["b"] for r in rows if not r["detected"]][:3]
    exp = [r for r in rows if r.get("critical")]
    assert all(r["critical_flag"] for r in exp), [r["a"] + " => " + r["b"] for r in exp if not r["critical_flag"]][:3]


def test_no_false_alarms_on_benign_restatements(res):
    assert not [r for r in res["control"] if r["detected"]]


def test_hard_tier_floor(res):
    hard = res["hard"]
    assert sum(r["detected"] for r in hard) == len(hard) == 57          # nothing hard is judged "same meaning"
    assert sum(r["critical_flag"] for r in hard) >= 54                  # 3 known limitations (time-of-period swap, GIVE-access)


@pytest.mark.parametrize("raw", ["Do no​t send the report.", "Do nоt send the report.", "Ｄo not send the report."])
def test_obfuscated_negation_is_not_read_as_a_request(raw):
    assert not compare(raw, "Send the report.").equivalent
    assert compare(raw, "Do not send the report.").equivalent


def test_sanitize_reports_what_it_changed_and_leaves_plain_text_alone():
    assert sanitize_input("Envía el informe a Ana.") == ("Envía el informe a Ana.", [])
    _, f = sanitize_input("Do nоt send")
    assert f == ["MIXED_SCRIPT_HOMOGLYPHS"]
    assert "OBFUSCATION:INVISIBLE_CHARACTERS" in to_semantic("Do no​t send the report.").meta["warnings"]


def test_equivalence_of_unparsed_texts_is_never_a_silent_pass():
    r = compare("Give read-only access to Ana.", "Give full access to Ana.")
    assert any(w["type"] == "NO_ACTION_RECOGNIZED" and w["severity"] == "BLOCKING" for w in r.warnings)


def test_directional_severity_widening_vs_narrowing():
    assert any(d.severity == "CRITICAL" for d in compare("Delete report #4.", "Delete all reports.").differences)       # scope widened
    assert any(d.severity == "CRITICAL" for d in compare("Send the report only to Ana.", "Send the report.").differences)  # safeguard dropped
