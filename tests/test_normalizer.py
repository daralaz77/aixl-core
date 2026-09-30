from aixl.core.normalizer import SemanticNormalizer

N = SemanticNormalizer()


def test_action_synonyms_converge():
    for w in ["analiza", "examina", "estudia", "analyze", "examine", "analisa"]:
        assert N.normalize_action(w) == "ANALYZE", w
    for w in ["busca", "search"]:
        assert N.normalize_action(w) == "SEARCH"
    for w in ["encuentra", "localiza", "detecta", "find"]:
        assert N.normalize_action(w) == "FIND", w


def test_time_forms_converge_and_stay_distinct():
    q1 = {N.normalize_time(x) for x in ["primer trimestre de 2026", "Q1 2026", "Q1-2026", "first quarter of 2026"]}
    assert q1 == {"Q1-2026"}
    assert N.normalize_time("segundo trimestre de 2026") == "Q2-2026"
    assert N.normalize_time("Q1 2026") != N.normalize_time("Q2 2026")


def test_numbers_and_units():
    assert N.normalize_number("1.000") == "1000" and N.normalize_number("1,000") == "1000"
    assert N.normalize_number("100") == "100"
    assert N.normalize_number("0,75") == "0.75"
    assert N.normalize_unit("registros") == N.normalize_unit("records") == "RECORDS"


def test_aggregate_qualifiers_are_not_dropped():
    assert N.normalize_aggregate("volumen de") == "TOTAL" and N.normalize_aggregate("promedio de") == "AVERAGE"
    assert N.normalize_aggregate("ventas") is None


def test_no_fuzzy_equivalence():
    assert not N.canonical_equal("ventas", "volumen de ventas")
    assert N.canonical_equal("Q1 2026", "primer trimestre de 2026")
    assert N.normalize_output("excel") == "XLSX" and N.normalize_output("pdf") == "PDF"
