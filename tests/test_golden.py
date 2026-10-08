"""Golden cases (§61): critical expected canonical fields, pinned. Any change here is a semantic change (§83)."""
import datetime

from aixl.api import service as S

T = datetime.date(2026, 10, 2)
GOLDEN = [
    ("Envía el informe a Ana mañana.", {"actions": ("SEND",), "entities": ("REPORT",), "references": ("@ANA",), "negation": ()}),
    ("No envíes el informe.", {"actions": ("SEND",), "negation": ("FORBID:SEND",)}),
    ("Busca hasta 10 resultados.", {"actions": ("SEARCH",)}),
    ("Do not send the report.", {"actions": ("SEND",), "negation": ("FORBID:SEND",)}),
]


def test_golden_fields():
    for text, exp in GOLDEN:
        c = S.to_semantic(text).canonical(today=T)
        for k, v in exp.items():
            assert c[k] == v, (text, k, c[k])


def test_golden_diff_cases():
    assert S.compare("Envía el informe.", "No envíes el informe.").equivalent is False
    assert S.compare("Envía el informe a Ana.", "Envía el informe a Carlos.").equivalent is False
    assert S.compare("Envía el informe a Ana mañana.", "Send the report to Ana tomorrow.").equivalent
    assert S.compare("Envía el informe a Ana mañana.", "Envie o relatório para Ana amanhã.").equivalent
