"""Arena regressions: defects the arena found (fixed) + arena self-test so a blind oracle can't pass silently."""
import subprocess, sys
from aixl.gate import translate_gated
from aixl.translators.natural_to_semantic import to_graph
from aixl.serialization.aixl_codec import encode


def test_multi_space_does_not_drop_temporal_term():       # arena finding 2026-10-10 (COSM via `space`)
    a = encode(to_graph("Analiza los videos de esta semana."))
    assert encode(to_graph("Analiza los videos de   esta   semana.")) == a
    assert "T:THIS_WEEK" in a
    g = translate_gated("  Analiza   los videos de   esta   semana. ")
    assert g["mode"] != "AIXL" or "T:THIS_WEEK" in g["output"]


def test_lowercase_recipient_is_contained_by_gate():      # known translator miss, must stay contained
    assert translate_gated("Envía el informe a ana.")["mode"] == "NATURAL"


def test_arena_selftest_catches_all_planted_bugs():
    r = subprocess.run([sys.executable, "-m", "lab.arena.arena", "selftest"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_paraphrase_pairs_rules_route_never_false_same():
    from lab.arena.paraphrase import run
    cm, bad, rows = run()
    assert len(rows) == 48 and not bad          # 24 SAME + 24 DIFFERENT written before running; fail-closed is allowed, false-same is not


def test_paraphrase_hybrid_with_stored_blind_judges_never_false_same():
    """Judges were two blind subagents (haiku, sonnet) under rules_v1, ids shuffled (data/arena/judges). Replayed, not re-judged."""
    import json, pathlib
    from aixl.semantic.hybrid import decide
    root = pathlib.Path(__file__).resolve().parents[1] / "data" / "arena"
    rows = [json.loads(l) for l in open(root / "paraphrase_pairs.jsonl", encoding="utf-8")]
    inv = {v: k for k, v in json.load(open(root / "judges" / "idmap.json")).items()}
    J = {n: dict(l.split("\t") for l in open(root / "judges" / f"{n}.tsv").read().splitlines()) for n in ("haiku", "sonnet")}
    for i, r in enumerate(rows):
        d = decide(r["a"], r["b"], {n: (lambda a, b, n=n, k=inv[i]: J[n][k]) for n in J})
        if r["expected"] == "DIFFERENT":
            assert d.verdict != "SAME", r
