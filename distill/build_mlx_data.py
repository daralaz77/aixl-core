"""Builds the MLX LoRA training set (chat format, no system prompt -> ~40% fewer tokens per example) from the
already-validated corpora. Keeps the proven consistency mechanism (EQUIVALENT pairs share ONE target and are
oversampled 3x), normalizes every label through the real codec (encode(decode(x))) so the student learns a
single canonical serialization, and drops anything the codec cannot decode.

usage: python distill/build_mlx_data.py [--out distill/mlx_data] [--valid 150] [--pair-copies 3]
"""
import json
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aixl.serialization import aixl_codec  # noqa: E402
from aixl.translators.natural_to_semantic import to_graph  # noqa: E402


def canon(aixl):
    try:
        return aixl_codec.encode(aixl_codec.decode(aixl))
    except Exception:  # noqa: BLE001
        return None


_PT_VERB = re.compile(r"\b(?:exclua|excluam|excluir|exclui|apague|apagar|apaga)\b", re.I)


def fix_pt_delete(text, aixl):
    """2026-10-02 vocabulary decision (card sha 6320431e...): Portuguese "excluir/exclua" and "apagar/apague" applied to data
    are DELETE. The cloud teachers labelled them EXCLUDE/DISABLE under the old card (117+ rows), which is what taught the
    local model to hide PT deletes from the irreversible-action check. Relabel only when the rule-based translator (which
    carries the PT-evidence gate and the "da análise/do relatório" and "apague a luz" exceptions) also says DELETE."""
    if not _PT_VERB.search(text):
        return aixl
    try:
        rule = aixl_codec.encode(to_graph(text))
    except Exception:  # noqa: BLE001
        return aixl
    def acts(a):
        m = re.search(r" A:(\S+)", a)
        return set(m.group(1).split(",")) if m else set()
    old, new = acts(aixl), acts(rule)
    swap = [a for a in ("EXCLUDE", "DISABLE") if a in old and a not in new]
    if "DELETE" not in new or "DELETE" in old or not swap:
        return aixl
    out = aixl
    for a in swap:
        out = re.sub(rf"(?<![A-Z]){a}(?![A-Z])", "DELETE", out)
    out = out.replace("I:REQUEST_TRANSFORMATION", "I:REQUEST_EXECUTION")
    return canon(out) or aixl


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
    n_valid, pair_copies, n_dev_groups = 150, 3, 80
    if "--out" in sys.argv:
        out_dir = sys.argv[sys.argv.index("--out") + 1]
    if "--valid" in sys.argv:
        n_valid = int(sys.argv[sys.argv.index("--valid") + 1])
    if "--dev-groups" in sys.argv:
        n_dev_groups = int(sys.argv[sys.argv.index("--dev-groups") + 1])
    qwen_path = sys.argv[sys.argv.index("--qwen") + 1] if "--qwen" in sys.argv else None
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
    # consensus paraphrase groups (distill/gen_paraphrase_groups.py): forced identical target per group
    groups = {}
    para_path = os.path.join(ROOT, "distill", "corpus_paraphrase.jsonl")
    if os.path.exists(para_path):
        for line in open(para_path, encoding="utf-8"):
            if line.strip():
                d = json.loads(line)
                groups.setdefault(d["group"], []).append((d["text"], d["aixl"]))
    gkeys = sorted(groups)
    random.Random(11).shuffle(gkeys)
    dev_keys = set(gkeys[:n_dev_groups])
    dev_rows = [(t, a, g) for g in gkeys[:n_dev_groups] for t, a in groups[g]]
    dev_texts = {t for t, _, _ in dev_rows}
    for g in gkeys[n_dev_groups:]:
        for t, a in groups[g]:
            unique[t] = a
            paired_texts.add(t)
    n_q_groups = n_q_texts = 0
    if qwen_path:  # open-model paraphrase groups (distill/build_qwen_groups.py): label = the seed's validated label, x pair_copies
        qgroups = {}
        for line in open(qwen_path, encoding="utf-8"):
            if line.strip():
                d = json.loads(line)
                qgroups.setdefault(d["group"], []).append((d["text"], d["aixl"]))
        for g, members in qgroups.items():
            if g[2:] in dev_keys:  # never train on a seed whose group is held out as DEV
                continue
            n_q_groups += 1
            for t, a in members:
                if t in unique and unique[t] != a and t != g[2:]:
                    continue  # a different label already exists for this exact text: keep the validated one
                if t not in dev_texts:
                    unique[t] = a
                    paired_texts.add(t)
                    n_q_texts += 1
    counts = {}
    for text, _ in load(os.path.join(ROOT, "distill", "corpus_consistent.jsonl")):
        counts[text] = counts.get(text, 0) + 1
    paired_texts.update(t for t, c in counts.items() if c > 1)

    clean, dropped, changed, pt_fixed = {}, 0, 0, 0
    for text, aixl in unique.items():
        c = canon(aixl)
        if c is None:
            dropped += 1
            continue
        c2 = fix_pt_delete(text, c)
        pt_fixed += c2 != c
        c = c2
        changed += c != aixl
        clean[text] = c

    rng = random.Random(0)
    texts = sorted(t for t in clean if t not in dev_texts)
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
    with open(os.path.join(out_dir, "dev_groups.jsonl"), "w", encoding="utf-8") as f:
        for t, a, g in dev_rows:
            c = canon(a)
            c = fix_pt_delete(t, c) if c else c
            if c:
                f.write(json.dumps({"text": t, "aixl": c, "group": g}, ensure_ascii=False) + "\n")
    print(f"paraphrase groups: {len(gkeys)} (dev held-out groups: {len(dev_keys)}, dev texts: {len(dev_rows)})")
    print(f"unique texts: {len(unique)}  dropped(undecodable): {dropped}  relabeled-by-canonicalization: {changed}")
    print(f"open-model groups used: {n_q_groups} ({n_q_texts} texts) from {qwen_path}")
    print(f"relabeled PT delete verbs (excluir/apagar -> DELETE): {pt_fixed}")
    print(f"paired (oversampled x{pair_copies}): {len(paired_texts & set(clean))}")
    print(f"train rows: {len(train_rows)}  valid rows: {len(valid_texts)}  -> {out_dir}")


if __name__ == "__main__":
    main()
