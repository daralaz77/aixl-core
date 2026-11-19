"""Slot binding (which day / hour / number / bound / modal belongs to which action), relative-clause negation and the closed-shape rewrites (blind33 round).
Every NOT_EQUIVALENT pair here was accepted as EQUIVALENT by the comparator at 0.7.1; every control pair must stay proven."""
import pytest

from aixl.semantic import compare_texts


def V(a, b):
    return compare_texts(a, b).verdict


SWAPS = [("Back up the data on Monday and migrate on Tuesday.", "Back up the data on Tuesday and migrate on Monday."),
         ("Haz la copia el lunes y migra el martes.", "Haz la copia el martes y migra el lunes."),
         ("Faça o backup na segunda e migre na terça.", "Faça o backup na terça e migre na segunda."),
         ("Pay today and submit tomorrow.", "Pay tomorrow and submit today."),
         ("Run job A at 9:00 and job B at 10:00.", "Run job A at 10:00 and job B at 9:00."),
         ("Pay before Monday and submit after Friday.", "Pay after Friday and submit before Monday."),
         ("You must back up the data and you may restart the server.", "You may back up the data and you must restart the server."),
         ("You must back up the data\nyou may restart the server.", "You may back up the data\nyou must restart the server."),
         ("You must back up the data - you may restart the server.", "You may back up the data - you must restart the server."),
         ("You must not approve and publish.", "You must not approve and must publish."),
         ("Keep at least 3 copies and wait at most 5 minutes.", "Keep at most 5 copies and wait at least 3 minutes."),
         ("Keep up to 3 copies and wait at least 5 minutes.", "Keep at least 5 copies and wait up to 3 minutes."),
         ("Apart from the first step, repeat the rest and skip the checks.", "Repeat the rest and skip the checks apart from the first step.")]

RELATIVE = [("Employees who never miss a meeting receive a bonus.", "Employees who miss a meeting never receive a bonus."),
            ("Students who do not cheat pass the exam.", "Students who cheat do not pass the exam."),
            ("Os alunos que n\u00e3o colam passam na prova.", "Os alunos que colam n\u00e3o passam na prova."),
            ("Los empleados que nunca llegan tarde reciben un bono.", "Los empleados que llegan tarde nunca reciben un bono."),
            ("Certifique-se de que o script n\u00e3o sobrescreva a configura\u00e7\u00e3o e crie um backup.", "Certifique-se de que o script sobrescreva a configura\u00e7\u00e3o e n\u00e3o crie um backup.")]

RULE_GUARDS = [("You do not have to deploy on Friday.", "You must not deploy on Friday."),         # 'do not have to' is not 'must not'
               ("You don't have to back up the data.", "You must back up the data."),
               ("Keep 5 or more backups.", "Keep at most 5 backups."),
               ("Keep 5 or fewer backups.", "Keep at least 5 backups."),
               ("Keep a minimum of 5 backups.", "Keep at most 5 backups."),
               ("Back up the data, but do not restart the server.", "Back up the data; restart the server."),
               ("Tell the team which tasks are not finished.", "Tell the team that tasks are not finished."),   # an interrogative 'which' is not a relative 'that'
               ("Ask who is not ready.", "Ask that is not ready.")]

CONTROLS = [("Run the job on Monday and Tuesday.", "Run the job on Tuesday and Monday."),
            ("Back up on Monday and migrate on Tuesday.", "Back up on Monday, and migrate on Tuesday."),
            ("Delete the files that are not encrypted.", "Delete the files which are not encrypted."),
            ("Contact the clients who have not paid.", "Contact the clients that have not paid."),
            ("Keep at least 5 backups.", "Keep 5 or more backups."),
            ("Keep at most 5 backups.", "Keep 5 or fewer backups."),
            ("Keep at least 5 backups.", "Keep a minimum of 5 backups."),
            ("Guarda al menos 5 copias.", "Guarda 5 o m\u00e1s copias."),
            ("No, at most three.", "No, three at most."),
            ("You must back up the data.", "You have to back up the data."),
            ("Debes hacer la copia.", "Tienes que hacer la copia."),
            ("Back up the data, but do not restart the server.", "Back up the data; do not restart the server."),
            ("Unless it is raining, the drill takes place outdoors.", "The drill takes place outdoors, except when it is raining."),     # found by blind33 (a false REJECT)
            ("Todos deben fichar, excepto el personal de limpieza.", "Salvo el personal de limpieza, todos deben fichar.")]               # blind33: the front-exception guard must not fire with a single action


@pytest.mark.parametrize("a,b", SWAPS + RELATIVE + RULE_GUARDS)
def test_these_pairs_are_never_proven_equivalent(a, b):
    assert V(a, b) != "EQUIVALENT" and V(b, a) != "EQUIVALENT"


@pytest.mark.parametrize("a,b", CONTROLS)
def test_these_controls_are_proven_equivalent(a, b):
    assert V(a, b) == "EQUIVALENT" and V(b, a) == "EQUIVALENT"


MODAL_SUBSTITUTIONS = [("The project plan should be updated daily and you must attend the weekly review.", "The project plan should be updated daily and you may attend the weekly review."),
                       ("The meeting should start at 10 AM and you may adjust the agenda.", "The meeting must start at 10 AM and you should adjust the agenda."),
                       ("Os funcionários podem atender os clientes e devem limpar o chão.", "Os funcionários podem atender os clientes e podem limpar o chão.")]       # found by blind34 (post-hoc)


@pytest.mark.parametrize("a,b", MODAL_SUBSTITUTIONS)
def test_a_modal_changed_in_one_clause_is_never_proven_equivalent(a, b):
    assert V(a, b) != "EQUIVALENT" and V(b, a) != "EQUIVALENT"


def test_may_and_can_are_the_same_modal_class():
    assert V("You may back up the data and you must restart the server.", "You can back up the data and you must restart the server.") == "EQUIVALENT"
