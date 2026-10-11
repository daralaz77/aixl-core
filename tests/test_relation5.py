"""Prompt 1.1 own examples. Expected labels fixed BEFORE running (Módulo 9). `SAFE_MISS` = engine is allowed to answer
UNDETERMINED (fail-closed) but must never answer EQUIVALENT when expected is not."""
import pytest
from aixl.relation5 import classify, error_from_relation, RELATIONS
from aixl.semantic.compare import compare_texts


def classify_texts(a, b):
    return classify(compare_texts(a, b))

CASES = [  # a, b, expected
 ("Resume el informe en cinco puntos.", "Resume el informe en diez puntos.", "CONTRADICTORY"),
 ("Resume el informe.", "Resume el informe en cinco puntos.", "PARTIAL"),
 ("Resume el informe en cinco puntos y envíalo a Ana.", "Resume el informe en cinco puntos.", "PARTIAL"),
 ("Borra el archivo.", "No borres el archivo.", "CONTRADICTORY"),
 ("Elimina los registros duplicados.", "Elimina los registros que no estén duplicados.", "CONTRADICTORY"),   # prompt's contrast test
 ("Traduce el texto al inglés.", "Translate the text into English.", "EQUIVALENT"),                          # prompt's example
 ("Resume el informe en cinco puntos.", "Summarize the report in five bullet points.", "EQUIVALENT"),       # prompt's example
 ("Resume el informe.", "Traduce el informe al inglés.", "COMPATIBLE"),
]
EXACT = {0, 1, 2, 3}  # rule engine is expected to be exact here; the rest may be UNDETERMINED (safe miss) but never EQUIVALENT


@pytest.mark.parametrize("i", range(len(CASES)))
def test_prompt_cases(i):
    a, b, exp = CASES[i]
    r = classify_texts(a, b)
    assert r.relation in RELATIONS
    if i in EXACT:
        assert r.relation == exp
    elif exp != "EQUIVALENT":
        assert r.relation != "EQUIVALENT"      # never a false equivalence
    else:
        assert r.relation in ("EQUIVALENT", "UNDETERMINED")


def test_error_record_direction():
    a, b, exp = CASES[4]
    got = classify_texts(a, b)
    rec = error_from_relation("T5", a, b, exp, got)
    assert rec is None or rec.error_type == "EQUIVALENCE_ERROR"   # safe miss, not FALSE_CONFIDENCE
