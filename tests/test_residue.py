"""ADR-016 step 2: R: residue atom (details no slot can express are kept, never dropped)."""
from aixl import compare_aixl, from_aixl
from aixl.serialization import aixl_codec
from aixl.core.ontology import load_config
from aixl.core.lexicon_gaps import unaccounted_content, residue_key

ON = {**load_config(), "inconclusive": True}
BASE = "V:AIXL-0.3 I:REQUEST_EXECUTION A:SEND D:REPORT"


def test_residue_roundtrips_through_the_codec():
    g = from_aixl(BASE + ' R:"every week","to the CFO"')
    assert [n.value for n in g.by_type("RESIDUE")] == ["every week", "to the CFO"]
    assert aixl_codec.encode(g).endswith('R:"every week","to the CFO"')


def test_old_messages_without_residue_are_unchanged():
    assert compare_aixl(BASE, BASE).equivalent


def test_residue_on_one_side_only_is_a_difference():
    r = compare_aixl(BASE, BASE + ' R:"by Monday"')
    assert not r.equivalent and r.differences[0].kind == "added"


def test_same_residue_in_different_order_or_wording_frame_is_equivalent():
    assert compare_aixl(BASE + ' R:"to the CFO","every week"', BASE + ' R:"every week","to the CFO"').equivalent


def test_different_residue_both_sides_is_not_equivalent_and_inconclusive_when_enabled():
    a, b = BASE + ' R:"to the CFO"', BASE + ' R:"to the CEO"'
    assert not compare_aixl(a, b).equivalent
    assert compare_aixl(a, b, ON).verdict == "INCONCLUSIVE"


def test_residue_words_count_as_accounted_for_the_lint():
    text = "Send the report every week to the CFO"
    bare = from_aixl(BASE)
    assert "cfo" in unaccounted_content(text, bare)
    assert "cfo" not in unaccounted_content(text, from_aixl(BASE + ' R:"every week","to the CFO"'))


def test_residue_key_is_order_free_and_drops_function_words():
    assert residue_key(["by the CFO", "weekly"]) == residue_key(["weekly", "CFO"])
