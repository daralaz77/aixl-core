from aixl.confidence import claim_tier

OK = {"ok": True}
FLAG = {"ok": False}


def test_proof_beats_judges():
    assert claim_tier({"equivalent": True, "verified": True}, OK, [])["tier"] == "P"


def test_no_votes_no_claim():
    t = claim_tier({}, OK, [])
    assert t["tier"] == "none" and t["false_same_measured"] is None


def test_unanimous_same_tiers_follow_relay_check():
    assert claim_tier({}, OK, ["SAME", "SAME"])["tier"] == "J+"
    assert claim_tier({}, FLAG, ["SAME", "same"])["tier"] == "J"


def test_disagreement_is_flagged_as_unsafe():
    t = claim_tier({}, OK, ["SAME", "DIFFERENT"])
    assert t["tier"] == "split" and t["false_same_measured"] > 0.5


def test_all_different():
    assert claim_tier({}, OK, ["DIFFERENT", "DIFF"])["tier"] == "N"
