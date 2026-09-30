from aixl.core.ambiguity import detect_ambiguity_graph as amb


def reasons(t):
    r = amb(t)
    return r.ambiguous, {f.reason for f in r.findings}


def test_demo6_recent_data_is_ambiguous():
    ok, rs = reasons("Analiza los datos recientes.")
    assert ok and "VAGUE_TIME" in rs
    assert amb("Analiza los datos recientes.").fields == ["TIME"]


def test_specified_instructions_are_not_ambiguous():
    for t in ["Analiza las ventas del primer trimestre de 2026 en JSON.", "Elimina el reporte #81.", "Compara el dataset #77 con el dataset #81.",
              "Analyze the sales of Q1 2026.", "No elimines el reporte #4."]:
        assert not amb(t).ambiguous, t


def test_pronoun_without_antecedent():
    for t in ["Elimínalo.", "Fix it.", "Analiza eso.", "Send her the file.", "Analiza aquello."]:
        ok, rs = reasons(t)
        assert ok, t


def test_pronoun_with_single_antecedent_is_resolved_and_with_two_is_ambiguous():
    assert not amb("Traduce el reporte #4 y envíalo.").ambiguous      # (a generic "el reporte" with no id is itself unresolved for a send/delete)
    ok, rs = reasons("Analiza las ventas y los clientes y elimínalos.")
    assert ok and "MULTIPLE_POSSIBLE_REFERENTS" in rs


def test_missing_year_and_missing_target_and_scope():
    assert "MISSING_YEAR" in reasons("Analiza el informe de marzo.")[1]
    assert "UNSPECIFIED_SCOPE" in reasons("Borra todo.")[1]
    assert reasons("Analiza.")[0]
    assert "MISSING_COMPARAND" in reasons("Compara ambos.")[1] or reasons("Compara ambos.")[0]


def test_unresolved_the_old_ones_and_generic_file_delete():
    assert amb("Delete the old ones.").ambiguous
    assert amb("Elimina el archivo.").ambiguous
    assert not amb("Elimina el archivo #12.").ambiguous


def test_relative_time_is_a_note_not_a_block():
    r = amb("Analiza las ventas de ayer.")
    assert not r.ambiguous and r.notes and r.notes[0]["reason"] == "RELATIVE_TIME_NEEDS_ANCHOR"


def test_never_invents_information():
    r = amb("Analiza los datos recientes.")
    assert all(f.evidence != "" or f.reason.startswith("MISSING") for f in r.findings)
