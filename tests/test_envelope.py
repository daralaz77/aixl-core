from aixl.envelope import seal, verify


def test_paraphrase_matches():
    assert verify(seal("Analiza las ventas de Q1 2026."), "Analyze Q1 2026 sales.") == "MATCH"


def test_negation_detected():
    assert verify(seal("Elimina el reporte."), "No elimines el reporte.") == "MISMATCH"


def test_number_change_detected():
    assert verify(seal("Analiza 100 usuarios."), "Analiza 1000 usuarios.") == "MISMATCH"


def test_out_of_domain_is_unverified_not_match():
    e = seal("cuando entro a cartelera en la cinematch no se despliega menu")
    assert e["verifiable"] is False and verify(e, "cuando entro a cartelera en la cinematch no se despliega menu") == "UNVERIFIED"


def test_unknown_word_abstains_instead_of_guessing():  # 'registros' is not fully encoded -> no claim, even though the numbers differ
    assert verify(seal("Analiza 100 registros."), "Analiza 1000 registros.") == "UNVERIFIED"
