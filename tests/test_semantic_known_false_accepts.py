"""2026-11-17: pairs that are NOT equivalent in meaning but that the comparator (v0.7.1 / main 04e9574, identical code path) calls EQUIVALENT. Found by an independent adversarial audit
of 440 pairs (OLD code, before any lexicon change). They are recorded as strict xfail: when someone fixes a class, the test flips to XPASS(strict) and fails the suite, which is the
signal to delete the marker. Do NOT 'fix' them by adding these sentences to a lexicon: each is a CLASS (negation scope, number of an excepted set, a 'no,' answer glued to a bound)."""
import pytest

from aixl.semantic import compare_texts

KNOWN = [("Never save, but delete.", "Save, but never delete."),                                               # negation scope moves: 'do not save' vs 'do not delete'
         ("Nunca salve, mas apague.", "Salve, mas nunca apague."),                                             # same, pt
         ("Reinicie tudo, exceto o teste.", "Reinicie tudo, exceto os testes."),                                # number of the excepted set ignored
         ("Reinicie todos os servidores, exceto os de teste.", "Reinicie todos os servidores, exceto o de teste."),
         ("Keep logs? No, fewer than five days.", "Keep logs? No fewer than five days."),                      # the comma after an answer 'no' is ignored
         ("The answer is no, fewer than five servers.", "The answer is at least five servers."),
         ("Should I keep logs for a week? No, fewer than five days.", "Should I keep logs for a week? At least five days.")]


@pytest.mark.xfail(strict=True, reason="known false accept of the published comparator, see module docstring")
@pytest.mark.parametrize("a,b", KNOWN)
def test_known_false_accept_is_still_accepted(a, b):
    assert compare_texts(a, b).verdict != "EQUIVALENT" and compare_texts(b, a).verdict != "EQUIVALENT"
