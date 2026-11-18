"""2026-11-17: seven pairs that are NOT equivalent in meaning but that the published comparator (v0.7.1 / main 04e9574) called EQUIVALENT, found by an independent adversarial audit, and their fix.
Three classes: (1) NEGATION SCOPE: the parser gives the whole step one polarity, so a negation in another clause ('Never save, but delete' / 'Save, but never delete') made the texts
identical; now a negation word whose clause (a hard break is ':', ';', but, while, so, or, pero, mas, ...) differs between the texts leaves the pair INCONCLUSIVE. (2) THE EXCEPTED SET: 'exceto o teste' / 'exceto os testes' and 'exceto os de teste' / 'exceto o de teste' differ in the
number of the excepted set (the noun plural was invisible to the dropped-feature ledger because it lives in the EXCEPT atom; the article number was ignored); now both leave the pair INCONCLUSIVE. (3) AN ANSWER 'no,': a comma
right after 'no / não' stays in the identity check and is flagged (AMBIGUOUS_ANSWER_NO): 'No, fewer than five' is an answer, not 'no fewer than five'.
The controls below are equivalent pairs that must KEEP being proven: they get the same verdict on v0.7.1 and after the fix."""
import pytest

from aixl.semantic import compare_texts

V = lambda a, b: compare_texts(a, b).verdict  # noqa: E731

FIXED = [("Never save, but delete.", "Save, but never delete."),
         ("Nunca salve, mas apague.", "Salve, mas nunca apague."),
         ("Reinicie tudo, exceto o teste.", "Reinicie tudo, exceto os testes."),
         ("Reinicie todos os servidores, exceto os de teste.", "Reinicie todos os servidores, exceto o de teste."),
         ("Keep logs? No, fewer than five days.", "Keep logs? No fewer than five days."),
         ("The answer is no, fewer than five servers.", "The answer is at least five servers."),
         ("Should I keep logs for a week? No, fewer than five days.", "Should I keep logs for a week? At least five days."),
         # found by the independent audit of the first fix (class 1: other clause breaks; class 2: the excepted noun pooled with the main noun; class 3: other marks and answer words)
         ("Do not save the file: delete the copy.", "Save the file: do not delete the copy."),
         ("Don't save the file while deleting the copy.", "Save the file while not deleting the copy."),
         ("Do not save the file, so delete the copy.", "Save the file, so do not delete the copy."),
         ("Save, but delete, but never archive.", "Save, but never delete, but archive."),
         ("Restart the server except the tests.", "Restart the servers except the test."),
         ("Restart all servers except the test server and the staging servers.", "Restart all servers except the test servers and the staging server."),
         ("Keep logs? No. Fewer than five days.", "Keep logs? No fewer than five days."),
         ("Keep logs? No; fewer than five days.", "Keep logs? No fewer than five days."),
         ("Keep logs? No \u2014 more than five days.", "Keep logs? No more than five days."),
         ("Should I save? Nunca, borra el archivo.", "Should I save? Nunca borra el archivo."),
         ("Should I save? Don't, delete the file.", "Should I save? Don't delete the file."),
         ("Keep logs? None, fewer than five days.", "Keep logs? None fewer than five days."),
         # second independent audit (274 + 1806 pairs): negation scope with a coordinator and no hard break, exception words the parser does not model, other marks / wrappers / answer words
         ("Never email the client and notify the manager.", "Email the client and never notify the manager."),
         ("Do not ping and quarantine the client.", "Ping and do not quarantine the client."),
         ("No cifre el informe y dispare el aviso.", "Cifre el informe y no dispare el aviso."),
         ("N\u00e3o cadastre o cliente e crie o chamado.", "Cadastre o cliente e n\u00e3o crie o chamado."),
         ("Restart the server minus the test servers.", "Restart the servers minus the test server."),
         ("Reinicia todo, sin el de prueba.", "Reinicia todo, sin los de prueba."),
         ("Reinicia todo excepto el de prueba y el de staging.", "Reinicia todo excepto el de prueba y los de staging."),
         ("Reinicie todos os servidores, excluindo o de teste.", "Reinicie todos os servidores, excluindo os de teste."),
         ("Keep logs? **No** \u2014 fewer than five days.", "Keep logs? **No** fewer than five days."),
         ("Keep logs? No / fewer than five days.", "Keep logs? No fewer than five days."),
         ("Keep logs? nah, fewer than five days.", "Keep logs? nah fewer than five days."),
         ("Are there five servers? There are not, fewer than five.", "Are there five servers? There are not fewer than five."),
         ("Keep logs?\nNo\nfewer than five days.", "Keep logs? No fewer than five days."),
         # third independent audit (447 fresh pairs): more connectors as clause breaks, prohibition words, contracted articles / demonstratives, 'no one', underscores, multi-word answers
         ["The ticket must not be closed, otherwise the customer is notified.", "The ticket must be closed, otherwise the customer is not notified."],
         ["Nao salve o arquivo, alem disso apague a copia.", "Salve o arquivo, alem disso nao apague a copia."],
         ["Esta prohibido guardar el archivo, pero se debe borrar la copia.", "Se debe guardar el archivo, pero esta prohibido borrar la copia."],
         ["Reinicie todos os servidores, excetuando o de teste.", "Reinicie todos os servidores, excetuando os de teste."],
         ["Who may approve? No one, at most two managers.", "Who may approve? No one at most two managers."],
         ["Keep logs? _No_, fewer than five days.", "Keep logs? _No_ fewer than five days."],
         ["Keep logs? No way, fewer than five days.", "Keep logs? No way fewer than five days."],
         ["Can I reboot? You cannot, more than five users.", "Can I reboot? You cannot more than five users."]]

CONTROLS = [("Do not save the file, but delete the copy.", "Don't save the file, but delete the copy."),
            ("Never save the file, but delete the copy.", "Never save the file, but delete the copy."),
            ("Reinicie todos os servidores, exceto os de teste.", "Reinicie todos os servidores, exceto os de teste."),
            ("Restart all servers except the test servers.", "Restart all servers, except for the test servers."),
            ("Restart all servers except the test server.", "Restart all servers, other than the test server."),
            ("Keep logs? No fewer than five days.", "Keep logs? No fewer than five days."),
            ("Reply no, fewer than five days.", "Reply no, fewer than five days."),
            ("Do not keep more than five days of logs.", "Keep at most five days of logs."),
            ("Do not, under any circumstances, delete the file.", "Do not under any circumstances delete the file."),
            ("Do not, however, delete the file.", "Do not however delete the file."),
            ("Reinicia todos los servidores, excepto los de prueba.", "Reinicia todos los servidores, con excepci\u00f3n de los de prueba."),
            ("All staff must attend the fire drill except the night shift.", "All staff apart from the night shift must attend the fire drill."),
            ("Guarda al menos tres copias de cada backup.", "Guarda como m\u00ednimo tres copias de cada backup."),
            ("Delete the file? No.", "Delete the file? No!"),
            ("Should I save? No: it is locked.", "Should I save? No, it is locked."),
            ("Should I save? No; it is locked.", "Should I save? No, it is locked."),
            ["Staff must not, however, share the password.", "Staff must not however share the password."],
            ["Never, ever, disable the alarm.", "Never ever disable the alarm."],
            ["Never, under any circumstances, disable the alarm.", "Never under any circumstances disable the alarm."],
            ["Who may approve? Nobody, at most two managers.", "Who may approve? No one, at most two managers."]]


@pytest.mark.parametrize("a,b", FIXED)
def test_former_false_accept_is_no_longer_equivalent(a, b):
    assert V(a, b) != "EQUIVALENT" and V(b, a) != "EQUIVALENT"


@pytest.mark.parametrize("a,b", CONTROLS)
def test_control_equivalent_pair_is_still_proven(a, b):
    assert V(a, b) == "EQUIVALENT" and V(b, a) == "EQUIVALENT"


GAPS_NOW_CLOSED = [
    ("The host that is not patched must be quarantined.", "The host that is patched must not be quarantined."),
    ["Reinicie todas as maquinas, com excecao da de teste.", "Reinicie todas as maquinas, com excecao das de teste."],
    ["Delete every log but that of the auditor.", "Delete every log but those of the auditor."],
    ["Email the clients who have not paid.", "Do not email the clients who have paid."],
    ["The file is not saved, the copy must be deleted.", "The file is saved, the copy must not be deleted."],
    ["Step 2: Do not format the volume, mount the share.", "Step 2: Format the volume, do not mount the share."],
    ["Los equipos que no tienen cifrado deben apagarse.", "Los equipos que tienen cifrado no deben apagarse."],           # negation right before the modal, after a relative pronoun
    ["Should I wipe the disk? Don't, wipe the cache.", "Should I wipe the disk? Don't wipe the cache."],                    # answer + comma + a verb the lexicon does not know
    ["Reply with 'no, fewer than five days' if asked about logs.", "Reply with 'no fewer than five days' if asked about logs."],      # the quote before the answer word
    ["Provisiona ningun servidor y decomisiona las bases.", "Provisiona servidores y decomisiona ninguna base."],           # negative quantifier moved to the other clause
    ["Revoga as senhas, fora a do administrador e a do auditor.", "Revoga as senhas, fora a do administrador e as do auditor."],
    ["Reinicia todo, excepcion hecha del de prueba.", "Reinicia todo, excepcion hecha de los de prueba."],
    ["Can I reboot? Yes, fewer than five minutes.", "Can I reboot? Yes fewer than five minutes."],                          # an affirmative answer followed by a mark
    ["Debo borrar? No, mas de diez.", "Debo borrar? No mas de diez."],                                                         # found by audit 5: 'mas' is a comparative here, not a connector
    ["Check whether the user is not an admin.", "Do not check whether the user is an admin."],
    ["Restart the server but the test servers.", "Restart the servers but the test server."],
    ["Devo guardar? Tampouco, menos de cinco dias.", "Devo guardar? Tampouco menos de cinco dias."]]


@pytest.mark.parametrize("a,b", GAPS_NOW_CLOSED)
def test_formerly_open_gap_is_closed(a, b):
    assert V(a, b) != "EQUIVALENT" and V(b, a) != "EQUIVALENT"


GAP_CONTROLS = [("Can I reboot? Yes, but not now.", "Can I reboot? Yes but not now."),
                ("Neither the admin nor the auditor may approve the refund.", "Neither the admin, nor the auditor may approve the refund."),
                ("If the disk is full, do not write.", "Do not write if the disk is full."),
                ("Please, never delete the file.", "Please never delete the file."),
                ("Do not email the clients who have paid.", "Don't email the clients who have paid.")]


@pytest.mark.parametrize("a,b", GAP_CONTROLS)
def test_closing_the_gaps_keeps_these_proofs(a, b):
    assert V(a, b) == "EQUIVALENT" and V(b, a) == "EQUIVALENT"


# Design decision, not a hole: the KIND of the mark after an answer word is not meaning ('No, x' = 'No: x' = 'No/ x' = 'No ... x'): what is meaning is that there IS one ('No, x' / 'No x' stay apart).
MARK_KIND_IS_NOT_MEANING = [("Keep logs? No, fewer than five days.", "Keep logs? No/ fewer than five days."),
                            ("Keep logs? No, fewer than five days.", "Keep logs? No \u2026 fewer than five days.")]


@pytest.mark.parametrize("a,b", MARK_KIND_IS_NOT_MEANING)
def test_the_kind_of_mark_after_an_answer_is_not_meaning(a, b):
    assert V(a, b) == "EQUIVALENT"
