"""Context-aware ambiguity (§24, §35, §91), added 2026-10-02. The Core never picks a candidate."""
import inspect

from aixl.api import service as S

CTX = {"entities": [{"id": "juan_a", "name": "Juan Pérez"}, {"id": "juan_b", "name": "Juan Gómez"},
                    {"id": "ana", "name": "Ana Ruiz", "aliases": ["Anita"]}]}


def test_two_juans_is_ambiguous_with_both_candidates():
    r = S.detect_ambiguity("Envía el informe a Juan.", CTX)
    f = r.findings[0].to_dict()
    assert r.ambiguous and r.reason == "AMBIGUOUS_REFERENCE"
    assert f["candidate_interpretations"] == ["juan_a", "juan_b"] and f["affected_nodes"] and f["required_context"]


def test_same_in_english_and_portuguese():
    for t in ("Send the report to Juan.", "Envie o relatório para Juan."):
        assert S.detect_ambiguity(t, CTX).reason == "AMBIGUOUS_REFERENCE"


def test_surname_disambiguates_and_is_noted_not_mutated():
    r = S.detect_ambiguity("Envía el informe a Juan Pérez.", CTX)
    assert not r.ambiguous
    n = next(n for n in r.notes if n["reason"] == "RESOLVED_REFERENCE")
    assert n["entity"] == "juan_a" and n["provenance"] == "EXTERNAL_CONTEXT"


def test_unique_name_and_alias_resolve():
    assert [n["entity"] for n in S.detect_ambiguity("Envía el informe a Ana.", CTX).notes] == ["ana"]
    assert [n["entity"] for n in S.detect_ambiguity("Envía el informe a Anita.", CTX).notes] == ["ana"]


def test_unknown_is_not_ambiguous():
    r = S.detect_ambiguity("Envía el informe a Carlos.", CTX)
    assert not r.ambiguous and r.notes[0]["reason"] == "UNKNOWN_REFERENCE"


def test_two_people_one_ambiguous():
    r = S.detect_ambiguity("Send the report to Ana and Juan", CTX)
    assert r.ambiguous and len(r.findings) == 1


def test_without_context_behaviour_unchanged():
    assert "context" in inspect.signature(S.detect_ambiguity).parameters
    assert not S.detect_ambiguity("Envía el informe a Juan.").ambiguous
    assert "candidate_interpretations" not in str(S.detect_ambiguity("Elimina el archivo.").to_dict())


def test_ambiguous_target_changes_nothing_in_comparison():
    assert S.compare("Envía el informe a Juan.", "Send the report to Juan.").equivalent
