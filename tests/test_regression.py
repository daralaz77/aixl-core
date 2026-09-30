"""Every bug found becomes a test here (spec §32). Format: BUG-NNN, how it was found, what it broke."""
from aixl.translators.natural_to_semantic import to_graph
from aixl.core.comparator import compare_graphs


def eq(a, b):
    return compare_graphs(to_graph(a), to_graph(b)).equivalent


def test_bug001_confidence_without_leading_zero_was_read_as_nine():
    # found by test_demo5: "Confianza >= .9" was parsed as >=9 (the leading-dot decimal lost its dot)
    assert to_graph("Confianza >= .9").canonical()["modifiers"] == ("CONFIDENCE>=0.9",)
    assert eq("Confianza >= 0.90", "Confianza >= .9")
    assert not eq("Confianza >= 0.90", "Confianza >= 9")


def test_bug002_enclitic_pronoun_followed_by_punctuation_was_missed():
    # found by test_ambiguity: "elimínalos." (trailing period) was not recognised as verb+pronoun
    from aixl.core.ambiguity import detect_ambiguity_graph
    r = detect_ambiguity_graph("Analiza las ventas y los clientes y elimínalos.")
    assert r.ambiguous and r.findings[0].reason == "MULTIPLE_POSSIBLE_REFERENTS"


def test_bug003_set_minus_tuple_crash_in_ambiguity_detector():
    # found by test_ambiguity: TypeError (tuple - set) on 'Elimina el archivo.'
    from aixl.core.ambiguity import detect_ambiguity_graph
    assert detect_ambiguity_graph("Elimina el archivo.").ambiguous


# ---- bugs / gaps found by the blind rounds (each phrased with my own sentences, not copied from the blind data) ----
def test_bug004_action_synonyms_create_generate_get_retrieve_search_find_check_validate_are_one_task():
    assert eq("Crea un reporte de clientes.", "Escribe un reporte de clientes.")
    assert eq("Fetch 5 products.", "Get 5 products.")
    assert eq("Busca los eventos.", "Localiza los eventos.")
    assert eq("Verifica los datos de usuarios.", "Valida los datos de usuarios.")


def test_bug005_language_target_with_into_and_articles():
    assert to_graph("Translate the file into English.").canonical()["constraints"] == ("LANG=EN",)
    assert to_graph("Traduza o texto para o inglês.").canonical()["constraints"] == ("LANG=EN",)
    assert not eq("Translate the document into Spanish.", "Translate the document into Portuguese.")
    assert eq("Traduce el documento al idioma inglés.", "Translate the document into English.")


def test_bug006_passive_obligation_and_postposed_prohibition():
    assert eq("El reporte debe ser enviado hoy.", "Envía el reporte hoy.")
    assert eq("The report must be generated as JSON.", "Generate the report in JSON.")
    assert eq("Deleting users is forbidden.", "Do not delete users.")
    assert eq("The update must never be executed.", "Never run the update.")


def test_bug007_without_verb_is_a_prohibition_and_excluir_is_not_incluir():
    assert eq("Traduce sin modificar el formato.", "Traduce; prohibido modificar el formato.")
    assert eq("Excluye los datos de prueba.", "No incluyas los datos de prueba.")
    assert not eq("Traduce sin modificar el formato.", "Traduce y modifica el formato.")


def test_bug008_existence_and_containment_conditions():
    assert eq("Actualiza el producto solo si existe una anomalía.", "Actualiza el producto únicamente si se detecta una anomalía.")
    assert not eq("Verifica que el documento no contenga anomalías.", "Verifica que el documento contenga anomalías.")
    assert eq("Check whether the report has anomalies.", "Verify if the report contains anomalies.")
    assert eq("Si hay más de 100 registros, no ejecutes el proceso.", "No ejecutes el proceso cuando haya más de 100 registros.")
    assert eq("Envía una alerta siempre que existan más de 100 registros.", "Si hay más de 100 registros, envía una alerta.")


def test_bug009_quantity_units_ranking_words_and_number_words():
    assert eq("Procesa 1.000 registros de usuarios.", "Process 1,000 user records.")
    assert eq("Crea un documento con los 10 productos más vendidos.", "Escribe un documento con el top 10 de productos más vendidos.")
    assert eq("Get the 20 best customers.", "Fetch the top 20 customers.")
    assert eq("Crea un reporte con los cinco mejores clientes.", "Crea un reporte con los 5 mejores clientes.")
    assert not eq("Examina los últimos 100 registros.", "Examina los primeros 100 registros.")


def test_bug010_dates_ranges_relative_and_year_forms():
    assert eq("Analiza las ventas de marzo de 2026.", "Analiza las ventas de 2026-03.")
    assert eq("Calculate sales for 2025-01-01 through 2025-03-31.", "Calculate sales for Q1 2025.")
    assert eq("Get sales from 2025.", "Get the sales of the year 2025.")
    assert eq("Calcula el total de ventas del último mes.", "Calcula el total de ventas del mes pasado.")
    assert eq("Analiza los clientes del 2º trimestre de 2026.", "Analiza los clientes del segundo trimestre de 2026.")


def test_bug011_named_recipients_and_possessive_apostrophe():
    assert not eq("Envía el informe a la empresa Acme.", "Envía el informe a la empresa Beta.")
    assert to_graph("Compare this week's sales with last week's sales.").canonical()["references"] == ()


def test_bug012_light_verb_constructions():
    assert eq("Ejecuta el análisis de las ventas.", "Analiza las ventas.")
    assert eq("Run the validation of the datasets.", "Validate the datasets.")


def test_bug013_priority_levels_are_distinct_and_english_pt_verbs():
    assert not eq("Verifica los datos con prioridad urgente.", "Verifica los datos con prioridad alta.")
    assert eq("Actualiza el producto #20 con prioridad alta.", "Modifica el producto #20; la prioridad es alta.")
    assert eq("Não exclua os registros dos usuários.", "Nunca remova os registros dos usuários.")
    assert eq("Envía el reporte de hoy.", "Remite el reporte de hoy.")


def test_bug014_contradiction_overlap_by_kind_and_step_order():
    from aixl.core.contradiction import detect_contradiction_graphs as dc
    assert not dc(to_graph("Include customers in the report."), to_graph("Exclude users from the report.")).contradiction
    assert dc(to_graph("Ejecuta la traducción antes de generar el informe."), to_graph("Ejecuta la traducción después de generar el informe.")).contradiction


def test_bug015_ambiguity_generic_file_and_plural_agreement():
    from aixl.core.ambiguity import detect_ambiguity_graph as amb
    assert amb("Traduce el archivo.").ambiguous
    assert not amb("Find every event of the company Acme dated 2026-03-15 and list them.").ambiguous


def test_bug016_allow_vs_forbid_without_a_recognised_verb_is_still_opposite():
    # false positives of blind run 3: "Permite que ... vean" vs "Prohíbe que ... vean" were judged equivalent
    assert not eq("Permite que los usuarios vean el reporte.", "Prohíbe que los usuarios vean el reporte.")
    assert not eq("Allow the user to open the report.", "Forbid the user to open the report.")
    assert eq("Permite que los usuarios vean el reporte.", "Autoriza a los usuarios a ver el reporte.")
    from aixl.core.contradiction import detect_contradiction_graphs as dc
    assert dc(to_graph("Permite que los usuarios vean el reporte."), to_graph("Prohíbe que los usuarios vean el reporte.")).contradiction


def test_bug017_without_noun_and_portuguese_include():
    assert not eq("Do not send the report without a summary.", "Do not send the report with a summary.")
    assert not eq("Inclua os clientes inativos na lista.", "Não inclua os clientes inativos na lista.")


def test_bug018_portuguese_execute_and_subjunctive_run():
    assert eq("Executa o modelo #3.", "Ejecuta el modelo #3.")
    assert eq("No ejecutes el modelo.", "No corras el modelo.")


def test_bug019_number_before_confidence_word_and_plural_units():
    assert eq("Analyze sales with confidence >= 0.9.", "Analyze sales with at least 0.90 confidence.")
    assert eq("Elimina el reporte si hay más de 10 anomalías.", "Delete the report if there are more than 10 anomalies.")


def test_bug020_codec_tolerates_stray_space_after_comparator():
    # found by E-XV (2026-09-27): several LLM encoders wrote "H:> .90" / "F:COUNT>= 100" with a stray
    # space right after the operator; the codec used to reject the whole line (ERROR:INVALID_AIXL).
    from aixl.serialization import aixl_codec
    a = aixl_codec.decode("V:AIXL-0.3 I:REQUEST_ANALYSIS A:FIND E:ANOMALY H:> .90")
    b = aixl_codec.decode("V:AIXL-0.3 I:REQUEST_ANALYSIS A:FIND E:ANOMALY H:>.90")
    assert a.canonical() == b.canonical()
    c1 = aixl_codec.decode("V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE F:COUNT>= 100:RECORDS")
    c2 = aixl_codec.decode("V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE F:COUNT>=100:RECORDS")
    assert c1.canonical() == c2.canonical()


def test_bug021_codec_tolerates_multiple_output_values():
    # found by E-XV (2026-09-27): several LLM encoders wrote O:MARKDOWN,TABLE (two formats for one
    # "Markdown table" request); the codec used to reject any O: with more than one value.
    from aixl.serialization import aixl_codec
    g = aixl_codec.decode("V:AIXL-0.3 I:REQUEST_GENERATION A:GENERATE D:USERS O:MARKDOWN,TABLE")
    assert g.canonical()["output"] == ("MARKDOWN", "TABLE")
    g2 = aixl_codec.decode("V:AIXL-0.3 I:REQUEST_GENERATION A:GENERATE D:USERS O:TABLE,MARKDOWN")
    assert g.canonical() == g2.canonical()
    assert set(aixl_codec.encode(g).split("O:")[1].split(",")) == {"MARKDOWN", "TABLE"}


def test_bug022_codec_merges_repeated_list_atom_instead_of_rejecting():
    # found by E-XV (2026-09-27): Gemini sometimes wrote a list atom twice on one line instead of
    # merging into one comma-separated token (e.g. two `E:` tokens); the codec used to reject the
    # whole line. Merging is safe (union of values); a repeated SCALAR atom (e.g. two `H:` or two
    # `V:`) is still a real conflict and must still raise.
    from aixl.serialization import aixl_codec
    from aixl.legacy02.core.parser import AixlError
    g = aixl_codec.decode("V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE,FIND E:COMPANY D:IMAGE E:ANOMALY G:ANOMALY_DETECTION")
    assert set(g.canonical()["entities"]) == {"COMPANY", "ANOMALY"}
    try:
        aixl_codec.decode("V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE H:>.5 H:>.9")
        assert False, "duplicate scalar atom must still raise"
    except AixlError as e:
        assert e.code == "INVALID_AIXL"


# ---- E-DATE: reference clock + duration/time-of-day extensions (2026-09-27, closing set-6 gaps) ----
from datetime import date as _date                          # noqa: E402
from aixl.translators.natural_to_semantic import to_graph as _tg  # noqa: E402
_T = _date(2026, 9, 27)


def _eqd(a, b, today=_T):
    return compare_graphs(_tg(a, today=today), _tg(b, today=today)).equivalent


def test_bug023_relative_day_and_month_resolve_against_a_reference_date():
    # evidence: independent blind authors (blind3 A3-024, blind6 S6-009/S6-061) consistently label
    # relative-day/month wording as EQUIVALENT to the literal same-day/month date, not just once.
    assert _eqd("Fetch yesterday's sales results.", "Fetch the sales results for 2026-09-26.")
    assert _eqd("Analiza los eventos del mes pasado.", "Analiza los eventos de agosto de 2026.")
    assert not _eqd("Fetch yesterday's sales results.", "Fetch the sales results for 2026-09-20.")
    # a different reference date resolves to a different literal, still self-consistent
    assert _eqd("Fetch yesterday's sales results.", "Fetch the sales results for 2026-09-19.", today=_date(2026, 9, 20))


def test_bug024_date_range_two_formats_and_slash_dates():
    # bug025 in same round: 0.2 analyzer only kept the SECOND day of "entre el 1 y el 15 de agosto de
    # 2026", and never understood DD/MM/YYYY at all (set6 S6-032).
    assert _eqd("Calcula las ventas totales entre el 1 y el 15 de agosto de 2026.",
                "Calcula las ventas totales del 01/08/2026 al 15/08/2026.")
    assert not _eqd("Calcula las ventas totales entre el 1 y el 15 de agosto de 2026.",
                     "Calcula las ventas totales del 01/08/2026 al 20/08/2026.")


def test_bug025_clock_time_before_after_12h_and_24h():
    # the time of day used to be silently dropped entirely (out of vocabulary), which made two
    # genuinely different deadlines look EQUIVALENT — a false positive, not just a missed pair.
    assert _eqd("Envía el documento validado a Cascada Foods antes de las 3:00 pm.",
                "Antes de las 15:00, remite el documento validado a Cascada Foods.")
    assert not _eqd("Send the report before 3:00 pm.", "Send the report before 5:00 pm.")


def test_bug026_age_duration_constraint():
    assert _eqd("Delete all customer images older than one year.",
                "Elimina todas las imágenes de clientes con más de un año de antigüedad.")
    assert not _eqd("Delete images older than one year.", "Delete images older than two years.")


def test_bug027_priority_synonym_urgent_vs_high_stays_not_equivalent():
    # verified against the corpus (2026-09-27): 23 independent blind pairs across 6 rounds label
    # "urgent" vs "high priority" NOT_EQUIVALENT, only 1 single-annotator pair (set6 S6-033) called
    # them equivalent. The majority reading wins; S6-033 is treated as a noisy label, not a bug.
    assert not _eqd("Send an urgent alert to Vertex Ltda about the detected anomaly.",
                     "Dispatch a high-priority alert to Vertex Ltda regarding the detected anomaly.")


def test_bug028_deadline_cue_by_and_scheduled_at_time():
    # found by set 7 (E-DATE round 2, 2026-09-27): bug025's fix only covered "before/after"; "by" is
    # the same BEFORE semantics with a different word ("submit by 9am" was a false EQUIVALENT against
    # "submit by 9pm", same failure class as before/after but a cue word the first fix missed).
    assert not _eqd("Submit the document by 9am.", "Submit the document by 9pm.")
    assert _eqd("Submit the document by 9am.", "Submit the document by 9am.")
    # "at/for/para/a las" is a scheduled TIME_AT, not before/after; also compact "2:30pm" (no space
    # before am/pm) must not leak into the generic quantity extractor as a spurious "2".
    assert _eqd("Schedule the meeting for 2:30pm.", "Programa la reunión para las 14:30.")
    assert not _eqd("Schedule the meeting for 2:30pm.", "Schedule the meeting for 3:30pm.")


def test_bug029_duration_unit_conversion_year_equals_twelve_months():
    # found by set 7 (E-DATE round 2): an LLM encoder reused the card's own COUNT>N:UNIT pattern for
    # "older than" and wrote 1:YEARS vs 12:MONTHS for the same duration — compared unequal without
    # this conversion. Applies to both the rule-based AGE constraint and any F:COUNT condition.
    assert not _eqd("Delete images older than one year.", "Delete images older than two years.")
    # "tenure" isn't in the AGE_RX cue phrases (a different vocabulary gap, documented, not fixed here)
    assert not _eqd("Flag customers older than one year.", "Flag customers with more than 12 months of tenure.")
    from aixl.serialization import aixl_codec
    from aixl.core.comparator import compare_graphs
    a = aixl_codec.decode("V:AIXL-0.3 I:REQUEST_ANALYSIS A:FIND D:CUSTOMERS F:COUNT>1:YEARS")
    b = aixl_codec.decode("V:AIXL-0.3 I:REQUEST_ANALYSIS A:FIND D:CUSTOMERS F:COUNT>12:MONTHS")
    assert compare_graphs(a, b).equivalent


def test_bug030_reference_number_without_hash_sigil():
    # found by set 8 (E-DATE round 3, 2026-09-27): "ticket número 77" / "issue number 58" / "event 340"
    # (no literal '#') were not recognized as the same reference as "#77"/"#58"/"#340" — a real
    # false negative on 4 independent pairs in one fresh set, not a one-off.
    assert _eqd("Revisa el ticket #77 antes de cerrarlo.", "Verifica el ticket número 77 antes de cerrarlo.")
    assert _eqd("Update the status of issue #204.", "Update the status of ticket number 204.")
    assert _eqd("Verify the anomaly reported in event #340.", "Check the anomaly logged under event 340.")
    assert not _eqd("Revisa el ticket número 77.", "Revisa el ticket número 78.")


def test_bug031_reference_time_reused_for_relative_date_at_comparator_level():
    # found by set 7 (E-DATE round 2): the round-1 reference-clock fix lived only in the rule-based
    # translator, so an LLM-encoded 'T:TODAY' never matched a literal date decoded from its own AIXL
    # line. Moved to SemanticGraph.canonical()/compare_graphs(today=...) so it covers BOTH routes.
    from aixl.serialization import aixl_codec
    from aixl.core.comparator import compare_graphs
    from datetime import date as _d
    a = aixl_codec.decode("V:AIXL-0.3 I:REQUEST_RETRIEVAL A:GET D:SALES T:TODAY")
    b = aixl_codec.decode("V:AIXL-0.3 I:REQUEST_RETRIEVAL A:GET D:SALES T:2026-09-27")
    assert compare_graphs(a, b, today=_d(2026, 9, 27)).equivalent
    assert not compare_graphs(a, b, today=_d(2026, 9, 28)).equivalent


def test_bug032_unknown_action_value_does_not_crash_the_comparator():
    # found by E-INTEROP (2026-09-29): Gemini, encoding independently from the same frozen card, wrote
    # the noun `A:ANALYSIS` instead of the verb `A:ANALYZE` on one line out of 100. That value isn't in
    # ACTION_TO_INTENT, and derive_intent's bare dict lookup raised an uncaught KeyError, crashing the
    # WHOLE comparison instead of just judging that one line not-equivalent. A protocol must degrade
    # gracefully on a value it doesn't recognize (that's the interoperability requirement), not crash.
    from aixl.serialization import aixl_codec
    from aixl.core.comparator import compare_graphs
    a = aixl_codec.decode("V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYSIS D:DATA T:THIS_YEAR")
    b = aixl_codec.decode("V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE D:DATA T:THIS_YEAR")
    r = compare_graphs(a, b)          # must not raise
    assert not r.equivalent           # ANALYSIS != ANALYZE as a raw action value, honestly reported


def test_bug033_expanded_verb_vocabulary_converges_with_gemini_readings():
    # found by E-INTEROP (2026-09-29): 18 of 47 cross-vendor disagreements were verbs not explicit in the
    # card/code (export, notify, close, archive, present, schedule, mark) or a generic-verb-vs-specific-
    # object ambiguity (generate A SUMMARY). Card + rule-based translator extended together so BOTH routes
    # pick the SAME action for these — the actual "way to reach agreement" for two parties that never talk
    # to each other live: a shared, more complete deterministic vocabulary.
    assert _eqd("Notify Kaelis Group about the update.", "Send Kaelis Group an alert about the update.")
    assert _eqd("Close ticket #77.", "Update ticket #77's status to closed.")
    assert not _eqd("Close ticket #77.", "Delete ticket #77.")           # close is a status change, NOT deletion
    assert _eqd("Archive events older than two weeks.", "Disable events older than two weeks.")
    assert not _eqd("Archive events older than two weeks.", "Delete events older than two weeks.")  # archive != delete
    assert _eqd("Present the anomaly summary as a table.", "Show the anomaly summary as a table.")
    assert _eqd("Schedule the call for 9am.", "Create the call for 9am.")
    assert _eqd("Genera el resumen antes de las 11:00 a.m.", "Resume antes de las 11:00 a.m.")
    assert _eqd("If there are more than 100 records, generate a summary.",
                "Si hay más de 100 registros, resume.")
    # sanity: a plain "generate" with no "summary" object must stay GENERATE, not get swallowed
    assert not _eqd("Genera el resumen antes de las 11:00 a.m.", "Genera el reporte antes de las 11:00 a.m.")
