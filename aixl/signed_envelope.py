"""Authenticated semantic envelope: WHO sealed it, WHAT it means, and that neither changed — in one object.

`aixl.envelope.seal` binds a text to its semantic fingerprint but is NOT signed (SECURITY.md): anybody can forge a matching pair. Here the sealed envelope is signed with Ed25519 (the `cryptography` library, standard primitives only — no home-made
protocol, no home-made crypto). Verification answers two SEPARATE questions and never mixes them:
  1. is the object authentic (signature valid, algorithm allowed, key known, fresh, not replayed)?   -> BAD_SIGNATURE / BAD_ALGORITHM / UNKNOWN_KEY / STALE / REPLAY / MALFORMED
  2. does the text I actually hold match what was sealed?                                             -> AUTHENTIC_MATCH / AUTHENTIC_MISMATCH / AUTHENTIC_UNVERIFIED (the envelope's own three outcomes)
`AUTHENTIC_MISMATCH` means "the sender really sealed X, and what I hold is not X": drift or tampering AFTER sealing, with proof of who said X.
Signed bytes: the canonical JSON (sorted keys, no whitespace, UTF-8) of {v, envelope, alg, kid, ts, nonce}. Compatible with RFC 8785 for the value types used here (strings, integers, booleans, null, arrays, objects; no floats).
Limits, said plainly: NO key distribution, revocation or rotation (the caller supplies the trusted public key); replay and freshness are checked only when the caller passes `max_age_s` / `seen_nonces`; the clock is the caller's; Ed25519 is not
post-quantum (a hybrid ML-DSA signature is a design note, waiting for the project's own PQC code to be independently reviewed); this module has had no external security review. Requires the optional dependency `cryptography`."""
import base64
import hashlib
import json
import os
import time

from aixl.envelope import seal, verify

VERSION = "AIXL-SIG-1"
ALG = "EdDSA"
MAX_BYTES = 1_000_000


def _crypto():
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    except ImportError as e:                                                 # pragma: no cover
        raise ImportError("aixl.signed_envelope needs the optional dependency: pip install cryptography") from e
    return InvalidSignature, serialization, Ed25519PrivateKey, Ed25519PublicKey


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _unb64(s: str) -> bytes:
    if not isinstance(s, str) or not s.isascii():
        raise ValueError("not base64url")
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def generate_keypair():
    """(private_key, public_key) objects of the `cryptography` library."""
    _ic, _ser, priv_cls, _pub = _crypto()
    priv = priv_cls.generate()
    return priv, priv.public_key()


def public_key_from_bytes(raw: bytes):
    _ic, _ser, _priv, pub_cls = _crypto()
    return pub_cls.from_public_bytes(raw)


def public_bytes(public_key) -> bytes:
    _ic, ser, _priv, _pub = _crypto()
    return public_key.public_bytes(ser.Encoding.Raw, ser.PublicFormat.Raw)


def key_id(public_key) -> str:
    return _b64(hashlib.sha256(public_bytes(public_key)).digest())[:22]


def sign_envelope(text: str, private_key, *, now: int | None = None, nonce: str | None = None) -> dict:
    """Seal `text` (aixl.envelope.seal) and sign the result. Returns a JSON-serialisable dict."""
    env = seal(text)
    pub = private_key.public_key()
    body = {"v": VERSION, "envelope": env, "alg": ALG, "kid": key_id(pub), "ts": int(time.time() if now is None else now), "nonce": nonce or _b64(os.urandom(16))}
    sig = private_key.sign(_canonical(body))
    return {"v": VERSION, "envelope": env, "sig": {"alg": ALG, "kid": body["kid"], "ts": body["ts"], "nonce": body["nonce"], "value": _b64(sig)}}


def verify_signed(signed, public_key, received_text, *, max_age_s: int | None = None, now: int | None = None, seen_nonces: set | None = None) -> dict:
    """Never raises. Returns {"state", "kid", "envelope_state"}: see the module docstring for the states. `seen_nonces` (a mutable set) turns on replay detection and is updated on success."""
    out = {"state": "MALFORMED", "kid": None, "envelope_state": None}
    try:
        invalid_sig, _ser, _priv, _pub = _crypto()
        if not isinstance(signed, dict) or signed.get("v") != VERSION or not isinstance(signed.get("envelope"), dict) or not isinstance(signed.get("sig"), dict) or not isinstance(received_text, str):
            return out
        sig = signed["sig"]
        if not all(isinstance(sig.get(k), str) for k in ("alg", "kid", "nonce", "value")) or not isinstance(sig.get("ts"), int) or isinstance(sig.get("ts"), bool):
            return out
        out["kid"] = sig["kid"]
        if sig["alg"] != ALG:
            out["state"] = "BAD_ALGORITHM"                                      # `none`, HS256, anything else: never accepted
            return out
        if sig["kid"] != key_id(public_key):
            out["state"] = "UNKNOWN_KEY"
            return out
        body = {"v": VERSION, "envelope": signed["envelope"], "alg": sig["alg"], "kid": sig["kid"], "ts": sig["ts"], "nonce": sig["nonce"]}
        payload = _canonical(body)
        if len(payload) > MAX_BYTES:
            return out
        try:
            public_key.verify(_unb64(sig["value"]), payload)
        except (invalid_sig, ValueError):
            out["state"] = "BAD_SIGNATURE"
            return out
        if max_age_s is not None and abs((time.time() if now is None else now) - sig["ts"]) > max_age_s:
            out["state"] = "STALE"
            return out
        if seen_nonces is not None:
            if sig["nonce"] in seen_nonces:
                out["state"] = "REPLAY"
                return out
            seen_nonces.add(sig["nonce"])
        out["envelope_state"] = verify(signed["envelope"], received_text)         # MATCH / MISMATCH / UNVERIFIED
        out["state"] = "AUTHENTIC_" + out["envelope_state"]
        return out
    except ImportError:
        raise
    except Exception:                                                            # noqa: BLE001 — fail closed: an object we cannot read is never authentic
        return {"state": "MALFORMED", "kid": out.get("kid"), "envelope_state": None}
