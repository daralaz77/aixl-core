"""aixl.logic: propositional-skeleton equivalence over identical clauses. Fail-closed: anything it cannot read, it abstains on."""
import pytest

from aixl.logic import MAX_ATOMS, logic_compare


def v(a, b):
    return logic_compare(a, b)["verdict"]


@pytest.mark.parametrize("a,b", [
    ("Send the report if the client approves.", "If the client approves, send the report."),
    ("It is not true that we ship and we invoice.", "We do not ship or we do not invoice."),
    ("It is not true that we do not ship.", "We ship."),
    ("Notify Ana unless the ticket is closed.", "Notify Ana if the ticket is not closed."),
    ("Approve the plan if (the client signs or the manager signs) and the budget is open.",
     "Approve the plan if (the client signs and the budget is open) or (the manager signs and the budget is open)."),
    ("Si el cliente aprueba, envía el informe.", "Envía el informe si el cliente aprueba."),
    ("No es cierto que enviemos el informe y facturemos.", "No enviemos el informe o no facturemos."),
    ("Notify Ana if the ticket is closed or the client cancels.", "Notify Ana if the client cancels or the ticket is closed."),
])
def test_equivalent_logic(a, b):
    assert v(a, b) == "EQUIVALENT_LOGIC"


@pytest.mark.parametrize("a,b", [
    ("Send the report if the client approves.", "Send the report only if the client approves."),
    ("Approve the plan if (the client signs or the manager signs) and the budget is open.", "Approve the plan if the client signs or (the manager signs and the budget is open)."),
    ("Envie o relatório se o cliente aprovar.", "Envie o relatório somente se o cliente aprovar."),
    ("If the client approves, send the report.", "If the client approves, do not send the report."),
    ("Send the report and notify Ana.", "Send the report or notify Ana."),
])
def test_different_logic_has_a_counterexample(a, b):
    r = logic_compare(a, b)
    assert r["verdict"] == "DIFFERENT_LOGIC" and r["counterexample"] and r["a_holds"] != r["b_holds"]


@pytest.mark.parametrize("a,b", [
    ("Send the report and notify Ana or close the ticket.", "Send the report and notify Ana or close the ticket."),                 # mixed and/or, no parentheses
    ("If the client approves, send the report.", "If the report is sent, the client approves."),                                      # the clauses differ
    ("It is not true that we ship if the client pays.", "We ship if the client pays."),                                               # ambiguous scope
    ("If A is true, if B is true, ship.", "x"),                                                                                       # nested / malformed
    ("", "Send the report."),
    ("Send the report.", ""),
])
def test_abstains_instead_of_guessing(a, b):
    assert v(a, b) == "ABSTAIN"


def test_different_clauses_are_never_called_equivalent():
    r = logic_compare("Send the report to Ana if the client approves.", "Send the report to Luis if the client approves.")
    assert r["verdict"] == "ABSTAIN" and r["only_in_a"] and r["only_in_b"]


def test_too_many_clauses_abstain():
    txt = " and ".join(f"clause number {i} holds" for i in range(MAX_ATOMS + 1))
    assert v(txt, txt) == "ABSTAIN"


def test_oversize_input_does_not_raise():
    assert v("a" * 100000, "b") == "ABSTAIN"


def test_action_order_may_matter_so_it_abstains():
    """found on an older, independent set: `fetch X and generate Y` is labelled different from `generate Y and fetch X`."""
    assert v("Fetch top 10 sales records and generate a JSON file.", "Generate a JSON file and fetch top 10 sales records.") == "ABSTAIN"


def test_negation_position_matters_with_a_modal():
    assert v("It is not necessary to restart the server after the patch.", "It is necessary not to restart the server after the patch.") == "ABSTAIN"


def test_condition_order_does_not_matter():
    assert v("Notify Ana if the ticket is closed and the client cancels.", "Notify Ana if the client cancels and the ticket is closed.") == "EQUIVALENT_LOGIC"
