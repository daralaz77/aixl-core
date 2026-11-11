"""Mutation property tests for the semantic comparator (no extra dependency: a deterministic mutation engine over a small base corpus).

The project goal is NO SILENT FAILURE: a text and a copy of it with ONE meaning-changing edit must never come out EQUIVALENT. blind23-25 found
8 holes one set at a time (plural, article, tense, version-like numerals, 'not prohibited'); these properties search for the next one before an
outside author does. Each mutator is a single, local, meaning-changing edit written on its own; a mutator that does not apply to a sentence
returns None and is skipped. A failing property is a REAL finding: fix the comparator (or record it in KNOWN_OPEN with the reason), never loosen the check.
(tests/test_properties.py is a different file: the master-prompt invariants of the core graph.)
"""
import itertools
import re

import pytest

from aixl.semantic import compare_texts

BASE = [
    # English
    "Delete the file from the shared folder.", "Send the report to the client by Friday.", "Upgrade to version 2.1 before launch.",
    "The ticket was closed yesterday.", "You must reset the password every 90 days.", "Approve the request if the manager agrees.",
    "Back up the database before the release.", "Share the document with the team.", "The server is available on weekends.",
    "Restart the service after 10 minutes.", "Each user may edit the page.", "Copy the invoice to the accountant.",
    # Spanish
    "Borra el archivo de la carpeta compartida.", "Envía el informe al cliente antes del viernes.", "Instala la versión 3.2 del cliente.",
    "El ticket fue cerrado ayer.", "Debes cambiar la contraseña cada 90 días.", "Aprueba la solicitud si el gerente está de acuerdo.",
    "Respalda la base de datos antes del lanzamiento.", "Comparte el documento con el equipo.", "El servidor está disponible los fines de semana.",
    "Reinicia el servicio después de 10 minutos.", "Cada usuario puede editar la página.", "Copia la factura al contador.",
    # Portuguese
    "Apague o arquivo da pasta compartilhada.", "Envie o relatório ao cliente antes de sexta.", "Instale a versão 4.5 do cliente.",
    "O chamado foi fechado ontem.", "Você deve trocar a senha a cada 90 dias.", "Aprove a solicitação se o gerente concordar.",
    "Faça o backup do banco de dados antes do lançamento.", "Compartilhe o documento com a equipe.", "O servidor está disponível nos fins de semana.",
    "Reinicie o serviço depois de 10 minutos.", "Cada usuário pode editar a página.", "Copie a fatura para o contador.",
    # round 2 (added after the first mutation round): recipients, days, units, people, degree
    "Send the invoice to Ana on Monday.", "Tell him the meeting starts at 9 am.", "Wait 3 days before shipping the order.",
    "Envía la factura a Ana el lunes.", "Dile a ella que la reunión empieza a las 9.", "Espera 3 días antes de enviar el pedido.",
    "Envie a fatura para a Ana na segunda.", "Diga a ele que a reunião começa às 9.", "Espere 3 dias antes de enviar o pedido.",
    "The disk is almost full.", "El disco está casi lleno.", "O disco está quase cheio.",
    # round 3: conditions, coordination, exceptions, roles
    "Archive the logs and the reports.", "Archiva los registros y los informes.", "Arquive os logs e os relatórios.",
    "Send the file to the client if the manager approves.", "Envía el archivo al cliente si el gerente aprueba.", "Envie o arquivo ao cliente se o gerente aprovar.",
    "The client pays the supplier.", "El cliente paga al proveedor.", "O cliente paga ao fornecedor.",
    # round 4: possessives, pronouns, grammatical person, simple past
    "Send me your report before noon.", "Revise o meu código antes do deploy.", "Envía tu informe antes del mediodía.",
    "She sends the invoice every month.", "Ella envía la factura cada mes.", "Ela envia a fatura todo mês.",
    "Tell him the invoice is overdue.", "Dile a él que la factura venció.", "Diga a ele que a fatura venceu.",
    "The bank closes at noon.", "El banco cierra al mediodía.", "O banco fecha ao meio-dia.",
    "I approve the budget.", "Yo apruebo el presupuesto.", "Eu aprovo o orçamento.",
]


def _sub(pattern, repl, text, flags=re.I):
    new, n = re.subn(pattern, repl, text, count=1, flags=flags)
    return new if n and new != text else None


def m_plural_noun(t):          # one more of the thing: 'the file' -> 'the files', 'el archivo' -> 'los archivos'
    return (_sub(r"\bthe (file|report|ticket|invoice|document|request|password|user|page|client)\b", r"the \1s", t)
            or _sub(r"\bel (archivo|informe|ticket|documento|servicio|cliente|usuario)\b", r"los \1s", t)
            or _sub(r"\bo (arquivo|relatório|chamado|documento|serviço|cliente)\b", r"os \1s", t))


def m_indefinite(t):           # a specific thing -> any one thing
    return (_sub(r"\bthe (file|report|invoice|document|request|database|page)\b", r"a \1", t)
            or _sub(r"\bel (archivo|informe|documento|servicio)\b", r"un \1", t)
            or _sub(r"\bo (arquivo|relatório|documento|serviço)\b", r"um \1", t))


def m_tense(t):                # event vs state / present vs past
    return (_sub(r"\bwas closed\b", "is closed", t) or _sub(r"\bis available\b", "was available", t)
            or _sub(r"\bfue cerrado\b", "está cerrado", t) or _sub(r"\bestá disponible\b", "estuvo disponible", t)
            or _sub(r"\bfoi fechado\b", "está fechado", t) or _sub(r"\bestá disponível\b", "esteve disponível", t))


def m_number_up(t):            # a different quantity
    new = re.sub(r"\b(\d+)\b", lambda m: str(int(m.group(1)) + 5), t, count=1)
    return new if new != t else None


def m_version(t):              # '2.1' -> '2.10': same float, different release
    return _sub(r"\b(\d+\.\d)\b", r"\g<1>0", t)


def m_negate(t):               # insert a negation
    return (_sub(r"\bmust\b", "must not", t) or _sub(r"\bis available\b", "is not available", t)
            or _sub(r"\bdebes\b", "no debes", t) or _sub(r"\bestá disponible\b", "no está disponible", t)
            or _sub(r"\bdeve\b", "não deve", t) or _sub(r"\bestá disponível\b", "não está disponível", t))


def m_modal(t):                # obligation <-> permission
    return (_sub(r"\bmust\b", "may", t) or _sub(r"\bmay\b", "must", t) or _sub(r"\bdebes\b", "puedes", t)
            or _sub(r"\bpuede\b", "debe", t) or _sub(r"\bdeve\b", "pode", t) or _sub(r"\bpode\b", "deve", t))


def m_before_after(t):
    return (_sub(r"\bbefore\b", "after", t) or _sub(r"\bafter\b", "before", t) or _sub(r"\bantes de\b", "después de", t)
            or _sub(r"\bdespués de\b", "antes de", t) or _sub(r"\bantes d(o|a)\b", r"depois d\1", t) or _sub(r"\bdepois de\b", "antes de", t))


def m_swap_verb(t):            # a different action on the same object
    return (_sub(r"^Delete\b", "Copy", t) or _sub(r"^Copy\b", "Delete", t) or _sub(r"^Borra\b", "Copia", t) or _sub(r"^Copia\b", "Borra", t)
            or _sub(r"^Apague\b", "Copie", t) or _sub(r"^Copie\b", "Apague", t) or _sub(r"^Send\b", "Delete", t) or _sub(r"^Envía\b", "Borra", t)
            or _sub(r"^Envie\b", "Apague", t))


def m_each_all(t):             # per item vs the whole set
    return (_sub(r"\bEach user\b", "All users", t) or _sub(r"\bCada usuario\b", "Todos los usuarios", t) or _sub(r"\bCada usuário\b", "Todos os usuários", t))


def m_recipient(t):            # a different person receives it
    return (_sub(r"\bto Ana\b", "to Luis", t) or _sub(r"\ba Ana\b", "a Luis", t) or _sub(r"\bpara a Ana\b", "para o Luis", t))


def m_weekday(t):              # a different day
    return (_sub(r"\bon Monday\b", "on Tuesday", t) or _sub(r"\bel lunes\b", "el martes", t) or _sub(r"\bna segunda\b", "na terça", t)
            or _sub(r"\bby Friday\b", "by Monday", t) or _sub(r"\bantes del viernes\b", "antes del lunes", t) or _sub(r"\bantes de sexta\b", "antes de segunda", t))


def m_unit(t):                 # same number, other unit
    return (_sub(r"\b3 days\b", "3 hours", t) or _sub(r"\b3 días\b", "3 horas", t) or _sub(r"\b3 dias\b", "3 horas", t)
            or _sub(r"\b10 minutes\b", "10 hours", t) or _sub(r"\b10 minutos\b", "10 horas", t))


def m_person(t):               # him <-> her, el <-> ella
    return (_sub(r"\bTell him\b", "Tell her", t) or _sub(r"\bDile a ella\b", "Dile a él", t) or _sub(r"\bDiga a ele\b", "Diga a ela", t))


def m_degree(t):               # almost <-> fully
    return (_sub(r"\balmost full\b", "fully full", t) or _sub(r"\bcasi lleno\b", "completamente lleno", t) or _sub(r"\bquase cheio\b", "totalmente cheio", t))


def m_and_or(t):               # all of them -> any of them
    return (_sub(r"\bthe logs and the reports\b", "the logs or the reports", t) or _sub(r"\blos registros y los informes\b", "los registros o los informes", t)
            or _sub(r"\bos logs e os relatórios\b", "os logs ou os relatórios", t))


def m_drop_condition(t):       # the condition disappears
    return (_sub(r" if the manager approves", "", t) or _sub(r" si el gerente aprueba", "", t) or _sub(r" se o gerente aprovar", "", t))


def m_add_only(t):             # sufficient -> necessary
    return (_sub(r" if the manager approves", " only if the manager approves", t) or _sub(r" si el gerente aprueba", " solo si el gerente aprueba", t)
            or _sub(r" se o gerente aprovar", " somente se o gerente aprovar", t))


def m_roles(t):                # who does what to whom
    return (_sub(r"^The client pays the supplier", "The supplier pays the client", t) or _sub(r"^El cliente paga al proveedor", "El proveedor paga al cliente", t)
            or _sub(r"^O cliente paga ao fornecedor", "O fornecedor paga ao cliente", t))


def m_possessive(t):           # whose it is
    return (_sub(r"\byour report\b", "our report", t) or _sub(r"\bo meu código\b", "o seu código", t) or _sub(r"\btu informe\b", "mi informe", t))


def m_pronoun(t):              # who: him <-> her
    return (_sub(r"\bTell him\b", "Tell them", t) or _sub(r"\bDile a él\b", "Dile a ella", t) or _sub(r"\bDiga a ele\b", "Diga a eles", t))


def m_subject_person(t):       # grammatical person of the subject
    return (_sub(r"^She sends\b", "They send", t) or _sub(r"^Ella envía\b", "Ellas envían", t) or _sub(r"^Ela envia\b", "Elas enviam", t)
            or _sub(r"^I approve\b", "We approve", t) or _sub(r"^Yo apruebo\b", "Nosotros aprobamos", t) or _sub(r"^Eu aprovo\b", "Nós aprovamos", t))


def m_simple_past(t):          # habitual present -> one past event, with no auxiliary
    return (_sub(r"\bcloses at\b", "closed at", t) or _sub(r"\bcierra al\b", "cerró al", t) or _sub(r"\bfecha ao\b", "fechou ao", t)
            or _sub(r"\bsends the\b", "sent the", t) or _sub(r"\benvía la\b", "envió la", t) or _sub(r"\benvia a\b", "enviou a", t))


MUTATORS = {"plural": m_plural_noun, "indefinite": m_indefinite, "tense": m_tense, "number": m_number_up, "version": m_version,
            "negate": m_negate, "modal": m_modal, "before_after": m_before_after, "swap_verb": m_swap_verb, "each_all": m_each_all,
            "recipient": m_recipient, "weekday": m_weekday, "unit": m_unit, "person": m_person, "degree": m_degree,
            "and_or": m_and_or, "drop_condition": m_drop_condition, "add_only": m_add_only, "roles": m_roles,
            "possessive": m_possessive, "pronoun": m_pronoun, "subject_person": m_subject_person, "simple_past": m_simple_past}

# (mutator, base sentence) pairs KNOWN to come out EQUIVALENT: each one is an open hole, listed so the suite stays green AND the hole stays visible.
# Do not add a pair without a one-line reason.
KNOWN_OPEN: dict = {
    # 2026-11-11 (blind30): a DELIBERATE policy change, not a hole. 'each / every / cada' and 'all / todos' on the SUBJECT, with no number, no collective word
    # ('together', 'total', 'entre'), no exception and no order marker ('before', 'antes'), are now proven equal: four authors in blind25, blind28 and blind29 labelled such pairs
    # EQUIVALENT. The cases that really differ (an object quantifier, a count, a sequence) keep their guards in tests/test_semantic_recall_2026_11_11.py.
    ("each_all", "Cada usuario puede editar la página."): "subject each/all with no count, collective word or order marker is proven equal on purpose (blind30)",
}

CASES = [(name, base, mut(base)) for (name, mut), base in itertools.product(MUTATORS.items(), BASE) if mut(base) is not None]


def test_the_corpus_exercises_every_mutator():
    seen = {name for name, _, _ in CASES}
    assert seen == set(MUTATORS), f"mutators that never applied: {set(MUTATORS) - seen}"
    assert len(CASES) >= 60


@pytest.mark.parametrize("name,base,mutated", CASES, ids=[f"{n}:{b[:28]}" for n, b, _ in CASES])
def test_one_meaning_changing_edit_is_never_equivalent(name, base, mutated):
    if (name, base) in KNOWN_OPEN:
        pytest.xfail(KNOWN_OPEN[(name, base)])
    assert compare_texts(base, mutated).verdict != "EQUIVALENT", f"silent failure: {base!r} || {mutated!r}"
    assert compare_texts(mutated, base).verdict != "EQUIVALENT", f"silent failure (reversed): {mutated!r} || {base!r}"


@pytest.mark.parametrize("text", BASE)
def test_a_text_is_never_different_from_itself(text):
    assert compare_texts(text, text).verdict == "EQUIVALENT"


@pytest.mark.parametrize("name,base,mutated", CASES[::3], ids=[f"{n}:{b[:28]}" for n, b, _ in CASES[::3]])
def test_the_verdict_does_not_depend_on_the_order_of_the_texts(name, base, mutated):
    assert compare_texts(base, mutated).verdict == compare_texts(mutated, base).verdict
