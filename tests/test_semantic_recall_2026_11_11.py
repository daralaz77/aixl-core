"""2026-11-11, from blind28 (120 pairs, in-vocabulary constructs): the comparator proved 0 of 5 equivalent deadline pairs and 0 of 7 word-order pairs, and accepted
three arguable pairs ('never' vs 'do not', 'nenhum' vs 'qualquer', create vs generate). Rules added: fixed deadline phrasings, a fronted time/frequency adjunct,
and two ledger entries. Each rule has positive cases (now proven) and guards (still not proven). Strict mode keeps reading the words as written."""
import pytest

from aixl.semantic import compare_texts

V = lambda a, b: compare_texts(a, b).verdict  # noqa: E731
S = lambda a, b: compare_texts(a, b, strict=True).verdict  # noqa: E731

DEADLINES = [("Submit the report by Friday.", "Submit the report no later than Friday."),
             ("Submit the invoice by Monday at the latest.", "Submit the invoice no later than Monday."),
             ("Submit the report by Friday.", "Submit the report by Friday at the latest."),
             ("Entregue as notas fiscais até o dia 5.", "Entregue as notas fiscais no máximo até o dia 5.")]
FRONTED = [("After the backup finishes, delete the old logs.", "Delete the old logs after the backup finishes."),
           ("Mañana, envía el acta de la reunión a todos los asistentes.", "Envía el acta de la reunión a todos los asistentes mañana."),
           ("Cada semana, el administrador revisa los backups.", "El administrador revisa los backups cada semana."),
           ("Every Monday, send the report to the team.", "Send the report to the team every Monday.")]


@pytest.mark.parametrize("a,b", DEADLINES + FRONTED)
def test_new_phrasings_are_proven_equivalent(a, b):
    assert V(a, b) == "EQUIVALENT" and V(b, a) == "EQUIVALENT"


@pytest.mark.parametrize("a,b", DEADLINES[:3] + FRONTED)
def test_strict_mode_still_reads_the_words_as_written(a, b):
    assert S(a, b) == "INCONCLUSIVE"                       # the rewrites happen after `norm`: strict never proves a paraphrase


@pytest.mark.parametrize("a,b", [("Submit the report.", "Submit the report at the latest."),                      # a bare 'at the latest' is content, not a rewrite
                                 ("Submit the report before Friday.", "Submit the report no later than Friday."),   # before excludes the day, no later than includes it
                                 ("Submit the report by Friday.", "Submit the report no later than Saturday."),
                                 ("After the backup finishes, delete the old logs.", "Delete the old logs before the backup finishes."),
                                 ("Before the meeting starts, close the doors.", "Close the doors after the meeting starts."),
                                 ("Every Monday, send the report.", "Send the report every Tuesday."),
                                 ("Every user, send me the report.", "Send me the report every user.")])
def test_guards_are_still_not_proven_equivalent(a, b):
    assert V(a, b) != "EQUIVALENT"


@pytest.mark.parametrize("a,b", [("Do not share the admin password with anyone.", "Never share the admin password with anyone."),
                                 ("Não envie nenhum arquivo ao cliente.", "Não envie qualquer arquivo ao cliente."),
                                 ("No compartas la clave con nadie.", "Nunca compartas la clave con nadie.")])
def test_never_and_qualquer_on_one_side_only_are_not_proven(a, b):
    assert V(a, b) != "EQUIVALENT"


@pytest.mark.parametrize("a", ["Never share the password.", "Nunca compartas la contraseña.", "Não envie qualquer arquivo ao cliente."])
def test_same_word_on_both_sides_is_still_equivalent(a):
    assert V(a, a) == "EQUIVALENT"
