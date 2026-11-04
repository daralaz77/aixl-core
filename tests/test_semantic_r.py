"""0.3-R semantic track: model invariants + one regression per defect found while building it (master prompt §39)."""
import json
import os

import pytest

from aixl.semantic import compare_texts, parse

V = lambda a, b: compare_texts(a, b).verdict


def FLAGGED(a, b):
    """A difference is reported: asserted (NOT_EQUIVALENT) or, for a type outside the closed list DEFINITE_PATHS, kept as `suspected` under INCONCLUSIVE.
    Never EQUIVALENT either way (no silent failure)."""
    v = compare_texts(a, b)
    return v.verdict == "NOT_EQUIVALENT" or (v.verdict == "INCONCLUSIVE" and bool(v.suspected))


# ---- model: provenance, explicit ambiguity, unspecified-vs-specified ------------------------------------------------------------
def test_atoms_carry_span_provenance_scope():
    o = parse("Resume el informe en 200 palabras.")
    q = [a for a in o.atoms() if a.type == "QTY"][0]
    assert q.value == ("exact_implicit", 200, "words") and q.provenance == "DEFAULTED" and q.scope == 0 and q.span


def test_unspecified_is_not_filled_in():
    o = parse("Resume el informe.")
    assert not [a for a in o.atoms() if a.type in ("QTY", "TIME", "COND", "EXCEPT", "ONLY")]      # length/audience/language stay ABSENT, never defaulted


def test_ambiguity_is_kept_as_candidates_not_resolved():
    a = [x for x in parse("Evita las fuentes secundarias.").atoms() if x.type == "DEONTIC"][0]
    assert a.value == "DISCOURAGE" and "DONT" in a.candidates and a.ambiguous
    d = [x for x in parse("Usa el último documento.").atoms() if x.type == "ORD"][0]
    assert "most_recent" in d.candidates


def test_inferred_reference_is_marked_inferred():
    o = parse("Abre el archivo y ciérralo.")
    ref = [a for a in o.atoms() if a.type == "REF"][0]
    assert ref.provenance == "INFERRED" and not ref.ambiguous and ("TOK", "file") in o.steps[1].items


# ---- P1 / P2 core (the failures measured on blind13) ------------------------------------------------------------------------------
@pytest.mark.parametrize("a,b", [
    ("Usa fuentes oficiales.", "No uses fuentes oficiales."),
    ("Resume todos los documentos excepto los confidenciales.", "Resume todos los documentos."),
    ("Only managers can approve expenses.", "Managers can approve expenses."),
    ("Envía el informe antes del viernes.", "Envía el informe el viernes."),
    ("Envía el informe después del viernes.", "Envía el informe antes del viernes."),
    ("Mantén el acceso suspendido hasta que termine la auditoría.", "Mantén el acceso suspendido desde que termine la auditoría."),
    ("Envía el recordatorio cada lunes.", "Envía el recordatorio el próximo lunes."),
    ("Primero cobra el pago y luego despacha el pedido.", "Despacha el pedido y luego cobra el pago."),
    ("Usa el segundo archivo.", "Usa el primer archivo."),
    ("Copia el segundo archivo sobre el primero.", "Copia el primer archivo sobre el segundo."),
    ("Compra al menos tres cajas.", "Compra tres cajas."),
    ("Aprueba el reembolso solo si el cliente adjunta el recibo.", "Aprueba el reembolso si el cliente adjunta el recibo."),
    ("Puedes borrar los logs.", "Debes borrar los logs."),
    ("Resume el informe.", "Resume el informe en inglés."),
 ])
def test_core_distortions_are_never_equivalent(a, b):
    assert FLAGGED(a, b)


def test_swapped_stage_numbers_are_never_equivalent():     # regression (blind13 S041): numbers lost their position; INCONCLUSIVE is the honest answer
    assert V("Use o resultado da etapa 2 como entrada da etapa 3.", "Use o resultado da etapa 3 como entrada da etapa 2.") != "EQUIVALENT"


@pytest.mark.parametrize("a,b", [
    ("Evita las fuentes secundarias.", "No uses fuentes secundarias."),                       # hard vs soft prohibition
    ("No borres todos los archivos.", "No borres ningún archivo."),                           # 'not all' vs 'none'
    ("Entrega el reporte antes del viernes.", "Entrega el reporte a más tardar el viernes."),  # is the limit inclusive?
    ("Bórralo.", "Borra el informe."),                                                         # unresolved anaphora must not be guessed
    ("Pídele al técnico que revise el equipo del gerente antes de que él se vaya.", "Pídele al técnico que revise el equipo del gerente antes de que el técnico se vaya."),
    ("Usa el último documento.", "Usa el documento más reciente."),
    ("Revisa los contratos y los informes de 2024.", "Revisa los contratos de 2024 y los informes de 2024."),   # modifier scope / distribution
    ("Schedule the meeting for next Friday.", "Schedule the meeting for this Friday."),
    ("Paga el boleto.", "Pague o boleto."),                                                    # regression: ES/PT false friend, same spelling
])
def test_undecidable_pairs_stay_inconclusive(a, b):
    assert V(a, b) == "INCONCLUSIVE"


@pytest.mark.parametrize("a,b", [
    ("Si el archivo está vacío, solicita otro archivo.", "Solicita otro archivo si el archivo está vacío."),
    ("Delete the logs unless the logs are under legal hold.", "If the logs are not under legal hold, delete the logs."),
    ("Resume todos los documentos excepto los confidenciales.", "Resume todos los documentos menos los confidenciales."),
    ("Antes de reiniciar, borra el caché.", "Primero borra el caché y luego reinicia."),
    ("Selecciona entre 10 y 20 archivos.", "Selecciona al menos 10 y como mucho 20 archivos."),   # canonicalization: at_least+at_most == range
    ("Don't send the report to anyone.", "Send the report to no one."),
    ("Abre el archivo y ciérralo.", "Abre el archivo y cierra el archivo."),
    ("Lee el informe y el contrato.", "Lee el contrato y el informe."),
    ("Run the tests, then deploy.", "Run the tests, then deploy."),
])
def test_true_equivalences_are_proven(a, b):
    assert V(a, b) == "EQUIVALENT"


# ---- fail-closed invariants -------------------------------------------------------------------------------------------------------
def test_equivalent_requires_no_open_ambiguity_unless_identical():
    v = compare_texts("Envíalo mañana.", "Envíalo mañana.")
    assert v.verdict == "EQUIVALENT" and any("identical" in w for w in v.warnings)
    assert V("Envíalo mañana.", "Enviarlo mañana.") != "EQUIVALENT"


def test_unrepresentable_construct_never_yields_not_equivalent():
    assert V("Agrega media taza de harina.", "Agrega una taza de harina.") == "INCONCLUSIVE"


def test_light_verb_and_pronoun_never_prove_difference():
    assert V("Resume el informe.", "Haz un resumen del informe.") == "INCONCLUSIVE"


def test_verdict_explains_itself():
    v = compare_texts("Envía el informe antes del viernes.", "Envía el informe después del viernes.")
    d = v.diffs[0].to_dict()
    assert d["difference_type"] == "DISTORTION" and d["semantic_path"].endswith("time") and d["severity"] == "MAJOR"


# ---- dev-set gates: zero false-equivalent on the two development sets --------------------------------------------------------------
def _false_equiv(rows):
    return [r for r in rows if r["expected_equivalence"] != "EQUIVALENT" and V(r["text_a"], r["text_b"]) == "EQUIVALENT"]


def test_golden_r_no_false_equivalent():
    D = os.path.join(os.path.dirname(__file__), "..", "data", "golden_r")
    T = {r["id"]: r["source_text"] for r in map(json.loads, open(os.path.join(D, "texts.jsonl"), encoding="utf-8"))}
    rows = [dict(expected_equivalence=p["expected_equivalence"], text_a=T[p["text_a"]], text_b=T[p["text_b"]]) for p in map(json.loads, open(os.path.join(D, "pairs.jsonl"), encoding="utf-8"))]
    assert _false_equiv(rows) == []


def test_blind13_as_dev_no_false_equivalent():
    D = os.path.join(os.path.dirname(__file__), "..", "data", "blind13")
    rows = [json.loads(l) for f in ("authorS_sonnet.jsonl", "authorO_opus.jsonl") for l in open(os.path.join(D, f), encoding="utf-8")]
    assert _false_equiv(rows) == []        # blind13 is DEVELOPMENT data for the semantic track; blind14 is the independent judge


def test_english_delete_is_not_split_into_clitics():        # regression: 'delete' -> 'de' + 'le' + 'te' made a phantom indirect-object pronoun
    assert not [a for a in parse("Delete the logs.").atoms() if a.type == "REF"]


# ---- NOT_EQUIVALENT reliability (blind14 error analysis: 32 of 71 NOT_EQUIVALENT verdicts were wrong paraphrases/undecidable pairs) ----------------
@pytest.mark.parametrize("a,b", [
    ("Unless the patient objects, share the results with the family.", "Share the results with the family, provided the patient doesn't object."),
    ("Each pallet may carry no more than 800 kg.", "A pallet's load must not exceed 800 kilograms."),                     # another construction for the same limit
    ("Never leave the fryer unattended while it is on.", "Whenever the fryer is switched on, someone must be watching it."),
    ("Payroll runs on the last business day of every month.", "Every month, salaries are processed on the final working day."),
    ("Mientras se hornea el pan, prepara el relleno.", "Prepara el relleno durante la cocción del pan."),
    ("Cancele a assinatura do cliente hoje.", "Cancela aí a assinatura do cliente ainda hoje."),                           # filler words are not added information
    ("Ligue para o cliente e confirme com ele a data.", "Ligue para o cliente e confirme a data com o próprio cliente."),
    ("Antes de pintar la pieza, lija la superficie.", "Lija la superficie y, una vez hecho, pinta la pieza."),
    ("Verifica la cuenta antes del cierre.", "Verifica la cuenta bancaria antes del cierre."),                              # a lone adjective: maybe polysemy, not provably new
    ("Book a room for the meeting next Friday.", "Book a room for the meeting on the coming Friday."),
    ("Envía varios recordatorios al cliente.", "Envía tres recordatorios al cliente."),
    ("Invita a los 3 jefes de área.", "Invita a todos los jefes de área."),
    ("Cierra el turno a la medianoche del martes.", "Cierra el turno el miércoles a las 00:00."),
    ("Cierra la sesión del cliente y cambia su contraseña.", "Cambia la contraseña del cliente y cierra su sesión."),
])
def test_paraphrase_or_undecidable_pair_is_never_called_not_equivalent(a, b):
    assert V(a, b) != "NOT_EQUIVALENT"


@pytest.mark.parametrize("a,b", [
    ("Envía el resumen a todo el equipo.", "Envía el resumen a todo el equipo y a los clientes."),            # anchored addition: a new recipient
    ("Traduce el contrato al inglés.", "Traduce el contrato al inglés y al francés."),
    ("Prepara la lista de proveedores con su teléfono.", "Prepara la lista de proveedores."),                # anchored loss: a required field
    ("Entrega el pedido dentro de 3 días.", "Entrega el pedido a partir de 3 días."),
])
def test_anchored_differences_are_still_not_equivalent(a, b):
    assert FLAGGED(a, b)


# ---- classes closed after blind15 (7 wrong NOT_EQUIVALENT: 3 paraphrases + 4 undecidable) ---------------------------------------------------
@pytest.mark.parametrize("a,b", [
    ("Revisa los extintores de forma bimensual.", "Revisa los extintores cada dos meses."),                       # 'bimensual' is genuinely ambiguous
    ("Revisa el tren de aterrizaje cada semana.", "Revisa el tren de aterrizaje al final de la semana."),         # recurrence vs a phase of the period
    ("Aprueba las reclamaciones de vehículos y motos menores de cinco años.", "Aprueba las reclamaciones de vehículos de cualquier antigüedad y de motos menores de cinco años."),
    ("Ship the older customers' orders first.", "Ship the orders from long-standing customers first."),           # 'first' = priority, not the ordinal; 'from' is not a time relation
    ("Everyone except visitors must wear a lab coat in the lab.", "In the lab, lab coats are mandatory for all people present, with visitors exempt."),
    ("Se a pressão cair abaixo de 2 bar, desligue a bomba.", "Desligue a bomba caso a pressão fique menor que 2 bar."),
    ("Publique o comunicado amanhã às 9h.", "Publique o comunicado daqui a 24 horas."),                          # '24 horas' is a duration, not the clock time 24:00
    ("Only managers can approve expenses.", "Nobody other than a manager may approve expenses."),                  # restriction written differently also flips polarity
    ("No confirmes la cita si el paciente no ha traído la autorización.", "Confirma la cita solo si el paciente ha traído la autorización."),   # contraposition
    ("Open the oldest ticket in the queue and assign it to yourself.", "Assign yourself the ticket that has been waiting longest in the queue, after opening it."),
])
def test_classes_closed_after_blind15_are_not_not_equivalent(a, b):
    assert V(a, b) != "NOT_EQUIVALENT"


def test_solo_despues_at_clause_start_marks_explicit_order():          # regression: proven equivalent, was a spurious extra step
    assert V("Antes de abrir la caja fuerte, verifica la identidad del cliente.", "Verifica la identidad del cliente; solo después, abre la caja fuerte.") == "EQUIVALENT"


def test_recurrence_values_are_normalised_to_period_tuples():
    t = [a for a in parse("Rota las claves cada 90 días.").atoms() if a.type == "TIME"][0]
    assert t.value == ("recurring", (90, "days"))
    assert [a for a in parse("Revisa los frenos de forma semestral.").atoms() if a.type == "TIME"][0].value == ("recurring", (6, "months"))
    assert V("Rota las claves cada 90 días.", "Rota las claves a los 90 días de crearlas.") == "NOT_EQUIVALENT"        # recurring vs once stays a definitive difference


# ---- found by blind16 (run once on frozen code: 2 false-equivalents, 4 wrong NOT_EQUIVALENT) ------------------------------------------------
def test_he_and_she_are_not_the_same_recipient():                  # blind16 V036: both pronouns were resolved to the single candidate name
    v = compare_texts("Cuando llegue la doctora Ruiz con el paciente, dale a él el informe.", "Cuando llegue la doctora Ruiz con el paciente, dale a ella el informe.")
    assert v.verdict != "EQUIVALENT"
    assert V("Dale a él el informe.", "Dale a ella el informe.") == "NOT_EQUIVALENT"
    assert V("Dale a él el informe.", "Dale a él el informe.") == "EQUIVALENT"


def test_order_stated_in_one_text_only_is_not_proven_equal():      # blind16 W045: 'y después' vs bare 'y'
    assert V("Instala el parche y después reinicia el servidor.", "Instala el parche y reinicia el servidor.") == "INCONCLUSIVE"
    assert V("Instala el parche y luego reinicia el servidor.", "Primero instala el parche y después reinicia el servidor.") == "EQUIVALENT"   # both explicit


@pytest.mark.parametrize("a,b", [
    ("Cada bus debe llevar como máximo 40 pasajeros de pie.", "Ningún bus puede llevar más de cuarenta pasajeros de pie."),
    ("Pesa la harina y el azúcar; luego tamiza la primera.", "Pesa la harina y el azúcar, y después tamiza la harina."),     # 'la primera' = anaphoric ordinal
    ("Before shipping, label and weigh the parcel.", "Label and weigh the parcel prior to shipment."),                         # extra step vs a nominalisation
])
def test_blind16_wrong_not_equivalent_classes(a, b):
    assert V(a, b) != "NOT_EQUIVALENT"


# ---- found by blind17 (short safety run): English possessives his/her were treated as gender-neutral ----------------------------------------
def test_his_vs_her_is_a_different_referent():
    assert V("The teacher told the student to submit his essay before the break.", "The teacher told the student to submit her essay before the break.") == "NOT_EQUIVALENT"
    assert V("Give him the badge.", "Give her the badge.") != "EQUIVALENT"
    assert V("Entrega su informe.", "Entrega su informe.") == "EQUIVALENT"          # Spanish 'su' stays gender-neutral


# ---- found by blind18 (post-hoc; 3 semantic false-equivalents / wrong NOT_EQUIVALENT traced to 4 defects) --------------------------------------------
def test_double_negation_under_a_modal_never_cancels_into_permission():        # blind18 Y002: 'no está permitido no registrar' vs 'está permitido registrar'
    assert V("No está permitido no registrar la temperatura al cierre.", "Está permitido registrar la temperatura al cierre.") != "EQUIVALENT"
    assert "AMBIGUOUS_DOUBLE_NEGATION" in compare_texts("No está permitido no registrar la temperatura.", "Es obligatorio registrar la temperatura.").flags


def test_trailing_condition_after_an_english_imperative_chain_is_flagged_ambiguous():       # blind18 X022: 'and call' was not seen as a second action
    v = compare_texts("Evacuate the tunnel and call the supervisor if the gas alarm sounds.", "If the gas alarm sounds, evacuate the tunnel and call the supervisor.")
    assert v.verdict != "EQUIVALENT" and "AMBIGUOUS_COND_SCOPE" in v.flags


def test_never_fail_to_equals_always():                                         # blind18 X003: was a spurious TIME addition
    assert V("Never fail to lock the server room when you leave.", "Always lock the server room when you leave.") != "NOT_EQUIVALENT"


def test_not_every_equals_some_do_not():                                         # blind18 X010
    assert V("Not every museum visitor needs a badge.", "Some museum visitors do not need a badge.") != "NOT_EQUIVALENT"


def test_negated_until_vs_only_after_is_not_a_definitive_difference():
    """Found by the real-judge MCP hybrid test: 'don't X until Y' vs 'X only after Y' was a definitive NOT_EQUIVALENT (time DISTORTION) although the parser itself flags the
    reading as AMBIGUOUS_NEGATED_TEMPORAL. The ambiguity now covers the relation difference; real differences (other operand, before/after) stay definitive."""
    from aixl.semantic import compare_texts
    v = compare_texts("Don't publish the draft until Imani has reviewed it.", "Publish the draft only after Imani has reviewed it.")
    assert v.verdict == "INCONCLUSIVE" and "AMBIGUOUS_NEGATED_TEMPORAL" in v.flags
    assert compare_texts("Send the report before Friday.", "Send the report after Friday.").verdict == "NOT_EQUIVALENT"
    assert compare_texts("Don't publish until Friday.", "Don't publish until Monday.").verdict == "NOT_EQUIVALENT"


def test_plural_oldest_never_crashes_the_parser():
    """'los tres archivos más antiguos' raised KeyError('antiguos'): the parser listed the form, the ordinal lexicon did not have it."""
    from aixl.semantic import compare_texts, parse
    compare_texts("Borra los tres archivos más antiguos de la carpeta de pruebas.", "Delete the three oldest files in the test folder.")
    for w in ("antiguos", "antigos", "recentes", "recientes"):
        parse(f"Borra los archivos más {w} de la carpeta.")


# ---- tag questions: found by the external SemAntoNeg corpus (28 false-EQUIVALENT). Cases below are OWN sentences, not corpus items ----
@pytest.mark.parametrize("a,b", [
    ("The door is open, isn't it?", "The door is not open, is it?"),
    ("They finished the report, didn't they?", "They did not finish the report, did they?"),
    ("She can drive, can't she?", "She can't drive, can she?"),
    ("The team is ready, isn't it?", "The team is ready, is it?"),         # same clause, opposite expectation: never proven equivalent
])
def test_tag_question_polarity_never_proven_equivalent(a, b):
    assert V(a, b) != "EQUIVALENT" and V(b, a) != "EQUIVALENT"


def test_tag_question_main_clause_polarity_is_compared():
    assert V("You are safe, aren't you?", "You are not safe, are you?") == V("You are safe.", "You are not safe.") == "NOT_EQUIVALENT"


def test_tag_question_is_flagged_and_a_real_clause_is_not():
    assert any(c == "AMBIGUOUS_TAG_QUESTION" for c, _ in parse("The door is open, isn't it?").flags)
    assert not any(c == "AMBIGUOUS_TAG_QUESTION" for c, _ in parse("The door is open, is it a problem?").flags)   # a real clause is not a tag


# ES/PT tags: '¿no?' / 'não é?' carry a bare 'no/não' that was counted as negation of the main clause (own sentences; the probe found 2 false-EQUIVALENT)
@pytest.mark.parametrize("a,b", [
    ("Estás seguro, ¿no?", "No estás seguro."),
    ("Estás seguro, ¿no es así?", "No estás seguro."),
    ("Você está seguro, não é?", "Você não está seguro."),
    ("Você está seguro, não é?", "Você não está seguro, certo?"),
    ("Entregas el informe, ¿no?", "No entregues el informe."),
])
def test_es_pt_tag_question_never_proven_equivalent_to_the_negated_clause(a, b):
    assert V(a, b) != "EQUIVALENT" and V(b, a) != "EQUIVALENT"


def test_es_pt_tag_question_is_flagged_but_a_real_negation_is_not_stripped():
    for t in ("Estás seguro, ¿no?", "Você está seguro, não é?", "Está seguro, né?", "Estás seguro, ¿verdad?"):
        assert any(c == "AMBIGUOUS_TAG_QUESTION" for c, _ in parse(t).flags), t
    for t in ("Usa fuentes oficiales, no más de cinco.", "Envía el informe, no antes del viernes.", "Usa fuentes, ¿cuáles?"):
        assert not any(c == "AMBIGUOUS_TAG_QUESTION" for c, _ in parse(t).flags), t
    assert V("Usa fuentes oficiales, no blogs.", "Usa fuentes oficiales.") != "EQUIVALENT"      # ', no X' is a real negation and must stay one


# ---- antonym lexicon: a single known antonym swap in an otherwise identical, polarity-free pair is a DEFINITE difference (was INCONCLUSIVE) ----
@pytest.mark.parametrize("a,b", [
    ("Mark the file as safe.", "Mark the file as unsafe."),
    ("Review authorized accounts.", "Review unauthorized accounts."),
    ("Keep the relevant files.", "Keep the irrelevant files."),
    ("The server is reachable.", "The server is unreachable."),
    ("Revisa las cuentas seguras.", "Revisa las cuentas inseguras."),
    ("Mantén los archivos relevantes.", "Mantén los archivos irrelevantes."),
    ("Revise contas seguras.", "Revise contas inseguras."),
])
def test_known_antonym_swap_is_not_equivalent(a, b):
    assert V(a, b) == V(b, a) == "NOT_EQUIVALENT"


@pytest.mark.parametrize("a,b", [
    ("Do not allow external access.", "Forbid external access."),               # negation + antonym = the SAME meaning: must never become NOT_EQUIVALENT by this rule
    ("Do not use unsafe accounts.", "Use safe accounts."),                      # polarity present: rule stays silent (these two are not equal either, but never via this rule)
    ("Use safe accounts.", "Use secure accounts."),                             # not an antonym pair: unchanged
])
def test_antonym_rule_is_silent_when_polarity_is_involved(a, b):
    from aixl.semantic.parser import parse as _p
    r = compare_texts(a, b)
    assert not any(d.path == "items.antonym" for d in r.diffs)


# ---- four real defects found by blind19 (a set written by other authors). The tests use OWN sentences, never the blind19 items ----
def _deontic(t):
    return [a.value for a in parse(t).atoms() if a.type == "DEONTIC"][0]


@pytest.mark.parametrize("t", ["No está prohibido grabar en la sala.", "Não é proibido gravar na sala.", "It is not forbidden to record in the room.", "Never forbidden to record here."])
def test_not_forbidden_is_permission_not_prohibition(t):
    assert _deontic(t) == "MAY"


def test_not_forbidden_still_differs_from_forbidden_and_equals_permitted():
    assert V("No está prohibido grabar en la sala.", "Está prohibido grabar en la sala.") == "NOT_EQUIVALENT"
    assert V("No está prohibido grabar en la sala.", "Está permitido grabar en la sala.") != "NOT_EQUIVALENT"
    assert V("Prohibido grabar en la sala.", "Está prohibido grabar en la sala.") != "NOT_EQUIVALENT"      # a plain prohibition is untouched


def test_unmodelled_modal_adjective_never_creates_a_definite_item_difference():
    assert V("Não é permitido entrar sem crachá.", "É obrigatório usar crachá para entrar.") != "NOT_EQUIVALENT"
    assert V("No es posible pagar sin tarjeta.", "Es necesario pagar con tarjeta.") != "NOT_EQUIVALENT"


@pytest.mark.parametrize("a,b", [
    ("Pide como mínimo cuatro cotizaciones.", "Pide más de tres cotizaciones."),
    ("Invite at most six guests.", "Invite fewer than seven guests."),
])
def test_integer_boundary_is_not_a_definite_difference(a, b):
    assert V(a, b) != "NOT_EQUIVALENT" and V(b, a) != "NOT_EQUIVALENT"


def test_integer_boundary_rule_does_not_hide_a_real_quantity_difference():
    assert V("Pide como mínimo cuatro cotizaciones.", "Pide más de cuatro cotizaciones.") == "NOT_EQUIVALENT"      # off by one in the other direction: a real difference
    assert V("Invite at most six guests.", "Invite fewer than six guests.") == "NOT_EQUIVALENT"


def test_final_in_front_of_a_noun_is_not_a_definite_difference_from_last():
    assert V("Close the gate after the last bus has left.", "Close the gate after the final bus has left.") != "NOT_EQUIVALENT"
    assert V("The shop closes once the last client has left.", "After the final client leaves, the shop closes.") != "NOT_EQUIVALENT"
    assert V("Send the final report.", "Send the report.") != "NOT_EQUIVALENT"      # 'final report' is not 'last report': stays unproven, never a definite LOSS


# ---- defects found by blind20 (second set by other authors). Tests use OWN sentences, never the blind20 items ----
def test_not_necessary_is_not_necessary_not_to():
    """'not obligatory' (nothing required) vs 'obligatory not to' (a prohibition): a safety-relevant confusion that was proven EQUIVALENT."""
    for a, b in [("No es necesario que firmes el acta hoy.", "Es necesario que no firmes el acta hoy."),
                 ("No es necesario que entregues la llave hoy.", "Es necesario que no entregues la llave hoy."),
                 ("Não é necessário que assine o termo hoje.", "É necessário que não assine o termo hoje."),
                 ("It is not necessary that you sign today.", "It is necessary that you do not sign today."),
                 ("No es obligatorio no usar el ascensor.", "Es obligatorio no usar el ascensor.")]:
        assert V(a, b) != "EQUIVALENT" and V(b, a) != "EQUIVALENT", (a, b)
    assert V("No es necesario que entregues la llave hoy.", "Es necesario que no entregues la llave hoy.") == "NOT_EQUIVALENT"
    assert _deontic("No es necesario que entregues la llave hoy.") == "NOT_REQUIRED"


@pytest.mark.parametrize("a,b", [
    ("Pay 4.200 dollars.", "Pay 4,200 dollars."),
    ("Pague 3.500 reais.", "Pague 3,500 reais."),
    ("Wait 1.000 seconds.", "Wait 1,000 seconds."),
])
def test_thousands_vs_decimal_separator_is_never_proven_equal(a, b):
    assert V(a, b) != "EQUIVALENT" and V(b, a) != "EQUIVALENT"
    assert any(c == "AMBIGUOUS_NUMBER_SEPARATOR" for c, _ in parse(a).flags)


def test_unambiguous_numbers_are_not_flagged_and_real_differences_stay():
    assert not any(c == "AMBIGUOUS_NUMBER_SEPARATOR" for c, _ in parse("Pay 4200 dollars. Wait 1,5 hours. Send 12.50 euros.").flags)
    assert V("Hay 1500 sillas.", "Hay 1600 sillas.") == "NOT_EQUIVALENT"


def test_spelled_compound_number_is_not_a_definite_difference():
    for a, b in [("Hay 1500 sillas.", "Hay mil quinientas sillas."), ("Hay 2500 asientos.", "Hay dos mil quinientos asientos.")]:
        assert V(a, b) != "NOT_EQUIVALENT", (a, b)


def test_unicamente_and_solamente_are_only():
    assert V("Solo puedes pasar si tienes pase.", "Puedes pasar únicamente si tienes pase.") != "NOT_EQUIVALENT"
    assert V("Solo puedes pasar si tienes pase.", "Puedes pasar solamente si tienes pase.") != "NOT_EQUIVALENT"
    assert FLAGGED("Puedes pasar si tienes pase.", "Puedes pasar únicamente si tienes pase.")      # a real necessary-vs-sufficient difference stays flagged (suspected, not asserted: cond.kind is outside the closed list)


def test_the_action_word_reappearing_as_a_noun_is_not_an_addition():
    assert V("Archive the files after the review.", "Move the files to the archive after the review.") != "NOT_EQUIVALENT"


def test_coordination_marker_is_not_an_added_item():
    assert V("Send the note to Ana and Luis or Carmen.", "Send the note to Ana, and to either Luis or Carmen.") != "NOT_EQUIVALENT"
    assert FLAGGED("Send the note to Ana.", "Send the note to Ana and Luis.")      # a real added recipient stays flagged


def test_time_modifier_moved_between_steps_is_a_scope_question_not_a_difference():
    assert V("Salve o arquivo e feche o programa antes de sair.", "Salve o arquivo antes de sair e feche o programa.") != "NOT_EQUIVALENT"
    assert V("Salve o arquivo antes de sair.", "Salve o arquivo depois de sair.") == "NOT_EQUIVALENT"


@pytest.mark.parametrize("a,b", [
    ("The offer applies whenever you buy online.", "The offer applies if you buy online."),
    ("A oferta vale sempre que comprar online.", "A oferta vale se comprar online."),
    ("La oferta vale cada vez que compras en línea.", "La oferta vale si compras en línea."),
])
def test_whenever_is_not_a_plain_if(a, b):
    assert V(a, b) == "INCONCLUSIVE" and V(b, a) == "INCONCLUSIVE"


# ---- defects found by blind21 (the set is spent; these use OWN sentences) -----------------------------------------------------------
@pytest.mark.parametrize("a,b", [
    ("Call the clients who live abroad.", "Call the clients, who live abroad."),
    ("Elimina los registros que están en la carpeta vieja.", "Elimina los registros, que están en la carpeta vieja."),
    ("Avise os técnicos que trabalham à noite.", "Avise os técnicos, que trabalham à noite."),
])
def test_comma_before_relative_clause_is_never_proven_equal(a, b):
    assert V(a, b) == "INCONCLUSIVE" and V(b, a) == "INCONCLUSIVE"


@pytest.mark.parametrize("a,b", [
    ("Since the disk was full, the job was stopped.", "The job was stopped because the disk was full."),
    ("After the disk filled up, we purged the logs.", "We purged the logs because the disk filled up."),
    ("Paramos o job porque o disco encheu.", "Paramos o job depois que o disco encheu."),
])
def test_causal_marker_is_not_an_added_item(a, b):
    assert V(a, b) != "NOT_EQUIVALENT" and V(b, a) != "NOT_EQUIVALENT"


@pytest.mark.parametrize("a,b", [
    ("Elena es la que más vendió este mes.", "Nadie vendió más que Elena este mes."),
    ("Nadie entregó más reportes que Rosa.", "Rosa entregó más reportes que todos."),
    ("Nobody scored higher than Rosa.", "Rosa scored the highest."),
])
def test_negative_quantifier_subject_is_not_a_prohibition(a, b):
    assert V(a, b) != "NOT_EQUIVALENT" and V(b, a) != "NOT_EQUIVALENT"


@pytest.mark.parametrize("a,b", [
    ("Reinicie o servidor só depois de instalar o patch.", "Instale o patch e depois reinicie o servidor."),
    ("Faça o deploy só depois do backup.", "Faça o backup e depois o deploy."),
    ("Solo después del respaldo, haz el despliegue.", "Haz el respaldo y luego el despliegue."),
])
def test_only_after_is_not_asserted_as_a_difference(a, b):
    assert V(a, b) != "NOT_EQUIVALENT" and V(b, a) != "NOT_EQUIVALENT"


# ---- defects found by blind22 (the set is spent; these use OWN sentences) ----------------------------------------------------------
@pytest.mark.parametrize("a,b", [
    ("Had they paid on Friday, the order would have shipped.", "If they had paid on Friday, the order would have shipped."),
    ("Should you need help, call the desk.", "If you need help, call the desk."),
])
def test_inverted_conditional_is_never_a_definite_difference(a, b):
    assert V(a, b) != "NOT_EQUIVALENT" and V(b, a) != "NOT_EQUIVALENT"


def test_locative_dentro_de_is_not_an_added_item_but_deadlines_still_compare():
    assert V("Guarda el informe en la carpeta de pagos.", "Guarda el informe dentro de la carpeta de pagos.") != "NOT_EQUIVALENT"
    assert V("Responde dentro de dos horas.", "Responde dentro de tres horas.") == "NOT_EQUIVALENT"


def test_less_than_n_units_and_within_next_n_units_are_one_deadline_not_a_difference():
    assert V("Entrega el informe en menos de tres días.", "Entrega el informe dentro de los próximos tres días.") != "NOT_EQUIVALENT"
    assert V("Entrega el informe en menos de tres días.", "Entrega el informe en menos de cuatro días.") == "NOT_EQUIVALENT"


# ---- closed list DEFINITE_PATHS (after blind22): only reliable slot types may assert NOT_EQUIVALENT --------------------------------------------
def test_closed_list_asserts_reliable_types_and_only_suspects_the_rest():
    assert V("You may delete the logs.", "You must delete the logs.") == "NOT_EQUIVALENT"                 # deontic: asserted
    assert V("Send the report in two days.", "Send the report in three days.") == "NOT_EQUIVALENT"        # quantity: asserted
    v = compare_texts("Delete all files except the logs.", "Delete all files.")                            # 'except': not asserted, never lost
    assert v.verdict == "INCONCLUSIVE" and v.suspected and any("except" in d.path for d in v.suspected)


def test_suspected_difference_still_vetoes_a_unanimous_same():
    from aixl import hybrid_protocol as hp
    r = hp.decide("Delete all files except the logs", "Delete all files", {"j1": "SAME", "j2": "SAME"})
    assert r["verdict"] == "REVIEW"


# ---- blind23: definiteness, tense, range inclusivity, any vs all ---------------------------------------------------------------------------
@pytest.mark.parametrize("a,b", [
    ("Send me the report when it is ready.", "Send me a report when it is ready."),
    ("Envía el informe al terminar.", "Envía un informe al terminar."),
    ("The order was cancelled.", "The order is cancelled."),
    ("La puerta fue cerrada.", "La puerta está cerrada."),
])
def test_dropped_function_words_that_change_meaning_are_never_equivalent(a, b):
    assert V(a, b) != "EQUIVALENT"


def test_range_vs_exact_ends_and_any_vs_all_are_not_asserted():
    assert V("Choose a number between 1 and 10.", "Choose a number from 1 to 10, inclusive.") != "NOT_EQUIVALENT"
    assert V("Cualquier archivo adjunto debe ser escaneado.", "Todo archivo adjunto debe ser escaneado.") != "NOT_EQUIVALENT"
    assert V("Se aceptan entre 3 y 5 archivos.", "Se aceptan entre 3 y 6 archivos.") != "EQUIVALENT"
