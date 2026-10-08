"""ADR-017 step 1: per-side completeness + structural markers (no tolerance parameter)."""
from aixl import compare_aixl, from_aixl
from aixl.core.completeness import annotate, check_completeness, extract_markers, marker_conflicts
from aixl.core.ontology import load_config

ON = {**load_config(), "inconclusive": True}
MOVE = "V:AIXL-0.3 I:REQUEST_EXECUTION A:UPDATE"


def test_short_value_is_content_not_noise():
    # 'sala B' vs 'sala C' (found in the blind10 simulation): the letter must be accounted for, or the side is incomplete
    g = from_aixl(MOVE + ' R:"reunión de presupuesto","sala"')
    assert "b" in check_completeness("Mueve la reunión de presupuesto a la sala B.", g)["unaccounted"]
    g2 = from_aixl(MOVE + ' R:"reunión de presupuesto","sala B"')
    assert check_completeness("Mueve la reunión de presupuesto a la sala B.", g2)["complete"]


def test_residue_key_separates_room_b_from_room_c():
    assert not compare_aixl(MOVE + ' R:"sala B"', MOVE + ' R:"sala C"').equivalent


def test_ordering_markers_are_extracted_and_opposed():
    ma, mb = extract_markers("Envía el recordatorio tres días antes del vencimiento."), extract_markers("Send the reminder three days after the due date.")
    assert "BEFORE" in ma and "AFTER" in mb
    assert marker_conflicts(ma, mb)[0] == [("BEFORE", "AFTER")]


def test_unreflected_marker_makes_a_side_incomplete():
    g = from_aixl("V:AIXL-0.3 I:REQUEST_EXECUTION A:SEND D:REPORT")           # encoder dropped 'only'
    r = check_completeness("Send only the report", g)
    assert not r["complete"] and r["unreflected_markers"] == ["ONLY"]


def test_marker_in_residue_counts_as_reflected():
    g = from_aixl('V:AIXL-0.3 I:REQUEST_EXECUTION A:SEND D:REPORT R:"only"')
    assert check_completeness("Send only the report", g)["complete"]


def test_opposed_markers_give_not_equivalent_even_if_residue_keys_agree():
    ga = annotate(from_aixl('V:AIXL-0.3 I:REQUEST_EXECUTION A:SEND D:REPORT R:"three days due date"'), "Send the report three days before the due date")
    gb = annotate(from_aixl('V:AIXL-0.3 I:REQUEST_EXECUTION A:SEND D:REPORT R:"three days due date"'), "Send the report three days after the due date")
    from aixl.core.comparator import compare_graphs
    r = compare_graphs(ga, gb, ON)
    assert r.verdict == "NOT_EQUIVALENT" and any(d.field == "MARKERS" for d in r.differences)


def test_incomplete_side_forces_inconclusive_only_when_flag_on():
    from aixl.core.comparator import compare_graphs
    mk = lambda: annotate(from_aixl("V:AIXL-0.3 I:REQUEST_EXECUTION A:SEND D:REPORT"), "Send the report to the CFO")
    assert compare_graphs(mk(), mk(), ON).verdict == "INCONCLUSIVE"
    assert compare_graphs(mk(), mk()).verdict == "EQUIVALENT"          # default unchanged


def test_complete_and_equal_stays_equivalent():
    from aixl.core.comparator import compare_graphs
    mk = lambda t: annotate(from_aixl('V:AIXL-0.3 I:REQUEST_EXECUTION A:SEND D:REPORT R:"CFO"'), t)
    assert compare_graphs(mk("Send the report to the CFO"), mk("Send the report to the CFO"), ON).verdict == "EQUIVALENT"


def test_negated_comparators_are_the_opposite_comparator():
    """Found by blind_markers (P022): 'no fewer than 3' was read as LESS+NEG, so it separated from 'at least 3'."""
    assert extract_markers("Remove no fewer than three drafts") == {"MORE_EQ"} == extract_markers("Delete at least three drafts")
    assert extract_markers("Delete no more than 3 records") == {"LESS_EQ"}
    assert extract_markers("Borra no menos de tres") == {"MORE_EQ"} and extract_markers("Apague nao mais de tres") == {"LESS_EQ"}
    assert extract_markers("Delete fewer than three") == {"LESS"}                      # un-negated unchanged
    assert extract_markers("Don't delete anything") == {"NEG"}                         # plain negation unchanged


def test_negated_comparator_pair_is_not_separated_but_real_opposites_are():
    from aixl.api.service import compare
    assert compare("Delete at least three old drafts from the shared folder.", "Remove no fewer than three old drafts from the shared folder.").verdict != "NOT_EQUIVALENT"
    assert compare("Delete at least three drafts.", "Delete no more than three drafts.").verdict != "EQUIVALENT"


def test_closed_lexicon_synonyms_and_every_all():
    assert extract_markers("Archive every email apart from the finance ones") >= {"EXCEPT"}
    assert extract_markers("Send it ahead of Friday") == {"BEFORE"}
    assert extract_markers("Approve requests exceeding 500 dollars") == {"MORE"}
    opposed, other = marker_conflicts(extract_markers("Archive all emails except finance"), extract_markers("Archive every email apart from finance"))
    assert not opposed and not other                                                    # same exception, different words
    assert marker_conflicts({"EVERY"}, set())[1] == ["EVERY"]                          # 'every Monday' vs 'next Monday' still not proven equal


def test_inclusive_vs_strict_bound_and_name_order():
    from aixl.api.service import compare
    from aixl.core.completeness import names_reordered
    assert compare("Reserva una sala para al menos diez personas.", "Reserva una sala para más de diez personas.").verdict != "EQUIVALENT"
    assert compare("Book a room for at least ten people.", "Book a room that fits ten people or more.").verdict != "NOT_EQUIVALENT"
    assert names_reordered("Ask Luis to send the budget to Sara.", "Ask Sara to send the budget to Luis.")
    assert not names_reordered("Send it to Ana and Luis.", "Send it to Ana and also Luis.")
    assert not names_reordered("Send the report on Friday to Ana.", "Send the report on Monday to Ana.")           # days are not names
    assert compare("Pide a Luis que envíe el presupuesto a Sara.", "Pide a Sara que envíe el presupuesto a Luis.").verdict != "EQUIVALENT"


def test_until_is_not_before():
    """blind_markers3 T013/U012: 'until' was BEFORE, so 'don't X until Y' was definitively NOT_EQUIVALENT to 'X only after Y'."""
    from aixl.api.service import compare
    assert extract_markers("Don't publish the draft until Imani has reviewed it.") >= {"UNTIL"} and "BEFORE" not in extract_markers("Wait until Wei approves")
    assert compare("Don't publish the draft until Imani has reviewed it.", "Publish the draft only after Imani has reviewed it.").verdict != "NOT_EQUIVALENT"
    assert compare("Delete the draft only after Wei has approved the final version.", "Wait until Wei has approved the final version, then delete the draft.").verdict != "NOT_EQUIVALENT"
    assert compare("Send the report before Friday.", "Send the report after Friday.").verdict == "NOT_EQUIVALENT"      # real opposites still separate


def test_negated_temporal_order_is_the_opposite_order():
    from aixl.api.service import compare
    assert extract_markers("Update the page, but not before the audit is finished") == {"AFTER"}
    assert extract_markers("Envíalo, pero no después del lunes") == {"BEFORE"}
    assert compare("Wait until after the audit to update the pricing page.", "Update the pricing page, but not before the audit is finished.").verdict != "NOT_EQUIVALENT"
    assert compare("Send it before Friday.", "Send it after Friday.").verdict == "NOT_EQUIVALENT"
