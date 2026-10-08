"""Phase 0: performance baseline so Phase 5 can only claim gains that are measured.  python -m benchmarks.perf_baseline [--json]"""
import json
import statistics as st
import subprocess
import sys
import time


def _ms_per_text(fn, texts, repeat=5):
    best = []
    for _ in range(repeat):
        t = time.perf_counter()
        for x in texts:
            fn(x)
        best.append((time.perf_counter() - t) / len(texts) * 1000)
    return round(min(best), 3), round(st.median(best), 3)


def main():
    t = time.perf_counter()
    import aixl.translators.natural_to_semantic as n   # noqa: F401  (cold import of the heaviest module)
    import_ms = round((time.perf_counter() - t) * 1000)
    from benchmarks.characterization import corpus, frozen_today
    from aixl.envelope import seal
    from aixl.gate import translate_gated
    from aixl.translators.natural_to_semantic import to_graph
    texts = corpus()
    out = {"corpus_texts": len(texts), "import_translator_ms": import_ms}
    with frozen_today():
        out["to_graph_ms_per_text(min,median)"] = _ms_per_text(to_graph, texts)
        out["translate_gated_ms_per_text(min,median)"] = _ms_per_text(translate_gated, texts)
        out["envelope_seal_ms_per_text(min,median)"] = _ms_per_text(seal, texts)
    if "--no-suite" not in sys.argv:
        t = time.perf_counter()
        r = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "-x", "--deselect", "tests/test_characterization.py"], capture_output=True, text=True)
        out["pytest_suite_s"] = round(time.perf_counter() - t, 1)
        out["pytest_tail"] = r.stdout.strip().splitlines()[-1]
    print(json.dumps(out, indent=1) if "--json" in sys.argv else "\n".join(f"{k:45} {v}" for k, v in out.items()))


if __name__ == "__main__":
    main()
