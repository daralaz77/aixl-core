"""Builds the MLX LoRA training set (chat format, no system prompt -> ~40% fewer tokens per example) from the
already-validated corpora. Keeps the proven consistency mechanism (EQUIVALENT pairs share ONE target and are
oversampled 3x), normalizes every label through the real codec (encode(decode(x))) so the student learns a
single canonical serialization, and drops anything the codec cannot decode.

usage: python distill/build_mlx_data.py [--out distill/mlx_data] [--valid 150] [--pair-copies 3]
"""
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aixl.serialization import aixl_codec  # noqa: E402


def canon(aixl):
    try:
        return aixl_codec.encode(aixl_codec.decode(aixl))
    except Exception:  # noqa: BLE001
        return None


def load(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                out.append((d["text"], d["aixl"]))
    return out


def main():
    out_dir = os.path.join(ROOT, "distill", "mlx_data")
    n_valid, pair_copies = 150, 3
    if "--out" in sys.argv:
        out_dir = sys.argv[sys.argv.index("--out") + 1]
    if "--valid" in sys.argv:
        n_valid = int(sys.argv[sys.argv.index("--valid") + 1])
    if "--pair-copies" in sys.argv:
        pair_copies = int(sys.argv[sys.argv.index("--pair-copies") + 1])

    unique = {}
    for text, aixl in load(os.path.join(ROOT, "distill", "corpus_merged.jsonl")):
        unique[text] = aixl

    paired_texts = set()
    fresh = json.load(open(os.path.join(ROOT, "distill", "fresh_texts.json"), encoding="utf-8"))
    for p in fresh["pairs"]:
        paired_texts.update([p["a"], p["b"]])
    for text, aixl in load(os.path.join(ROOT, "distill", "corpus_consistent.jsonl")):
        pass  # the base consistency corpus already repeats its EQUIVALENT pairs 3x; re-derive membership below
    counts = {}
    for text, _ in load(os.path.join(ROOT, "distill", "corpus_consistent.jsonl")):
        counts[text] = counts.get(text, 0) + 1
    paired_texts.update(t for t, c in counts.items() if c > 1)

    clean, dropped, changed = {}, 0, 0
    for text, aixl in unique.items():
        c = canon(aixl)
        if c is None:
            dropped += 1
            continue
        changed += c != aixl
        clean[text] = c

    rng = random.Random(0)
    texts = sorted(clean)
    rng.shuffle(texts)
    valid_texts = [t for t in texts if t not in paired_texts][:n_valid]
    valid_set = set(valid_texts)

    train_rows = []
    for t in texts:
        if t in valid_set:
            continue
        copies = pair_copies if t in paired_texts else 1
        train_rows.extend([t] * copies)
    rng.shuffle(train_rows)

    os.makedirs(out_dir, exist_ok=True)

    def dump(name, items):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            for t in items:
                row = {"messages": [{"role": "user", "content": t}, {"role": "assistant", "content": clean[t]}]}
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    dump("train.jsonl", train_rows)
    dump("valid.jsonl", valid_texts)
    print(f"unique texts: {len(unique)}  dropped(undecodable): {dropped}  relabeled-by-canonicalization: {changed}")
    print(f"paired (oversampled x{pair_copies}): {len(paired_texts & set(clean))}")
    print(f"train rows: {len(train_rows)}  valid rows: {len(valid_texts)}  -> {out_dir}")


if __name__ == "__main__":
    main()
