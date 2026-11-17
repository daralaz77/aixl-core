"""2026-11-17 (blind32 round): guard pairs for lexicon entries that were tried and NOT merged: 'no fewer than' = 'at least' (+1 of 30 fresh pairs, below the pre-registered +2, see data/blind32),
and two entries removed after an independent audit of 440 pairs ('jamais' as a negation word; 'com exce\u00e7\u00e3o de / do / da / dos / das' as an exception phrase). These pairs are NOT equivalent in meaning;
the last five are false accepts the audit found in the removed entries. Any future bound / negation / exception entry must keep every one of them unproven. They pass on main because it has none of those entries."""
import pytest

from aixl.semantic import compare_texts

V = lambda a, b: compare_texts(a, b).verdict  # noqa: E731

GUARDS = [("Keep at least five days of logs.", "Keep no more than five days of logs."),                  # opposite bound
          ("Keep at least five days of logs.", "Keep no fewer than six days of logs."),                  # other number
          ("Keep at least five days of logs.", "Keep fewer than five days of logs."),                    # fewer than = less than
          ("Keep no fewer than five days of logs.", "Keep exactly five days of logs."),                  # exact
          ("Keep no fewer than five days of logs.", "Keep more than five days of logs."),                # strict greater
          ("Keep no fewer than five days of logs.", "Keep at most five days of logs."),
          ("Nunca deixe o servidor sem senha.", "Deixe o servidor sem senha."),                          # negation dropped
          ("Jamais deixe o servidor sem senha.", "Sempre deixe o servidor sem senha."),                  # opposite
          ("Jamais deixe o servidor sem senha.", "Nunca deixe o cofre sem senha."),                      # other object
          ("Jamais deixe o servidor sem senha.", "Não deixe o servidor sem senha."),                # 'jamais' vs plain 'não': strength is not proven
          ("Reinicie todos os servidores, com exceção do de banco de dados.", "Reinicie todos os servidores."),                 # exception dropped
          ("Reinicie todos os servidores, com exceção do de banco de dados.", "Reinicie todos os servidores, exceto o de aplicação."),   # other exception
          ("Reinicie os servidores com exceção do de banco de dados.", "Reinicie apenas o servidor de banco de dados.")]       # exception vs only


@pytest.mark.parametrize("a,b", GUARDS)
def test_guards_never_prove_equal(a, b):
    assert V(a, b) != "EQUIVALENT" and V(b, a) != "EQUIVALENT"
