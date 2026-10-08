"""Ratchet for the §42 5x100 benchmark (rule-based pipeline). Floors = measured values (v1.2 after the PT lexicon + §66 warning fixes) (2026-10-02);
raise them when the system improves, never lower them silently. Known gaps live in BENCHMARK.md §5x100."""
import pytest
from benchmarks import sil5x100_eval as ev, sil5x100_gen as gen

FLOOR = {"EQUIVALENT": 100, "NOT_EQUIVALENT": 97, "PARTIALLY_EQUIVALENT": 100, "AMBIGUOUS": 100, "CONTRADICTORY": 100}   # v1.2: PT lexicons


@pytest.fixture(scope="module")
def rows():
    return ev.run()


def test_dataset_is_reproducible_and_balanced():
    ds = gen.build()
    assert {k: len(v) for k, v in ds.items()} == {k: 100 for k in ev.LABELS}
    for lab in ev.LABELS:                       # committed JSONL == regenerated (seed fixed)
        assert [{k: v for k, v in r.items() if k != "id"} for r in ev.load(lab)] == ds[lab]


@pytest.mark.parametrize("lab", ev.LABELS)
def test_class_floor(rows, lab):
    ok = sum(1 for r in rows if r["label"] == lab and r["pred"] == lab)
    assert ok >= FLOOR[lab], f"{lab}: {ok}/100 < floor {FLOOR[lab]}"


def test_no_ambiguity_false_positives_on_unambiguous_texts():
    assert sum(ev.detect_ambiguity(r["a"]).ambiguous for r in ev.load("EQUIVALENT")) == 0


def test_out_of_lexicon_objects_are_never_silent(rows):
    warned, total = ev.silent_loss(rows)
    assert total > 0 and warned == total


def test_every_miss_is_either_warned_or_known(rows):
    wrong = [r for r in rows if r["pred"] != r["label"]]
    assert all(ev.silent_loss([r])[0] for r in wrong), "a benchmark miss with NO transparency warning appeared"
