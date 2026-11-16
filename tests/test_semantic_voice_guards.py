"""2026-11-16 (blind31 round): guard pairs for a comparator rule that was tried and NOT merged (a regular 'by' passive proven equal to its active sentence; it proved +1 of 20 fresh pairs, below the pre-registered +5, see data/blind31).
These active/passive pairs are NOT equivalent in meaning (roles swapped, negation, tense, number, possessives, gender, mood, means, deadline, ...). 11 come from the first author's list; 12 are the false accepts an independent adversarial audit found in the first
version of the rule (259 pairs). Any future active/passive rule must keep every one of them unproven. They pass on v0.7.1 because that version never rewrites a passive."""
import pytest

from aixl.semantic import compare_texts

V = lambda a, b: compare_texts(a, b).verdict  # noqa: E731

GUARDS = [("The auditor approves the payment.", "The auditor is approved by the payment."),                  # roles swapped
          ("El gerente aprueba los pagos.", "El gerente es aprobado por los pagos."),                          # roles swapped, es
          ("The manager approves the payment.", "The payments are approved by the manager."),                   # singular vs plural object (the ledger cannot see it: 'approves' looks plural)
          ("The manager reviews the check.", "The checks are reviewed by the manager."),                         # noun that looks like a verb
          ("The manager approves the payment.", "The payment is not approved by the manager."),                 # negation on one side
          ("The manager approved the payment.", "The payment will be approved by the manager."),                # past vs future
          ("The system sends the receipt.", "The receipt is reviewed by the system."),                           # a different verb
          ("The report is sent by email.", "Email sends the report."),                                           # 'by' is a means, not an agent
          ("The payment is approved by Friday.", "Friday approves the payment."),                                # 'by' is a deadline
          ("The team approves the refund and the bonus.", "The refund and the bonus are approved by the team."),   # coordination: grouping not proven
          ("El sistema envía el recibo al cliente.", "El recibo es enviado por el sistema."),                   # one side adds a recipient
          # the 12 false accepts found by the independent adversarial audit of the first version of the rule (259 pairs, all INCONCLUSIVE now)
          ("El gerente está aprobando el pago.", "El pago es aprobado por el gerente."),                       # progressive
          ("El gerente aprobó el pago.", "El pago es aprobado por el gerente."),                                # preterite
          ("El gerente aprobaba el pago.", "El pago es aprobado por el gerente."),                              # imperfect
          ("The manager is approving the payment.", "The payment is approved by the manager."),                 # progressive (en)
          ("El sistema revisa el análisis.", "Los análisis son revisados por el sistema."),                      # invariant noun, singular vs plural article
          ("El gerente aprueba su pago.", "El pago es aprobado por el gerente."),                               # possessive on the patient
          ("El pago es aprobado por su gerente.", "El gerente aprueba el pago."),                               # possessive on the agent
          ("El gerente aprueba este pago.", "El pago es aprobado por el gerente."),                             # demonstrative
          ("El gerente se aprueba el pago.", "El pago es aprobado por el gerente."),                            # clitic 'se'
          ("¿Aprueba el gerente el pago?", "El pago es aprobado por el gerente."),                              # question vs statement
          ("El gerente aprueba el pago.", "El pago está aprobado por el gerente."),                             # 'estar' + participle: a state
          ("El gerente aprueba el pago.", "El pago es aprobado por la gerente.")]                               # gender of the agent


@pytest.mark.parametrize("a,b", GUARDS)
def test_guards_never_prove_equal(a, b):
    assert V(a, b) != "EQUIVALENT" and V(b, a) != "EQUIVALENT"
