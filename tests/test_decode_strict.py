"""Evolution Engine §7: no silent guess / silent drop at decode. Failing-before cases written first (orphan negation fingerprint-equal to no negation)."""
import pytest

from aixl.serialization.aixl_codec import AixlError, decode

BASE = "V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE D:SALES"


@pytest.mark.parametrize("extra", [" N:NO_DELETE", " K:FORBID_DELETE", " N:NO_SEND K:FORBID_SEND"])
def test_orphan_prohibition_raises(extra):
    with pytest.raises(AixlError) as e:
        decode(BASE + extra)
    assert e.value.code == "ORPHAN_NEGATION"


def test_backed_prohibition_still_decodes():
    f = decode("V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE,DELETE D:SALES,DATA N:NO_DELETE K:FORBID_DELETE").to_frame()
    assert "NO_DELETE" in f.negations


def test_unknown_value_default_tolerant_strict_rejects():
    line = "V:AIXL-0.3 I:REQUEST_ANALYSIS A:FOOBAR D:SALES"
    decode(line)                                   # bug032 behaviour kept
    with pytest.raises(AixlError) as e:
        decode(line, strict=True)
    assert e.value.code == "UNKNOWN_ATOM_VALUE"
