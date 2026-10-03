"""ADR-016 step 1: INCONCLUSIVE verdict (opt-in via config['inconclusive'])."""
from aixl import compare
from aixl.core.ontology import load_config

ON = {**load_config(), "inconclusive": True}


def test_default_behaviour_unchanged():
    r = compare("Send the weekly report to the CFO by Monday", "Send the weekly report to the CEO by Monday")
    assert r.verdict == "EQUIVALENT" and r.equivalent      # the 0.4 false-EQUIVALENT is still there when the flag is off


def test_unrepresented_difference_is_inconclusive_not_equivalent():
    r = compare("Send the weekly report to the CFO by Monday", "Send the weekly report to the CEO by Monday", ON)
    assert r.verdict == "INCONCLUSIVE" and not r.equivalent
    assert any(w["type"] == "UNACCOUNTED_CONTENT" for w in r.warnings)


def test_identical_wording_stays_equivalent():
    r = compare("Send the quarterly report to the CFO", "Send the quarterly report to the CFO", ON)
    assert r.verdict == "EQUIVALENT"


def test_real_difference_stays_not_equivalent():
    assert compare("Delete the report", "Summarize the report", ON).verdict == "NOT_EQUIVALENT"


def test_lexicon_paraphrase_across_languages_is_still_equivalent():
    assert compare("Resume el informe mañana.", "Resuma o relatório amanhã.", ON).verdict == "EQUIVALENT"


def test_morphological_variants_do_not_create_inconclusive():
    assert compare("Validate the datasets before publishing the results.", "Validate the datasets before the results are published.", ON).verdict != "INCONCLUSIVE"
