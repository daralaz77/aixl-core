"""Phase 0 safety net (docs/CLEANUP_ROADMAP.md): the observable pipeline output must not change during refactors.
If a change is INTENDED, regenerate with `python -m benchmarks.characterization --write` and review the diff in the commit."""
import json

from benchmarks.characterization import GOLDEN, snapshot


def test_pipeline_output_is_unchanged():
    want = json.loads(GOLDEN.read_text())
    got = json.loads(json.dumps(snapshot(), ensure_ascii=False))
    assert set(got) == set(want), f"corpus changed: +{sorted(set(got) - set(want))[:3]} -{sorted(set(want) - set(got))[:3]}"
    bad = [(t, k) for t in want for k in want[t] if got[t][k] != want[t][k]]
    assert not bad, f"{len(bad)} field(s) changed, first: {bad[:3]}"
