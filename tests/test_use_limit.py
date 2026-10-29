"""USE_LIMIT family: pure use-limit markers (no negation / number / date / modal) must not vanish unnoticed. Cases from the 12-pair probe (spent: regression only)."""
import pytest

from aixl.invariants import RELAY_FAMILIES, RELAY_FAMILIES_OPEN, RELAY_FAMILIES_V1, open_audience, relay_check, use_limits

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


def test_strong_audience_verb_is_an_opt_in_marker_whatever_group_follows():
    """v5-v7 as an OPT-IN family (USE_LIMIT_OPEN): fresh validation = 91 % of unusual audiences but 36.7 % decoy alarms, so it is NOT in RELAY_FAMILIES."""
    assert open_audience("Update the charts in the deck aimed at investors.")
    assert open_audience("Ajusta el informe dirigido a los inversionistas.")
    assert "AUDIENCE" not in use_limits("Update the charts in the deck aimed at investors.")
    assert "USE_LIMIT_OPEN" in RELAY_FAMILIES_OPEN and "USE_LIMIT_OPEN" not in RELAY_FAMILIES


def test_relay_check_open_mode_is_opt_in():
    a, b = "Update the charts in the deck aimed at investors.", "Update the charts in the deck."
    assert relay_check(a, b)["ok"] is True                              # the default: a group outside the closed list is not seen
    assert relay_check(a, b, open_audience=True)["ok"] is False


@pytest.mark.parametrize("text", [
    "Update the slides prepared for the meeting.", "Escribe el texto preparado para el viernes.", "Fix the deck made for testing.",
    "Entrega el informe escrito para revisar.", "Update the plan prepared for Q3 2026.", "Prepare o resumo escrito para a reunião.",
])
def test_event_time_and_verb_complements_are_not_an_audience(text):
    assert "AUDIENCE" not in use_limits(text)


def test_technical_target_is_not_an_audience():
    """blind11: `pull request targeting the main branch` = `dirigido a la rama principal` is an equivalent pair; it must not raise USE_LIMIT."""
    assert "AUDIENCE" not in use_limits("Ejecuta las pruebas en cada pull request dirigido a la rama principal.")
    assert "AUDIENCE" not in use_limits("Deploy the config meant for the staging environment.")


@pytest.mark.parametrize("text", [
    "Draft the workflow aimed at reducing ticket backlog.", "Escribe el plan orientado a reducir las devoluciones.", "Generate the records meant for load testing.",
    "Configure o ambiente, reservado para a rodada de testes.", "Faça o merge das correções, direcionado à ramificação principal do repositório.",
    "Set up the variant reserved for the pricing experiment.", "Compile the evidence tailored for the annual compliance audit.", "Write the notes prepared for the product launch event.",
])
def test_purposes_events_and_technical_targets_are_not_an_open_audience_v7(text):
    assert "AUDIENCE" not in use_limits(text) and not open_audience(text)


@pytest.mark.parametrize("text", [
    "Prepare the onboarding checklist, tailored for the summer interns.", "Write the guide aimed at marketing managers.",
    "Redija o folheto destinado às mães lactantes.", "Ajusta el informe dirigido a los inversionistas.",
])
def test_open_audiences_are_seen_in_open_mode_v7(text):
    assert open_audience(text)


def test_reservado_para_is_the_audience_verb_not_a_confidentiality_notice():
    assert "CONFIDENTIALITY" not in use_limits("Configure o ambiente, reservado para a rodada de testes.")
    assert "CONFIDENTIALITY" in use_limits("Documento reservado. Envie o relatório.")
