"""Phase 5: the _known cache must never hide a lexicon change (extensions append to the closed lexicons at runtime)."""
from aixl.core import lexicon_gaps
from aixl.legacy02.translators import natural_to_semantic as legacy


def test_known_sees_an_extension_added_after_first_use_and_forgets_it_when_removed(monkeypatch):
    w = "zzqxinvoice"
    assert lexicon_gaps._known(w) is False            # cached as False under the current lexicon version
    monkeypatch.setattr(legacy, "ENTITY_RX", legacy.ENTITY_RX + [("ZQXINVOICE", r"^zzqxinvoice$")])
    assert lexicon_gaps._known(w) is True             # an extension appended an entity: the cache must not answer False
    monkeypatch.undo()
    assert lexicon_gaps._known(w) is False            # extension gone: back to the original answer


def test_known_is_stable_for_unchanged_lexicons():
    assert lexicon_gaps._known("documento") is True and lexicon_gaps._known("documento") is True
    assert lexicon_gaps._known_at.cache_info().hits >= 1
