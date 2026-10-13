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


def test_envelope_v2_carries_the_witness_and_v1_is_still_accepted_with_it_recomputed():
    from aixl.envelope import ENV_VERSION
    e = seal("Envía el informe a Ana y a Luis.")
    assert e["v"] == ENV_VERSION == "AIXL-ENV-2" and e["or"] == 0
    old = {k: v for k, v in e.items() if k != "or"} | {"v": "AIXL-ENV-1"}          # an envelope sealed before the witness existed
    assert verify(old, "Envía el informe a Ana y a Luis.") == "MATCH"
    assert verify(old, "Envía el informe a Ana o a Luis.") == "MISMATCH"             # the old envelope no longer has the AND/OR hole


def test_malformed_or_unknown_envelopes_never_raise_and_never_claim():
    e = seal("Analiza las ventas de Q1 2026.")
    for bad in (None, [], "x", {}, {"v": "AIXL-ENV-9", **{k: v for k, v in e.items() if k != "v"}}, {k: v for k, v in e.items() if k != "fp"},
                {"v": "AIXL-ENV-2", "verifiable": True, "fp": "abcd1234"}):                    # no text, no witness
        assert verify(bad, "Analiza las ventas de Q1 2026.") == "UNVERIFIED", bad
    assert verify(e, None) == "UNVERIFIED"
