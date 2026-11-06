"""Atheris (libFuzzer) harness for ClusterFuzzLite: coverage-guided fuzzing of the semantic comparator.

Same invariants as tests/test_fuzz_properties.py, checked on every input: no crash, a text is never different from itself, strict mode only proves
the same token sequence, and the verdict does not depend on the order of the texts. Run locally (needs `pip install atheris`, Linux/macOS with clang):
    python fuzz/fuzz_semantic.py -max_total_time=60
"""
import sys

import atheris

with atheris.instrument_imports():
    from aixl.semantic import compare_texts, parse

VERDICTS = {"EQUIVALENT", "NOT_EQUIVALENT", "INCONCLUSIVE"}


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    a = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 300))
    b = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 300))
    loose, strict = compare_texts(a, b), compare_texts(a, b, strict=True)
    assert loose.verdict in VERDICTS
    if strict.verdict == "EQUIVALENT":
        assert parse(a).norm == parse(b).norm
    if loose.verdict != "EQUIVALENT":
        assert strict.verdict == loose.verdict
    same = compare_texts(a, a)
    assert same.verdict != "NOT_EQUIVALENT"
    assert compare_texts(b, a).verdict == loose.verdict, "verdict depends on the order of the texts"


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
