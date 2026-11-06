"""Property-based fuzzing of the semantic comparator and the translator (Hypothesis).

Random text (arbitrary unicode) and random SENTENCES built from a three-language word bank are thrown at the public entry points, and the
invariants that the project promises are checked on every example:

  * nothing crashes and nothing takes more than a few seconds (a ReDoS or an unhandled exception is a finding, see tests/test_redos_budget.py);
  * a text compared with itself is never NOT_EQUIVALENT (and is EQUIVALENT when it has any token);
  * strict mode: EQUIVALENT only for the same token sequence, never turns INCONCLUSIVE / NOT_EQUIVALENT into anything else;
  * the verdict does not depend on the order of the two texts.

`AIXL_FUZZ_PROFILE=deep python -m pytest tests/test_fuzz_properties.py` runs 20x more examples with a random seed (use it before a release or when
hunting); the default profile is deterministic so CI never flakes. A failing example is a REAL finding: fix the code or record it in KNOWN_OPEN with the reason.
"""
import os

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import aixl
from aixl.semantic import compare_texts, parse

settings.register_profile("ci", max_examples=150, deadline=4000, derandomize=True, database=None, suppress_health_check=[HealthCheck.too_slow])
settings.register_profile("deep", max_examples=3000, deadline=8000, database=None, suppress_health_check=[HealthCheck.too_slow])
settings.load_profile(os.environ.get("AIXL_FUZZ_PROFILE", "ci"))

VERDICTS = {"EQUIVALENT", "NOT_EQUIVALENT", "INCONCLUSIVE"}

WORDS = ("send delete copy approve share archive restart the a an this that each every all any no not never must may should can will was were is are "
         "report file invoice database server user client manager team folder password ticket version 2.1 2.10 10 3 90 100% 1,000 1.5 ten one two "
         "before after until by within on in at to from with without if unless only and or but because while today tomorrow yesterday Friday Monday "
         "minutes hours days weeks 9am 5pm noon midnight first second last please now "
         "envía borra copia aprueba comparte el la los las un una cada todos todo cualquier debes puedes no nunca solo antes después hasta si "
         "informe archivo factura servidor usuario cliente gerente carpeta contraseña días horas "
         "envie apague copie aprove o os as um uma cada todos deve pode não nunca somente antes depois até se relatório arquivo fatura dias").split()

sentences = st.lists(st.sampled_from(WORDS), min_size=1, max_size=16).map(lambda ws: " ".join(ws).capitalize() + ".")
free_text = st.text(max_size=250)
texts = st.one_of(sentences, free_text)

# (property, text_a, text_b) examples known to violate a property: an open hole listed with a one-line reason. Empty means none found.
KNOWN_OPEN: set = set()


@given(texts, texts)
def test_compare_never_crashes_and_returns_a_verdict(a, b):
    assert compare_texts(a, b).verdict in VERDICTS


@given(texts)
def test_a_text_is_never_different_from_itself(a):
    v = compare_texts(a, a)
    assert v.verdict != "NOT_EQUIVALENT"
    if parse(a).norm:
        assert v.verdict == "EQUIVALENT"


@given(texts, texts)
def test_strict_mode_is_equivalent_only_for_the_same_token_sequence(a, b):
    loose, strict = compare_texts(a, b), compare_texts(a, b, strict=True)
    if strict.verdict == "EQUIVALENT":
        assert parse(a).norm == parse(b).norm
    if loose.verdict != "EQUIVALENT":
        assert strict.verdict == loose.verdict


@given(sentences, sentences)
def test_the_verdict_does_not_depend_on_the_order_of_the_texts(a, b):
    assert compare_texts(a, b).verdict == compare_texts(b, a).verdict, (a, b)


@given(texts)
def test_translate_and_fingerprint_never_crash(a):
    aixl.to_semantic(a)
    assert isinstance(aixl.semantic_fingerprint(a), str)


@given(texts, texts)
def test_verified_comparison_and_relay_check_never_crash(a, b):
    assert aixl.compare_verified(a, b)["verdict"] in VERDICTS
    assert "ok" in aixl.relay_check(a, b)
