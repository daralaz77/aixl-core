"""USE_LIMIT family: pure use-limit markers (no negation / number / date / modal) must not vanish unnoticed. Cases from the 12-pair probe (spent: regression only)."""
import pytest

from aixl.invariants import RELAY_FAMILIES, RELAY_FAMILIES_V1, relay_check, use_limits

DROPS = [
    ("Confidential. Send the report to Ana.", "Send the report to Ana."),
    ("Confidencial. Envía el informe a Ana.", "Envía el informe a Ana."),
    ("Send the report to Ana (under NDA).", "Send the report to Ana."),
    ("Send the draft to Ana. Embargoed.", "Send the draft to Ana."),
    ("Envía el borrador a Ana. Bajo embargo.", "Envía el borrador a Ana."),
    ("Send the report to Ana. For management eyes.", "Send the report to Ana."),
    ("Envía el informe a Ana. Para la gerencia.", "Envía el informe a Ana."),
]


def test_family_registered():
    assert "USE_LIMIT" in RELAY_FAMILIES and "USE_LIMIT" not in RELAY_FAMILIES_V1


@pytest.mark.parametrize("a,b", DROPS)
def test_dropped_marker_is_flagged(a, b):
    r = relay_check(a, b)
    assert not r["ok"] and "USE_LIMIT" in {v["family"] for v in r["violations"]}


def test_added_marker_is_flagged():
    assert not relay_check("Send the report to Ana.", "Confidential. Send the report to Ana.")["ok"]


def test_identical_text_with_marker_passes():
    assert relay_check("Confidential. Send the report to Ana.", "Confidential. Send the report to Ana.")["ok"]


def test_same_concept_other_words_is_not_a_use_limit_change():
    a, b = "Confidential. Send the report to Ana.", "Internal-use document. Send the report to Ana."
    assert "USE_LIMIT" not in {v["family"] for v in relay_check(a, b)["violations"]}


def test_concepts():
    assert use_limits("This is a draft under NDA. For management.") == {"DOC_STATUS", "CONFIDENTIALITY", "AUDIENCE"}
    assert use_limits("Send the report to Ana.") == frozenset()


def test_recipient_is_not_an_audience_limit():
    """`para a diretoria` / `to the board` is an addressee, not a use limit: found on blind10 (2 false alarms before v2)."""
    fams = {v["family"] for v in relay_check("Envie o relatório para a diretoria.", "Send the report to the board.")["violations"]}
    assert "USE_LIMIT" not in fams
    assert "AUDIENCE" not in use_limits("Grant read-only access to the finance folder for the auditors.")
    assert "AUDIENCE" not in use_limits("Envie o relatório para a diretoria até o dia 5.")


@pytest.mark.parametrize("text,concept", [
    ("Update the dashboard prepared for the logistics managers.", "AUDIENCE"),
    ("Escribe la nota dirigida al equipo de finanzas.", "AUDIENCE"),
    ("Prepare o resumo direcionado à equipe de engenharia.", "AUDIENCE"),
    ("Circulate the work-in-progress checklist.", "DOC_STATUS"),
    ("Reescreva a minuta da política.", "DOC_STATUS"),
    ("Arquive os e-mails do contrato, em litígio.", "LEGAL_HOLD"),
    ("Envie a proposta, sujeita a parecer jurídico.", "LEGAL_HOLD"),
    ("Compartilhe o fluxo, em fase de aprovação.", "DOC_STATUS"),
])
def test_extended_lexicon_v3(text, concept):
    assert concept in use_limits(text)


def test_open_audience_nouns_are_a_known_limit():
    """`aimed at investors` is NOT seen: the audience noun list is closed (measured v3: 6 of 36 audience drops missed)."""
    assert "AUDIENCE" not in use_limits("Update the charts in the deck aimed at investors.")
