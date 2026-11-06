"""Atheris (libFuzzer) harness for ClusterFuzzLite: the translator, fingerprint, verified comparison and relay check must never crash or hang on any text."""
import sys

import atheris

with atheris.instrument_imports():
    import aixl


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    a = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 400))
    b = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 400))
    aixl.to_semantic(a)
    assert isinstance(aixl.semantic_fingerprint(a), str)
    assert aixl.compare_verified(a, b)["verdict"] in {"EQUIVALENT", "NOT_EQUIVALENT", "INCONCLUSIVE"}
    assert "ok" in aixl.relay_check(a, b)


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
