"""Targeted fix for the dominant failure mode measured in the first fine-tune (2026-10-01): F1 0.6056
with precision 0.9556 but recall only 0.4433 (fp=2, fn=54) -- the model rarely claims two DIFFERENT
texts are equivalent when they aren't (that part already works), but it very often encodes two
genuinely-equivalent paraphrases DIFFERENTLY, so they fail to compare as equivalent. That is a
consistency problem, not a vocabulary problem: independently-generated teacher answers for text A and
text B of the same EQUIVALENT pair can legitimately differ in harmless ways (field order, a synonym
action), and the small student model learned that variance as if it were signal.

Fix: for every real EQUIVALENT pair already labeled by a human author across this project's blind
corpora (blind3, blind4, blind6-9 -- NOT blind5, which stays held out), force BOTH sides' training
target to the exact same AIXL line, instead of each side's own independently-generated teacher answer.
This costs no new API calls (reuses distill/corpus.jsonl's existing teacher answers) and directly
teaches the invariance the model is currently missing. Consistency pairs are also oversampled (written
3x) so they carry real weight against the base corpus during fine-tuning.

usage: python distill/build_consistency_corpus.py
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from aixl.serialization import aixl_codec

PAIR_SOURCES = [
    "data/blind3/pairs_A3.jsonl", "data/blind3/pairs_B3.jsonl",
    "data/blind4/pairs_A4.jsonl", "data/blind4/pairs_B4.jsonl",
    "data/blind6/pairs_S6.jsonl", "data/blind7/pairs_S7.jsonl",
    "data/blind8/pairs_S8.jsonl", "data/blind9/pairs_S9.jsonl",
]


def load_base_corpus():
    pairs = {}
    with open(os.path.join(ROOT, "distill", "corpus.jsonl"), encoding="utf-8") as f:
        for l in f:
            if l.strip():
                d = json.loads(l)
                pairs[d["text"]] = d["aixl"]
    return pairs


def main():
    corpus = load_base_corpus()
    base_n = len(corpus)

    equivalent_pairs = []
    for src in PAIR_SOURCES:
        path = os.path.join(ROOT, src)
        if not os.path.exists(path):
            continue
        for l in open(path, encoding="utf-8"):
            if not l.strip():
                continue
            r = json.loads(l)
            if r.get("label") == "EQUIVALENT":
                equivalent_pairs.append((r["a"], r["b"]))

    forced, already_consistent, unresolved = 0, 0, 0
    consistency_examples = []  # (text, aixl) entries to oversample
    for text_a, text_b in equivalent_pairs:
        target_a, target_b = corpus.get(text_a), corpus.get(text_b)
        if target_a is None and target_b is None:
            unresolved += 1
            continue
        canonical = target_a or target_b
        # sanity: only force a target that actually decodes -- never invent one
        try:
            aixl_codec.decode(canonical)
        except aixl_codec.AixlError:
            unresolved += 1
            continue
        if target_a == target_b:
            already_consistent += 1
        else:
            forced += 1
        corpus[text_a] = canonical
        corpus[text_b] = canonical
        consistency_examples.append((text_a, canonical))
        consistency_examples.append((text_b, canonical))

    out_path = os.path.join(ROOT, "distill", "corpus_consistent.jsonl")
    with open(out_path, "w", encoding="utf-8") as out:
        for text, aixl in corpus.items():
            out.write(json.dumps({"text": text, "aixl": aixl}, ensure_ascii=False) + "\n")
        # oversample the consistency-corrected pairs 2 extra times (3x total) so fine-tuning
        # weighs the lesson "these must match" against the much larger base corpus
        for _ in range(2):
            for text, aixl in consistency_examples:
                out.write(json.dumps({"text": text, "aixl": aixl}, ensure_ascii=False) + "\n")

    total_lines = len(corpus) + 2 * len(consistency_examples)
    print(f"base corpus: {base_n} unique (text, aixl) pairs")
    print(f"corpus after merging new texts from pairs: {len(corpus)} unique (text, aixl) pairs")
    print(f"EQUIVALENT pairs found (blind3/4/6-9, blind5 excluded): {len(equivalent_pairs)}")
    print(f"  already consistent (both sides already matched): {already_consistent}")
    print(f"  forced to match (diverged before, now corrected): {forced}")
    print(f"  unresolved (neither side in base corpus, or target invalid): {unresolved}")
    print(f"total training lines written (base + 2x oversampled consistency pairs): {total_lines}")


if __name__ == "__main__":
    main()
