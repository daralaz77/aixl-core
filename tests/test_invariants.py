"""Critical-slot invariants (aixl.invariants / aixl.relay_check): near-verbatim relays, open vocabulary, no equivalence claim."""
import pytest

import aixl


@pytest.mark.parametrize("src,relay,family", [
    ("Borra los respaldos del servidor de pruebas.", "No borres los respaldos del servidor de pruebas.", "NEGATION"),
    ("Pay 100 dollars to Acme before Friday.", "Pay 1000 dollars to Acme before Friday.", "NUMBER"),
    ("Pay 100 dollars to Acme before Friday.", "Pay 100 dollars to Acme before Monday.", "WEEKDAY"),
    ("You must anonymize the export columns.", "You may anonymize the export columns.", "MODALITY"),
    ("Notify Ana and Luis about the incident.", "Notify Ana or Luis about the incident.", "DISJUNCTION"),
    ("Notify Ana and Luis about the incident.", "Notify Ana and Marta about the incident.", "NAME"),
    ("Si el cliente no pagó, márcalo como moroso.", "Márcalo como moroso.", "CONDITION"),
])
def test_corruptions_in_an_open_vocabulary_text_are_flagged(src, relay, family):
    r = aixl.relay_check(src, relay)
    assert r["ok"] is False and family in {v["family"] for v in r["violations"]}


@pytest.mark.parametrize("relay_of", [
    lambda t: t, lambda t: '"' + t + '"', lambda t: "**" + t.rstrip(".") + "**.", lambda t: "  " + t + "  \n",
    lambda t: "Please " + t[0].lower() + t[1:], lambda t: "Por favor, " + t[0].lower() + t[1:],
])
@pytest.mark.parametrize("src", [
    "Se o pedido estiver atrasado mais de cinco dias, ofereça frete grátis.", "No borres ningún ticket cerrado aunque tenga más de un año.",
    "Quando o chamado ficar parado por mais de 48 horas, avise o gerente.", "Escalate the zebra-crossing complaints to the municipal desk by Friday.",
])
def test_benign_formatting_edits_are_not_flagged(src, relay_of):
    assert aixl.relay_check(src, relay_of(src))["ok"] is True


def test_ok_is_never_an_equivalence_claim():
    r = aixl.relay_check("Send the report to Ana.", "Send the invoice to Ana.")        # a noun swap: vocabulary-only, invisible BY DESIGN
    assert r["ok"] is True and "not a proof" in r["note"]


def test_unanalysable_input_fails_closed():
    r = aixl.relay_check("x" * 100_000, "y")
    assert r["ok"] is False and "not analysed" in r["reason"]


def test_mcp_tool_is_exposed_and_matches_the_api():
    from aixl import mcp_server
    assert mcp_server.aixl_relay_check("Delete the logs.", "Do not delete the logs.") == aixl.relay_check("Delete the logs.", "Do not delete the logs.")


@pytest.mark.parametrize("src,relay,family", [
    ("Send the report to Ana and notify Luis.", "Cancel the report to Ana and notify Luis.", "ACTION"),
    ("Pide a Ana que revise el informe de Luis.", "Pide a Luis que revise el informe de Ana.", "NAME_ORDER"),
    ("Tell Marta that she can approve it.", "Tell Marta that he can approve it.", "PRONOUN"),
])
def test_blind_spots_closed_action_role_and_pronoun(src, relay, family):
    r = aixl.relay_check(src, relay)
    assert r["ok"] is False and family in {v["family"] for v in r["violations"]}
