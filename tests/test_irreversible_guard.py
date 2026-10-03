"""Irreversible-action guard (aixl/core/irreversible_guard.py): veto-only second opinion, evidence in distill/README.md."""
from aixl.core.irreversible_guard import assess, cue_signature, text_irreversible

DEL = "V:AIXL-0.3 I:REQUEST_EXECUTION A:DELETE"


def test_portuguese_delete_verbs_are_irreversible_even_when_model_says_exclude():
    # the distilled model encoded "Exclua"/"Apague" as EXCLUDE/DISABLE: the text-side check must still see DELETE
    assert text_irreversible("Exclua o relatório.") == {"DELETE"}
    assert text_irreversible("Apague os registros.") == {"DELETE"}
    r = assess("Exclua o relatório.", "Exclua o relatório.", "V:AIXL-0.3 A:EXCLUDE", "V:AIXL-0.3 A:EXCLUDE", True)
    assert r["escalate"] and r["reasons"][0].startswith("irreversible_verb_in_text_not_recognised")


def test_confirmation_condition_and_number_mismatches_veto_an_equivalent_verdict():
    for a, b in [("Delete the report without asking for confirmation.", "Delete the report after asking for confirmation."),
                 ("Delete the report only if it is old.", "Delete the report even if it is old."),
                 ("Send the file before Friday.", "Send the file after Friday."),
                 ("Delete ticket #77.", "Delete ticket #78."),
                 ("Back up the file and then delete it.", "Delete the file and then back it up.")]:
        assert assess(a, b, DEL, DEL, True)["escalate"], (a, b)


def test_translations_and_synonyms_are_not_vetoed():
    for a, b in [("Delete ticket #77.", "Elimina el ticket #77."), ("Do not send the draft.", "No envíes el borrador."),
                 ("Remove no more than 100 records.", "Remove at most one hundred records."),
                 ("Check report #31 before deleting it.", "Validate report #31 prior to removing it.")]:
        assert not assess(a, b, DEL, DEL, True)["escalate"], (a, b)


def test_never_acts_without_an_irreversible_action_and_never_flips_to_equivalent():
    # no irreversible verb on either side -> out of scope, even if cues differ
    assert not assess("Analyze sales in 2024.", "Analyze sales in 2025.", "V:AIXL-0.3 A:ANALYZE", "V:AIXL-0.3 A:ANALYZE", True)["escalate"]
    # a NOT_EQUIVALENT verdict is never touched for cue mismatch (veto-only: it can only add escalations to equivalence)
    assert not assess("Delete ticket #77.", "Delete ticket #78.", DEL, DEL, False)["escalate"]
    assert cue_signature("Delete ticket #77.") != cue_signature("Delete ticket #78.")


def test_portuguese_delete_verbs_translate_to_delete_in_the_rule_based_translator():
    # 2026-10-02: PT "apague/exclua" applied to data is DELETE (permanent), not DISABLE/EXCLUDE; ES "apaga" and PT
    # "exclua ... da análise" (leave out of a selection) and "apague a luz" (device off) keep their old meaning.
    from aixl.serialization import aixl_codec
    from aixl.translators.natural_to_semantic import to_graph

    def acts(t):
        return aixl_codec.encode(to_graph(t)).split(" A:")[1].split()[0]

    assert acts("Apague os registros de clientes.") == "DELETE"
    assert acts("Exclua os registros de clientes.") == "DELETE"
    assert acts("Não apague o relatório.") == "DELETE"
    assert acts("Exclua os usuários de teste da análise.").startswith("EXCLUDE")
    assert acts("Apague a luz do servidor.") == "DISABLE"
    assert acts("Apaga los registros.") == "DISABLE"
    assert acts("Excluye los registros de clientes.") == "EXCLUDE"
    # English "Do not ..." must not be read as Portuguese "do" (regression: first version of the PT-evidence helper did)
    assert acts("Do not ever exclude Ana from the results.").startswith("EXCLUDE")
    assert acts("Exclude test users from the analysis.").startswith("EXCLUDE")


def test_limit_and_before_synonyms_in_pt_es_en_are_not_vetoed():
    # false positives found by the free-teacher probe (2026-10-03): "no máximo" is a limit, not a negation; "antes das" = before
    for a, b in [("Cinco clientes como máximo deben aparecer en la lista.", "A maximum of five customers should appear on the list."),
                 ("Incluye un máximo de 10 ejemplos.", "Inclua no máximo 10 exemplos."),
                 ("Termina el despliegue antes de las 9am.", "Termine a implantação antes das 9am.")]:
        assert cue_signature(a) == cue_signature(b), (a, b)
