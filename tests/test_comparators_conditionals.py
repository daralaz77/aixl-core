"""Comparators (CMP=) and conditional connectives (COND=) are modelled, not just detected: a flipped bound or connective must change the
graph, and spelling variants of the same bound must not. Guarded end-to-end by benchmarks/logic_pairs_eval.py over data/arena/logic_pairs.jsonl."""
import json
import os

import pytest

import aixl
from aixl.translators.auto import to_graph_auto as tg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cons(text):
    return {c for c in tg(text).canonical()["constraints"]}


@pytest.mark.parametrize("text,expect", [
    ("Archive tickets with more than 5 attachments.", "CMP=GT:5"),
    ("Archiva tickets con al menos 5 adjuntos.", "CMP=GE:5"),
    ("Archive tickets with fewer than 5 attachments.", "CMP=LT:5"),
    ("Archive tickets with no more than 5 attachments.", "CMP=LE:5"),
])
def test_comparator_emitted(text, expect):
    assert any(expect in c for c in cons(text)), cons(text)


def test_comparator_bounds_differ():
    assert cons("Archive tickets with more than 5 attachments.") != cons("Archive tickets with at least 5 attachments.")


def test_no_fewer_than_is_single_comparator():
    c = [x for x in cons("Archive tickets with no fewer than 3 attachments.") if "CMP=" in x]
    assert len(c) == 1 and "CMP=GE:3" in c[0]


def test_number_spelling_is_canonical():
    assert cons("Keep scores >= .9") == cons("Keep scores >= 0.90")


def test_condition_connectives():
    assert any("COND=UNLESS" in c for c in cons("Notify the team unless the report is approved."))
    assert cons("Notify the team if the report is approved.") != cons("Notify the team unless the report is approved.")


def test_affirmation_and_question_are_not_conditions():
    assert not any("COND=" in c for c in cons("Si, muestrame las ventas."))


def test_logic_pairs_have_no_defects():
    import benchmarks.logic_pairs_eval as L
    rows = [json.loads(x) for x in open(os.path.join(ROOT, "data", "arena", "logic_pairs.jsonl"), encoding="utf-8") if x.strip()]
    bad = []
    for r in rows:
        if r["label"] != "DIFF":
            continue
        v = aixl.compare_verified(r["a"], r["b"])
        if v.get("verdict") == "EQUIVALENT" and v.get("verified"):
            bad.append((r["a"], r["b"]))
    assert not bad, bad
    assert L  # module imports cleanly


def test_noun_extension_represents_objects_and_never_drops_them():
    """aixl/resources/nouns_v1.json: an object noun must reach the graph (previously 'Delete the backups' == 'Delete the files' == 'Delete')."""
    import json
    assert aixl.compare("Delete the backups.", "Delete the files.").equivalent is False
    assert aixl.compare("Borra los respaldos.", "Delete the backups.").equivalent
    ents = json.load(open(os.path.join(ROOT, "aixl", "resources", "nouns_v1.json"), encoding="utf-8"))["entities"]
    assert "INVOICE" not in ents      # reserved: out-of-lexicon exemplar of the silent-loss benchmark and of the extension guide


@pytest.mark.parametrize("a,b", [
    ("You must not delete the records without a signed request.", "You may not delete the records without a signed request."),
    ("Valida los precios y verifica que ninguno baje del margen.", "Valida los precios y no verifica que ninguno baje del margen."),
    ("Confirma que ningún cliente quedó fuera.", "No confirmes que ningún cliente quedó fuera."),
    ("Verifica que al menos el 90 por ciento coincida.", "Verifica que al menos el 90 por ciento coincida, excepto los de 2025."),
])
def test_semantic_engine_no_false_equivalent_on_other_author_defects(a, b):
    """Found by `arena scope --other` (data/arena/other_author_seeds.jsonl): 16 false EQUIVALENT in the semantic engine used by the hybrid protocol."""
    from aixl.semantic.compare import compare_texts
    assert compare_texts(a, b).verdict != "EQUIVALENT"


def test_al_menos_is_a_comparator_not_an_exception():
    from aixl.semantic.compare import compare_texts
    assert compare_texts("Selecciona al menos 10 archivos.", "Selecciona 10 archivos.").verdict == "NOT_EQUIVALENT"


@pytest.mark.parametrize("a,b", [
    ("Compare the two documents and list the differences.", "Compare the two documents or list the differences."),
    ("Schedule a call for next Monday.", "Schedule a call for next Tuesday."),
    ("Si el cliente no ha pagado, márcalo.", "Do not si el cliente no ha pagado, márcalo."),
    ("Elimina el reporte de lunes.", "Elimina el reporte de martes."),
])
def test_surface_operators_are_visible_to_the_core_comparator(a, b):
    """DISJ= / DOW= / NEGN= constraints: the CORE (not only compare_verified) must not call these EQUIVALENT (arena, 549 -> 82 on own seeds)."""
    assert aixl.compare(a, b).equivalent is False


@pytest.mark.parametrize("a,b", [
    ("Book a room for at least ten people.", "Book a room that fits ten people or more."),
    ("Analise o relatório.", "Analiza el reporte."),
    ("Analiza los clientes del 2º trimestre de 2026.", "Analiza los clientes del segundo trimestre de 2026."),
    ("Agenda una llamada el lunes.", "Schedule a call on Monday."),
    ("No envíes el informe a nadie.", "No envíes el informe a nadie."),
])
def test_surface_operators_do_not_break_true_paraphrases(a, b):
    assert aixl.compare(a, b).equivalent is True


@pytest.mark.parametrize("a,b", [
    ("Delete the old backups.", "Delete the new backups."),
    ("Borra el archivo temporal.", "Borra el archivo permanente."),
    ("Cierra los tickets activos.", "Cierra los tickets inactivos."),
])
def test_contrast_modifiers_reach_the_graph(a, b):
    assert aixl.compare(a, b).equivalent is False


@pytest.mark.parametrize("a,b", [
    ("Delete duplicate rows from the orders table.", "Remove repeated rows from the orders table."),
    ("Borra los respaldos antiguos.", "Borra los respaldos viejos."),
])
def test_contrast_modifier_synonyms_converge(a, b):
    assert aixl.compare(a, b).equivalent is True


@pytest.mark.parametrize("a,b", [
    ("Delete invoices from March 3rd.", "Delete invoices from March 4th."),
    ("Send it to employees who joined after August 1st.", "Send it to employees who joined after August 2nd."),
    ("Schedule a 45-minute sync.", "Schedule a 54-minute sync."),
    ("Keep the older record as the primary one.", "Keep the newer record as the primary one."),
])
def test_compose_findings_day_of_month_hyphen_duration_comparative(a, b):
    """arena `compose` residue (2026-10-13): the day of a month, a `45-minute` duration and `older`/`newer` (without `than`) were silently dropped."""
    assert aixl.compare(a, b).equivalent is False


@pytest.mark.parametrize("a,b", [
    ("Elimina las facturas del 3 de marzo.", "Delete invoices from March 3rd."),
    ("Schedule a 45-minute sync.", "Schedule a 45 minute sync."),
    ("Calcula las ventas totales entre el 1 y el 15 de agosto de 2026.", "Calcula las ventas totales del 01/08/2026 al 15/08/2026."),
])
def test_compose_findings_do_not_split_true_paraphrases(a, b):
    assert aixl.compare(a, b).equivalent is True


@pytest.mark.parametrize("a,b", [
    ("You must delete the old backups.", "You may delete the old backups."),
    ("You should delete the logs.", "You may delete the logs."),
    ("Delete the logs.", "You may delete the logs."),
    ("You can delete the logs.", "You cannot delete the logs."),
])
def test_modal_strength_is_modelled(a, b):
    """arena modal_flip: must/should/may were function words the core ignored (`must` == `may`)."""
    assert aixl.compare(a, b).equivalent is False


@pytest.mark.parametrize("a,b", [
    ("Delete the logs.", "You must delete the logs."),
    ("Debes borrar los logs.", "Borra los logs."),
    ("Puedes borrar los logs.", "You can delete the logs."),
    ("Can you send the report?", "Send the report."),
    ("¿Puedes enviar el informe?", "Envía el informe."),
    ("You must not delete the logs.", "Don't delete the logs."),
])
def test_modal_paraphrases_still_converge(a, b):
    assert aixl.compare(a, b).equivalent is True


@pytest.mark.parametrize("a,b", [
    ("Compare the two documents and list the differences.", "Compare the two documents."),
    ("Resume los comentarios de la encuesta y destaca las quejas sobre entregas.", "Resume los comentarios de la encuesta."),
    ("List the top five accounts by churn risk and attach their last support interactions.", "List the top five accounts by churn risk."),
])
def test_dropped_trailing_clause_with_unknown_verb_is_visible(a, b):
    """arena drop_tail: a coordinated clause led by a verb outside the lexicon (list/destaca/attach) vanished without trace."""
    assert aixl.compare(a, b).equivalent is False


def test_noun_coordination_is_not_a_clause():
    assert aixl.compare("Delete the backups and logs from the server.", "Delete the backups and logs from the server.").equivalent
    from aixl.translators.natural_to_semantic import _verb_clause_count
    assert _verb_clause_count("delete the backups and logs from the server.") == 0
    assert _verb_clause_count("compare the documents and list the differences.") == 1


@pytest.mark.parametrize("a,b", [
    ("Process it without asking for approval.", "Do not process it without asking for approval."),
    ("Process it without asking for approval.", "Process it without asking for approval, pero no lo hagas."),
    ("Puedes cerrar los tickets sin respuesta.", "Puedes cerrar los tickets sin respuesta, pero primero envía un aviso."),
    ("Revise o código e aponte funções sem testes.", "Revise o código e não aponte funções sem testes."),
])
def test_second_negation_or_clause_after_existing_without_is_visible(a, b):
    """arena neg_suffix/neg_prefix/neg_scope: a text that already had a negation (`without`/`sin`/`sem`) hid every added one (negation was a boolean)."""
    assert aixl.compare(a, b).equivalent is False


@pytest.mark.parametrize("a,b", [
    ("Agende uma videochamada na terça, entre 14h e 16h.", "Agende uma videochamada na terça, entre 14h e 17h."),
    ("Agende uma reunião às 16h.", "Agende uma reunião às 23h."),
    ("Send the report to Ana and notify Luis.", "Cancel the report to Ana and notify Luis."),
    ("Pay before Friday.", "Pay after Friday."),
    ("Share the file, only for admins.", "Share the file."),
    ("You must anonymize it so you can upload.", "You may anonymize it so you can upload."),
    ("Schedule it at noon.", "Schedule it at 3 pm."),
])
def test_time_windows_clock_hours_weekday_relations_only_cancel_modal_count(a, b):
    """num_change / add_constraint / quantifier_add / antonym / modal_flip residue of the arena (other authors)."""
    assert aixl.compare(a, b).equivalent is False


@pytest.mark.parametrize("a,b", [
    ("Schedule it at 5 pm.", "Schedule it at 17:00."),
    ("Agenda la reunión a las 5 de la tarde.", "Agenda la reunión a las 17:00."),
    ("Agende uma reunião às 16h.", "Agende uma reunião às 16:00."),
    ("Schedule a call between 2 pm and 4 pm.", "Schedule a call between 14:00 and 16:00."),
    ("Paga antes del viernes.", "Pay before Friday."),
    ("Schedule it at noon.", "Schedule it at 12:00."),
])
def test_time_and_relation_paraphrases_converge(a, b):
    assert aixl.compare(a, b).equivalent is True
