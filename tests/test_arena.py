"""Arena regressions: defects the arena found (fixed) + arena self-test so a blind oracle can't pass silently."""
import subprocess
import sys

import pytest

from aixl.gate import translate_gated
from aixl.serialization.aixl_codec import encode
from aixl.translators.natural_to_semantic import to_graph


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
    import json
    import pathlib

    from aixl.semantic.hybrid import decide
    root = pathlib.Path(__file__).resolve().parents[1] / "data" / "arena"
    rows = [json.loads(l) for l in open(root / "paraphrase_pairs.jsonl", encoding="utf-8")]
    inv = {v: k for k, v in json.load(open(root / "judges" / "idmap.json")).items()}
    J = {n: dict(l.split("\t") for l in open(root / "judges" / f"{n}.tsv").read().splitlines()) for n in ("haiku", "sonnet")}
    for i, r in enumerate(rows):
        d = decide(r["a"], r["b"], {n: (lambda a, b, n=n, k=inv[i]: J[n][k]) for n in J})
        if r["expected"] == "DIFFERENT":
            assert d.verdict != "SAME", r


def test_natural_passthrough_is_byte_identical():          # regression of the multi-space fix: it must not rewrite the caller's text
    for t in ["Revisa este bloque:\n    def f(x):\n        return x  # dos niveles\n", "col1\tcol2\tcol3", "Hola   ", "   Analiza las ventas."]:
        g = translate_gated(t)
        assert g["mode"] == "NATURAL" and g["output"] == t, (t, g["output"])


def test_multi_space_text_is_still_analysed_normalised():   # ...while the ANALYSIS copy keeps the arena fix
    a = translate_gated("Compara el documento 1 con el documento 2.")
    b = translate_gated("Compara   el documento 1   con el documento 2.")
    assert (a["mode"], a["fingerprint"]) == (b["mode"], b["fingerprint"])


def test_replay_does_not_call_a_contained_failure_fixed():
    from lab.arena.arena import replay
    st = {sig.split("|")[2]: status for sig, code, status in replay()}
    assert st["paramariaparamaria"] == "CONTAINED"           # translator still loses the capital, gate falls back to NATURAL
    assert st["estasemanaestasemana"] == "FIXED"             # the multi-space defect really is fixed


def test_gate_seeds_really_take_the_aixl_path():           # if they stop doing so the META-GATE-* oracles silently go back to being vacuous
    from lab.arena.arena import GATE_SEEDS
    assert GATE_SEEDS and all(translate_gated(s)["mode"] == "AIXL" for s in GATE_SEEDS)


def test_selftest_plants_a_bug_for_every_oracle_family():
    from lab.arena.arena import selftest
    r = selftest()
    names = " | ".join(n for n, _ in r)
    assert all(ok for _, ok in r) and len(r) >= 5
    for word in ("comparator", "decoder", "number", "envelope", "same AIXL"):
        assert word in names, word


@pytest.fixture(scope="module")
def scope_counts():
    from lab.arena.arena import scope
    return scope(reps=1)["counts"]                                # the full 5-rep sweep (1,676 mutants) is `python -m lab.arena.arena scope`


@pytest.mark.slow                                          # ~15 s: the experimental comparator costs ~50 ms per mutant; CI runs it, `-m "not slow"` skips it
def test_scope_shipped_layers_have_no_defects_and_the_aixl_path_is_exercised(scope_counts):
    k = scope_counts
    assert k["mutants"] > 100
    assert k.get("semantic_equivalent", 0) == 0 and k.get("envelope_MATCH", 0) == 0 and k.get("gate_collapse", 0) == 0
    assert k.get("verified_compare_equivalent", 0) == 0
    assert k.get("gate_AIXL", 0) > 0                          # not vacuous: some mutants did reach the AIXL branch


@pytest.mark.slow
def test_new_attack_families_exist_and_scope_reports_what_was_decided(scope_counts):
    from lab.arena.arena import NL_ATTACKERS
    names = {n for n, _, _ in NL_ATTACKERS}
    assert {"conj_swap", "quant_flip", "cond_flip", "cond_drop", "modal_flip", "neg_scope", "order_swap"} <= names
    k = scope_counts
    assert 0 < k["decided"] < k["mutants"]                    # some real decisions, and the abstentions are counted instead of hidden
    assert any(key.startswith("family_decided:") for key in k)


def test_pt_article_o_is_not_attacked_as_a_disjunction():
    import random

    from lab.arena.arena import a_conj_swap
    assert a_conj_swap("Resuma o relatório em cinco pontos.", random.Random(1)) is None
    assert a_conj_swap("Envía el informe a Ana y a Luis.", random.Random(1)) == "Envía el informe a Ana o a Luis."
