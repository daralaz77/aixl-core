"""FASE 8 tests — the live negotiation protocol (aixl/negotiation.py), 2026-09-29."""
from datetime import date

import pytest

from aixl import negotiation as neg
from aixl.translators.natural_to_semantic import to_graph

T = date(2026, 9, 29)


def canon(text):
    return to_graph(text, today=T).canonical()


# ---- wire format ----------------------------------------------------------------------------------

def test_encode_decode_roundtrip_request():
    t = neg.NegotiationTurn("REQUEST", "M1", payload="V:AIXL-0.3 I:REQUEST_EXECUTION A:DELETE Y:#77")
    back = neg.decode(t.encode())
    assert back.turn_type == "REQUEST" and back.msg_id == "M1" and back.payload == t.payload


def test_encode_decode_roundtrip_clarify_with_quoted_fields():
    t = neg.NegotiationTurn("CLARIFY", "M2", ref_id="M1", dim="actions", candidates=("DELETE", "UPDATE"),
                            question='ACTION: receiver read "DELETE", sender implies "UPDATE" — which is correct?')
    back = neg.decode(t.encode())
    assert back.turn_type == "CLARIFY" and back.ref_id == "M1" and back.dim == "actions"
    assert back.candidates == ("DELETE", "UPDATE")
    assert back.question == t.question


def test_encode_decode_roundtrip_answer_and_accept_and_reject():
    a = neg.decode(neg.NegotiationTurn("ANSWER", "M3", ref_id="M2", dim="actions", value="UPDATE").encode())
    assert a.value == "UPDATE"
    acc = neg.decode(neg.NegotiationTurn("ACCEPT", "M4", ref_id="M3").encode())
    assert acc.turn_type == "ACCEPT" and acc.ref_id == "M3"
    rej = neg.decode(neg.NegotiationTurn("REJECT", "M5", ref_id="M3", reason="no consensus after 3 rounds").encode())
    assert rej.reason == "no consensus after 3 rounds"


def test_decode_rejects_malformed_input_without_crashing():
    with pytest.raises(neg.NegotiationError):
        neg.decode("this is not a negotiation line")
    with pytest.raises(neg.NegotiationError):
        neg.decode("NEGOTIATE MSG=M1")                     # missing X=
    with pytest.raises(neg.NegotiationError):
        neg.decode("NEGOTIATE X=BOGUS MSG=M1")              # unknown turn type


def test_turn_encode_rejects_unknown_type():
    with pytest.raises(neg.NegotiationError):
        neg.NegotiationTurn("BOGUS", "M1").encode()


# ---- negotiation state machine --------------------------------------------------------------------

def test_negotiate_converges_on_single_dimension_disagreement():
    # "archive" (DISABLE) vs an encoder that guessed UPDATE — a reversible actions disagreement, unlike
    # the Close/Delete pair used before E-MCP's destructive-action escalation fix (2026-09-30): that pair
    # now correctly REJECTs instead (see test_negotiate_rejects_an_irreversible_action_disagreement below),
    # so it stopped being a valid example of plain single-dimension convergence.
    sender = canon("Archive ticket #77.")
    receiver = canon("Update ticket #77.")
    assert sender["actions"] != receiver["actions"]          # sanity: they really do disagree going in
    out = neg.negotiate(sender, receiver, max_rounds=3)
    assert out.converged is True
    assert out.rounds == 1
    assert out.remaining_differences == []
    assert out.final_receiver_canonical["actions"] == sender["actions"]
    types = [t.turn_type for t in out.transcript]
    assert types == ["REQUEST", "CLARIFY", "ANSWER", "ACCEPT"]
    assert out.transcript[1].dim == "actions"                # the CLARIFY names the disputed dimension
    assert out.transcript[2].value == neg._fmt(sender["actions"])


def test_negotiate_resolves_multiple_dimensions_within_rounds():
    # UPDATE, not DELETE, on the receiver side — DELETE would trigger E-MCP's irreversible-action REJECT
    # (2026-09-30) before every dimension gets a chance to be negotiated, which isn't what this test checks.
    sender = canon("Send the report to Acme before 15:00.")
    receiver = canon("Update the document from Nova after 09:00.")
    n_diffs_before = len(neg.compare_canonical(sender, receiver).differences)
    assert n_diffs_before >= 2
    out = neg.negotiate(sender, receiver, max_rounds=6)
    assert out.converged is True
    assert out.rounds == n_diffs_before
    assert out.final_receiver_canonical == {**receiver, **{k: sender[k] for k in sender if sender[k] != receiver.get(k)}} \
        or neg.compare_canonical(sender, out.final_receiver_canonical).equivalent


def test_negotiate_rejects_after_max_rounds_instead_of_looping_forever():
    sender = canon("Send the report to Acme before 15:00.")
    receiver = canon("Update the document from Nova after 09:00.")
    n_diffs = len(neg.compare_canonical(sender, receiver).differences)
    assert n_diffs >= 2
    out = neg.negotiate(sender, receiver, max_rounds=1)
    assert out.converged is False
    assert out.rounds == 1
    assert len(out.remaining_differences) == n_diffs - 1     # exactly one dimension was resolved before the cap
    assert out.transcript[-1].turn_type == "REJECT"
    assert "no consensus after 1 rounds" in out.transcript[-1].reason


def test_negotiate_prioritizes_critical_severity_first():
    # negation is always CRITICAL severity; time here is MAJOR — CRITICAL must be negotiated in round 1
    sender = canon("Delete the report for this year.")
    receiver = canon("Do not delete the report for last year.")
    result = neg.compare_canonical(sender, receiver)
    fields = {d.field for d in result.differences}
    assert "NEGATION" in fields and len(fields) >= 2         # sanity: genuinely a multi-dimension, negation-included case
    out = neg.negotiate(sender, receiver, max_rounds=5)
    assert out.transcript[1].turn_type == "CLARIFY"
    assert out.transcript[1].dim == "negation"               # CRITICAL dimension negotiated before MAJOR ones
    assert out.converged is True


def test_negotiate_already_equivalent_needs_no_rounds():
    g = canon("Send the report to Acme.")
    out = neg.negotiate(g, dict(g), max_rounds=3)
    assert out.converged is True
    assert out.rounds == 0
    assert [t.turn_type for t in out.transcript] == ["REQUEST", "ACCEPT"]


def test_negotiate_accepts_when_last_round_exactly_resolves_at_the_cap():
    # found by running negotiate() on real E-INTEROP round-3 disagreements with max_rounds set to
    # EXACTLY the number of differing dimensions (the natural way to size the cap): the round that
    # patches the LAST dimension must still be re-checked for equivalence, or a negotiation that
    # resolves everything right at the cap was wrongly reported REJECTED (0/21 real cases "converged"
    # until this was fixed, despite every dimension actually having been resolved).
    # DISABLE vs UPDATE, not DELETE (E-MCP's irreversible-action REJECT, 2026-09-30, would otherwise fire
    # here instead of testing the round-cap edge case this test is actually about).
    sender = canon("Archive ticket #77.")
    receiver = canon("Update ticket #77.")
    n_diffs = len(neg.compare_canonical(sender, receiver).differences)
    out = neg.negotiate(sender, receiver, max_rounds=n_diffs)   # no spare round
    assert out.converged is True
    assert out.remaining_differences == []
    assert out.transcript[-1].turn_type == "ACCEPT"


def test_candidates_use_semicolon_so_a_multivalue_reading_survives_roundtrip():
    # found live (E-NEGOTIATE demo, 2026-09-29): an independent model, given only the v1 spec (which said
    # "CANDIDATES=<a>,<b>"), naturally wrote a comma-joined multi-value candidate ("REPORT,DATA") and
    # produced CANDIDATES=REPORT,DATA,REPORT — indistinguishable from 3 separate one-word candidates.
    # Fixed: ';' separates candidates, ',' stays free inside one candidate.
    t = neg.NegotiationTurn("CLARIFY", "M2", ref_id="M1", dim="data", candidates=("REPORT,DATA", "REPORT"))
    back = neg.decode(t.encode())
    assert back.candidates == ("REPORT,DATA", "REPORT")
    assert "CANDIDATES=REPORT,DATA;REPORT" in t.encode()


def test_negotiate_clarify_names_receiver_and_sender_the_right_way_round():
    # found by reading REAL `cli.py negotiate` output, not by any unit test above (they only checked the
    # final resolved ANSWER value, which is computed independently and was always correct even while this
    # was backwards): the CLARIFY's candidates and question text had receiver/sender swapped.
    sender = canon("Close ticket #77.")           # -> UPDATE
    receiver = canon("Delete ticket #77.")         # -> DELETE
    out = neg.negotiate(sender, receiver, max_rounds=3)
    clarify = out.transcript[1]
    assert clarify.candidates == ("DELETE", "UPDATE")            # (receiver's value, sender's value)
    assert "receiver read 'DELETE'" in clarify.question
    assert "sender's own message implies 'UPDATE'" in clarify.question


def test_negotiate_rejects_rather_than_silently_discard_a_correct_reading_when_sender_cant_resolve_actions():
    # found by a REAL third-party MCP client (Claude Desktop, E-MCP, 2026-09-30): "quita" is outside the
    # rule-based vocabulary, so the sender's own re-derived `actions` is empty/NOT_SPECIFIED. Before this
    # fix, negotiate() adopted that emptiness anyway and reported ACCEPT/converged, silently discarding the
    # receiver's plausibly-correct DELETE reading with no signal anything was lost — worse than an honest
    # REJECT, especially for a destructive action. Now it must REJECT instead of guessing wrong for free.
    sender = canon("Quita el ticket #77.")         # -> actions=() (out-of-vocabulary verb, unresolved)
    receiver = canon("Elimina el ticket #77.")     # -> DELETE
    out = neg.negotiate(sender, receiver, max_rounds=3)
    assert out.converged is False
    assert out.transcript[-1].turn_type == "REJECT"
    assert "does not resolve" in out.transcript[-1].reason
    assert any(d.field == "ACTION" for d in out.remaining_differences)


def test_negotiate_still_adopts_a_legitimately_empty_dimension_other_than_actions():
    # the fix above is scoped to `actions` only: a genuinely correct empty value on another dimension
    # (here, the sender really states no prohibition) must still be adopted and converge — rejecting
    # every empty sender value would be over-broad and was caught regressing this real case.
    sender = canon("Delete the report for this year.")              # -> no negation stated (correct)
    receiver = canon("Do not delete the report for last year.")     # -> FORBID:DELETE
    out = neg.negotiate(sender, receiver, max_rounds=5)
    assert out.converged is True


def test_negotiate_rejects_an_irreversible_action_disagreement_instead_of_trusting_the_sender():
    # found by a REAL third-party MCP client (Claude Desktop, E-MCP, 2026-09-30) testing
    # aixl_negotiate_autonomous: "Close ticket #77." (UPDATE) vs "Delete ticket #77." (DELETE) used to
    # ACCEPT/converge on UPDATE after just 1 round, purely because the sender said so — with no signal
    # that DELETE, the OTHER candidate, is irreversible and the sender could be wrong. Confirmed
    # systematic across 3 real pairs (Close/Delete, Archive/Delete, Send/Delete) before fixing, per
    # aixl-core's evidence-before-fix discipline. Now it must REJECT and say why, not silently pick a
    # side on something a wrong guess can't undo.
    sender = canon("Close ticket #77.")            # -> UPDATE
    receiver = canon("Delete ticket #77.")          # -> DELETE
    out = neg.negotiate(sender, receiver, max_rounds=3)
    assert out.converged is False
    assert out.transcript[-1].turn_type == "REJECT"
    assert "irreversible action" in out.transcript[-1].reason
    assert any(d.field == "ACTION" for d in out.remaining_differences)


def test_negotiate_still_resolves_a_merely_destructive_but_reversible_action_disagreement():
    # narrowing check: UPDATE and SEND are both on comparator's broader `destructive_actions` list (used
    # only for CRITICAL severity display) but NEITHER is on the narrower `irreversible_actions` list
    # (DELETE only) that gates the REJECT above — a first, broader attempt reusing `destructive_actions`
    # directly broke exactly this kind of case (any UPDATE-involving disagreement), caught by the
    # existing test suite before it shipped. Reversible actions must still resolve normally.
    sender = canon("Send the invoice.")             # -> SEND
    receiver = canon("Update the invoice.")          # -> UPDATE
    out = neg.negotiate(sender, receiver, max_rounds=3)
    assert out.converged is True
    assert out.transcript[-1].turn_type == "ACCEPT"
