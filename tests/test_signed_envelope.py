"""aixl.signed_envelope: authenticity and content are separate questions; everything unreadable is MALFORMED, never an exception."""
import copy
import json

import pytest

pytest.importorskip("cryptography")
from aixl.signed_envelope import generate_keypair, key_id, public_bytes, public_key_from_bytes, sign_envelope, verify_signed  # noqa: E402

TEXT = "Analiza las ventas del primer trimestre de 2026."


@pytest.fixture(scope="module")
def keys():
    return generate_keypair()


def test_roundtrip_is_authentic_and_matches(keys):
    priv, pub = keys
    r = verify_signed(sign_envelope(TEXT, priv), pub, TEXT)
    assert r["state"] == "AUTHENTIC_MATCH" and r["envelope_state"] == "MATCH" and r["kid"] == key_id(pub)


def test_authentic_but_the_text_I_hold_differs(keys):
    """the sender really sealed X; what I hold is not X: drift AFTER sealing, with proof of who said X."""
    priv, pub = keys
    r = verify_signed(sign_envelope("Elimina el reporte.", priv), pub, "No elimines el reporte.")
    assert r["state"] == "AUTHENTIC_MISMATCH"


def test_authentic_but_unverifiable_content(keys):
    priv, pub = keys
    text = "Please reconcile the quarterly ledger with zorblax protocols."
    assert verify_signed(sign_envelope(text, priv), pub, text)["state"] in ("AUTHENTIC_UNVERIFIED", "AUTHENTIC_MATCH")


@pytest.mark.parametrize("field", ["text", "fp", "v"])
def test_tampering_with_the_sealed_envelope_breaks_the_signature(keys, field):
    priv, pub = keys
    s = sign_envelope(TEXT, priv)
    s["envelope"][field] = "x" + str(s["envelope"].get(field) or "")
    assert verify_signed(s, pub, TEXT)["state"] == "BAD_SIGNATURE"


def test_tampering_with_the_signature_metadata(keys):
    priv, pub = keys
    for field, val in (("ts", 1), ("nonce", "AAAA")):
        s = sign_envelope(TEXT, priv)
        s["sig"][field] = val
        assert verify_signed(s, pub, TEXT)["state"] == "BAD_SIGNATURE"


def test_signature_of_another_message_does_not_transfer(keys):
    priv, pub = keys
    a, b = sign_envelope(TEXT, priv), sign_envelope("Elimina el reporte.", priv)
    a["sig"]["value"] = b["sig"]["value"]
    assert verify_signed(a, pub, TEXT)["state"] == "BAD_SIGNATURE"


def test_another_key_is_unknown_and_a_forged_kid_still_fails(keys):
    priv, pub = keys
    _p2, pub2 = generate_keypair()
    s = sign_envelope(TEXT, priv)
    assert verify_signed(s, pub2, TEXT)["state"] == "UNKNOWN_KEY"
    forged = copy.deepcopy(s)
    forged["sig"]["kid"] = key_id(pub2)
    assert verify_signed(forged, pub2, TEXT)["state"] == "BAD_SIGNATURE"


@pytest.mark.parametrize("alg", ["none", "HS256", "ES256", "eddsa", ""])
def test_only_eddsa_is_accepted(keys, alg):
    priv, pub = keys
    s = sign_envelope(TEXT, priv)
    s["sig"]["alg"] = alg
    assert verify_signed(s, pub, TEXT)["state"] == "BAD_ALGORITHM"


def test_survives_a_json_wire_roundtrip_and_key_reordering(keys):
    priv, pub = keys
    wire = json.loads(json.dumps(sign_envelope("Envía el informe a María antes del viernes. ñandú", priv), ensure_ascii=False))
    reordered = {k: wire[k] for k in reversed(list(wire))}
    reordered["envelope"] = {k: wire["envelope"][k] for k in reversed(list(wire["envelope"]))}
    assert verify_signed(reordered, pub, "Envía el informe a María antes del viernes. ñandú")["state"].startswith("AUTHENTIC_")


def test_ed25519_is_deterministic_so_a_fixed_input_gives_a_fixed_signature(keys):
    priv, _pub = keys
    assert sign_envelope(TEXT, priv, now=1000, nonce="n1") == sign_envelope(TEXT, priv, now=1000, nonce="n1")


def test_stale_and_replay(keys):
    priv, pub = keys
    s = sign_envelope(TEXT, priv, now=1000)
    assert verify_signed(s, pub, TEXT, max_age_s=60, now=1030)["state"] == "AUTHENTIC_MATCH"
    assert verify_signed(s, pub, TEXT, max_age_s=60, now=2000)["state"] == "STALE"
    seen = set()
    assert verify_signed(s, pub, TEXT, seen_nonces=seen)["state"] == "AUTHENTIC_MATCH"
    assert verify_signed(s, pub, TEXT, seen_nonces=seen)["state"] == "REPLAY"


@pytest.mark.parametrize("junk", [None, 5, "x", [], {}, {"v": "AIXL-SIG-1"}, {"v": "AIXL-SIG-1", "envelope": {}, "sig": {}}, {"v": "other", "envelope": {}, "sig": {}},
                                  {"v": "AIXL-SIG-1", "envelope": {}, "sig": {"alg": "EdDSA", "kid": "k", "nonce": "n", "value": "!!", "ts": True}}])
def test_garbage_is_malformed_and_never_raises(keys, junk):
    _priv, pub = keys
    assert verify_signed(junk, pub, TEXT)["state"] in ("MALFORMED", "UNKNOWN_KEY", "BAD_ALGORITHM")


def test_non_string_received_text_and_bad_base64(keys):
    priv, pub = keys
    s = sign_envelope(TEXT, priv)
    assert verify_signed(s, pub, None)["state"] == "MALFORMED"
    s["sig"]["value"] = "***not base64***"
    assert verify_signed(s, pub, TEXT)["state"] == "BAD_SIGNATURE"


def test_public_key_bytes_roundtrip(keys):
    _priv, pub = keys
    assert key_id(public_key_from_bytes(public_bytes(pub))) == key_id(pub)
