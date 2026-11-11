"""2026-11-11 (blind30 round): one comparator rule written after reading blind28 and blind29, kept after the fresh test (+2 proven, no false accept):
'each / every / cada / todo' and 'all / todos' on the SUBJECT are proven equal when nothing is counted, summed, excepted or ordered; exactly one plural, carried by the
quantified subject, is not a difference. (A second rule, a passive with a modal rewritten to the active sentence, fired on no fresh pair and was reverted per the
pre-registration; its guards below stay, so a passive is still never proven equal to a different active sentence.)
Every positive has guards that must stay unproven. Strict mode keeps reading the words as written."""
import pytest

from aixl.semantic import compare_texts

V = lambda a, b: compare_texts(a, b).verdict  # noqa: E731
S = lambda a, b: compare_texts(a, b, strict=True).verdict  # noqa: E731

UNIVERSAL = [("Every user must change the password this month.", "Each user must change the password this month."),
             ("Cada usuário deve ter uma conta de e-mail.", "Todo usuário deve ter uma conta de e-mail."),
             ("Cada paquete debe llevar una etiqueta.", "Todos los paquetes deben llevar una etiqueta."),
             ("Every employee must sign in.", "All employees must sign in.")]


@pytest.mark.parametrize("a,b", UNIVERSAL)
def test_new_rule_proves_these_equal_in_both_directions(a, b):
    assert V(a, b) == "EQUIVALENT" and V(b, a) == "EQUIVALENT"


@pytest.mark.parametrize("a,b", UNIVERSAL)
def test_strict_mode_still_reads_the_words_as_written(a, b):
    assert S(a, b) == "INCONCLUSIVE"


@pytest.mark.parametrize("a,b", [("Each user may edit the page.", "Each user may edit the pages."),                          # an object plural is a difference
                                 ("Every user edits the pages.", "All users edit the page."),                                # the subject plural must not cancel an object plural
                                 ("Each file must be under 5 MB.", "All files must be under 5 MB."),                         # a number: per file or in total
                                 ("Revisa cada archivo antes de subirlo.", "Revisa todos los archivos antes de subirlos."),  # an order marker: per file or as a batch
                                 ("Cada usuário pode baixar o arquivo.", "Todos os usuários podem baixar os arquivos."),
                                 ("Every employee must sign in.", "Some employees must sign in."),
                                 ("All employees except Ana must sign in.", "Every employee must sign in."),
                                 ("All the files must be zipped together.", "Each file must be zipped.")])
def test_universal_guards_stay_unproven(a, b):
    assert V(a, b) != "EQUIVALENT" and V(b, a) != "EQUIVALENT"


@pytest.mark.parametrize("a,b", [("The auditor must approve the payment.", "The payment must be approved by the manager."),            # another agent
                                 ("The auditor must approve the payment.", "The auditor must be approved by the payment."),             # roles swapped
                                 ("The payment must be approved by the auditor.", "The auditor must be approved by the payment."),
                                 ("The auditor must approve the payment.", "The payment must not be approved by the auditor."),         # polarity
                                 ("The manager approves the report.", "The report is approved by the manager."),                        # no modal: tense is not fixed, left alone
                                 ("The auditor must approve the payment.", "The payment must be approved by the auditor and the manager."),
                                 ("Every manager must approve the payment.", "The payment must be approved by every manager.")])
def test_passive_guards_stay_unproven(a, b):
    assert V(a, b) != "EQUIVALENT" and V(b, a) != "EQUIVALENT"
