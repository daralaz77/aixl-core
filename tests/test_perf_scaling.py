"""Scaling guards (consejo-5x audit): the graph build and the numeric-run regex used to be O(n^2). Ratios, not wall-clock thresholds, so they are stable."""
import random
import re
import time

from aixl.core.semantic_graph import SemanticGraph


def test_add_node_ids_are_unchanged_and_not_quadratic():
    g = SemanticGraph()
    ids = [g.add_node("TIME" if i % 3 else "ENTITY", f"v{i}").id for i in range(9)]
    assert ids == ["entity_1", "time_1", "time_2", "entity_2", "time_3", "time_4", "entity_3", "time_5", "time_6"]
    g.nodes.append(g.nodes[0])                                   # touched outside add_node: the counter must resynchronise
    assert g.add_node("ENTITY", "x").id == "entity_5"
    t0 = time.perf_counter()
    h = SemanticGraph()
    for _ in range(20000):
        h.add_node("TIME", "x")
    assert time.perf_counter() - t0 < 2.0                        # 20k nodes: ~0.03 s now, ~13 s with the old scan


def test_numeric_run_regex_is_equivalent_for_realistic_numbers_and_linear():
    nouns = r"(?:clientes|registros|ventas|usuarios)"
    old = re.compile(rf"\b(\d[\d.,]*\d|\d)\s+(?:de\s+)?(?={nouns}\b)")
    new = re.compile(rf"\b(\d[\d.,]{{0,40}}\d|\d)\s+(?:de\s+)?(?={nouns}\b)")
    rnd = random.Random(3)
    alphabet = ["1", "2", "5", "0", ",", ".", " ", "de ", "clientes", "registros", "x", "a1", "v", "-"]
    for _ in range(4000):
        s = "".join(rnd.choice(alphabet) for _ in range(rnd.randint(1, 25)))
        assert [m.span() for m in old.finditer(s)] == [m.span() for m in new.finditer(s)], s
    t0 = time.perf_counter()
    list(new.finditer("1,2,3," * 20000))                          # 120 KB of digits and commas: > 8 s with the old pattern
    assert time.perf_counter() - t0 < 1.0


def test_repeated_dates_and_words_give_the_same_result_as_one_occurrence_and_scale_roughly_linearly():
    from aixl.core.lexicon_gaps import unaccounted_content
    from aixl.translators.natural_to_semantic import to_graph
    one = "Analiza las ventas antes de Q1 2026 y despues de marzo de 2025. "
    g1 = to_graph(one)
    assert sorted(unaccounted_content(one, g1)) == sorted(unaccounted_content(one * 3, to_graph(one * 3)))
    t0 = time.perf_counter(); to_graph(one * 40); small = time.perf_counter() - t0
    t0 = time.perf_counter(); to_graph(one * 160); big = time.perf_counter() - t0
    assert big < small * 12 + 0.05                       # 4x the input: <= ~12x (quadratic would be ~16x; linear ~4x). Loose on purpose: stable on busy CI


def test_repeated_sentences_scale_roughly_linearly(monkeypatch):            # was x3.4 per doubling (quadratic): the working string was re-joined on every access
    from aixl.translators.natural_to_semantic import to_graph
    monkeypatch.setenv("AIXL_MAX_INPUT_CHARS", "1000000")        # 1,600 sentences = 49 KB, above the default analysis limit
    unit = "Analiza las ventas de Q1 2026. "
    to_graph(unit * 50)                                          # warm-up (regex compilation)
    t0 = time.perf_counter(); to_graph(unit * 400); small = time.perf_counter() - t0
    t0 = time.perf_counter(); to_graph(unit * 1600); big = time.perf_counter() - t0
    assert big < small * 9 + 0.05                                # 4x input: linear ~4x, quadratic ~16x
