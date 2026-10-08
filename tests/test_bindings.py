"""LIMITATIONS #3: action<->argument binding in the canonical form and AIXL (K:BIND=ACTION>ARG). 2026-10-02."""
import datetime
from aixl.api import service as S

T = datetime.date(2026, 10, 2)
b = lambda t: S.to_semantic(t).canonical()["bindings"]


def test_swapped_arguments_are_now_detected():
    r = S.compare("Elimina los usuarios y analiza los reportes.", "Elimina los reportes y analiza los usuarios.")
    assert not r.equivalent
    d = [x for x in r.differences if x.field == "BINDINGS"]
    assert d and d[0].severity == "CRITICAL"          # DELETE target changed
    assert S.detect_drift("Elimina los usuarios y analiza los reportes.", "Elimina los reportes y analiza los usuarios.").critical


def test_swap_detected_in_english_and_cross_language():
    assert not S.compare("Delete the users and analyze the reports.", "Delete the reports and analyze the users.").equivalent
    assert S.compare("Delete the users and analyze the reports.", "Elimina los usuarios y analiza los reportes.").equivalent
    assert S.compare("Delete the users and analyze the reports.", "Elimine os usuários e analise os relatórios.").equivalent


def test_bindings_contents():
    assert b("Busca el informe más reciente y envíalo a Ana.") == ("SEARCH>REPORT", "SEND>@ANA")
    assert b("Envía el informe a Ana.") == ()           # single action: nothing to bind


def test_aixl_roundtrip_keeps_bindings_and_fingerprint():
    t = "Elimina los usuarios y analiza los reportes."
    line = S.to_aixl(t)
    assert "K:" in line and "BIND=DELETE>USERS" in line
    assert S.from_aixl(line).canonical()["bindings"] == b(t)
    assert S.compare_aixl(line, S.to_aixl(t)).equivalent
    assert S.round_trip(t).preserved
    assert S.semantic_fingerprint(t, today=T) == S.semantic_fingerprint_aixl(line, today=T)


def test_fingerprint_separates_the_swap():
    a, c = "Elimina los usuarios y analiza los reportes.", "Elimina los reportes y analiza los usuarios."
    assert S.semantic_fingerprint(a, today=T) != S.semantic_fingerprint(c, today=T)


def test_missing_bindings_are_unknown_not_a_difference():
    """An AIXL line from an encoder that never emits BIND (e.g. an LLM with the frozen card) must still match."""
    import re
    with_b = S.to_aixl("Elimina los usuarios y analiza los reportes.")
    no_b = re.sub(r"\s*K:\S+", "", with_b)          # this text has no other constraint, so the whole K atom goes
    assert "BIND" not in no_b and S.from_aixl(no_b).canonical()["bindings"] == ()
    assert S.compare_aixl(with_b, no_b).equivalent


def test_subset_binding_is_compatible_but_reassignment_is_not():
    assert S.compare("Recupera el resultado #200 y compáralo con el resultado #201.",
                     "Obtén los resultados #200 y #201 y compáralos.").equivalent


def test_unreliable_clauses_have_no_bindings():
    for t in ("Verify the customer data before sending the report to Acme Corp.",
              "The customer data must be verified before the report is sent to Acme Corp.",
              "Enable the audio filter, then update the document #5."):
        assert b(t) == (), t


def test_synonym_actions_bind_identically():
    assert b("Check the users and delete the reports") == b("Validate the users and remove the reports")


def test_output_and_dependencies_stay_out_of_bindings():
    assert all(">" in x and "<" not in x and "TABLE" not in x for x in b("Calcula las ventas y preséntalas en una tabla."))


def test_config_without_bindings_keys_still_works():
    """SEMANTIC_CHANGELOG 0.4.0 promises custom configs written before the dimension existed keep working."""
    import json
    from aixl.core.ontology import load_config
    c = json.loads(json.dumps(load_config()))
    c["weights"].pop("bindings"); c["severity"].pop("bindings")
    r = S.compare("Elimina los usuarios y analiza los reportes.", "Elimina los reportes y analiza los usuarios.", c)
    assert not r.equivalent and r.critical_changes
