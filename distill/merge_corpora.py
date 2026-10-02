"""Merges the recycled, consistency-fixed corpus (corpus_consistent.jsonl, 3017 lines -- proven to help,
F1 0.6056 -> 0.6928) with the genuinely fresh, non-recycled corpus (corpus_fresh.jsonl, built
2026-10-01 after the project's own honest read: a 1.5B model fine-tuned on only recycled data plateaued,
and more epochs on the same ~1400 underlying sentences wasn't going to close the gap to the cloud route).

Simple concatenation with de-dup (a text appearing in both keeps the consistency corpus's label, since
that one already went through the pair-forcing correction) -- no re-weighting here; the oversampling
corpus_consistent.jsonl already did (its 400 EQUIVALENT pairs written 3x) stays as-is in the merged file.

usage: python distill/merge_corpora.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path):
    pairs = []
    with open(path, encoding="utf-8") as f:
        for l in f:
            if l.strip():
                d = json.loads(l)
                pairs.append((d["text"], d["aixl"]))
    return pairs


def main():
    consistent = load(os.path.join(ROOT, "distill", "corpus_consistent.jsonl"))
    fresh = load(os.path.join(ROOT, "distill", "corpus_fresh.jsonl"))

    seen = {text: aixl for text, aixl in consistent}
    added = 0
    for text, aixl in fresh:
        if text not in seen:
            seen[text] = aixl
            added += 1

    out_path = os.path.join(ROOT, "distill", "corpus_merged.jsonl")
    with open(out_path, "w", encoding="utf-8") as out:
        for text, aixl in seen.items():
            out.write(json.dumps({"text": text, "aixl": aixl}, ensure_ascii=False) + "\n")

    print(f"corpus_consistent.jsonl: {len(consistent)} lines")
    print(f"corpus_fresh.jsonl: {len(fresh)} lines ({added} genuinely new texts added)")
    print(f"total merged: {len(seen)} lines -> {out_path}")


if __name__ == "__main__":
    main()
