"""AIXL v1.0 prompt audit (docs/V1_PROMPT_AUDIT.md): one test per prompt section that has a testable claim."""
from aixl.core.fingerprint import fingerprint_graph as fp
from aixl.gate import compact, count_tokens, expand, translate_gated
from aixl.serialization.aixl_codec import decode, encode
from aixl.translators.natural_to_semantic import to_graph


def test_s1_no_saving_means_natural():  # §1
    r = translate_gated("Traduce este documento al inglés.")
    assert r["mode"] == "NATURAL" and r["output"] == "Traduce este documento al inglés."


def test_s1_saving_uses_aixl_and_is_shorter():  # §1/§23
    r = translate_gated("Compara el documento 1 con el documento 2.")
    assert r["mode"] == "AIXL" and r["tokens_aixl"] < r["tokens_natural"]


def test_s5_compact_roundtrip_preserves_fingerprint():  # §5/§13
    for t in ["Compara el documento 1 con el documento 2.", "Translate this document into English."]:
        g = to_graph(t)
        assert fp(decode(expand(compact(encode(g))))) == fp(g)


def test_s12_negation_never_dropped():  # §12
    r = translate_gated("No elimines los datos originales.")
    assert r["mode"] == "NATURAL" or "NO_DELETE" in r["aixl"] or "FORBID" in r["aixl"]


def test_s16_silent_loss_blocked():  # §16 fidelity > compression ("solamente la información más importante" is not encoded)
    r = translate_gated("Resume este documento en cinco puntos y conserva solamente la información más importante.")
    assert r["mode"] == "NATURAL" and r["reason"] == "incomplete_encoding"


def test_s14_no_overencoding_of_non_requests():  # §14
    assert translate_gated("Hola")["mode"] == "NATURAL"


def test_s17_multilingual_same_graph():  # §17
    a, b, c = (fp(to_graph(x)) for x in ["Traduce este documento al inglés.", "Translate this document into English.", "Traduza este documento para inglês."])
    assert a == b == c


def test_token_proxy_monotonic():
    assert count_tokens("a b c") < count_tokens("a b c d e f")


def test_short_message_dropped_context_blocked():  # real-traffic defect (V1_PROMPT_AUDIT.md): 'creo que' was silently dropped
    for t in ["creo que ya revisa", "listo revisa", "ya me logee por favor correlo tu"]:
        assert translate_gated(t)["mode"] == "NATURAL", t


def test_known_but_unencoded_object_blocked():  # 'redacta el correo' -> A:GENERATE dropped the object
    assert translate_gated("redacta el correo")["mode"] == "NATURAL"


def test_affirmation_not_dropped():  # 'si muestrame' ('yes, show me') -> A:GET lost the 'yes'
    for t in ["si muestrame", "yes show me", "ok revisa"]:
        assert translate_gated(t)["mode"] == "NATURAL", t
