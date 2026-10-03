"""Packs everything the Colab pipeline needs into one small zip: the project's real codec/comparator (so F1 is
computed by the SAME code as every other route), blind5 texts + gold pairs, the training data and pipeline.py."""
import os, sys, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "distill", "colab", "bundle.zip")

def add_tree(z, rel):
    for dp, dn, fn in os.walk(os.path.join(ROOT, rel)):
        dn[:] = [d for d in dn if d != "__pycache__"]
        for f in fn:
            if f.endswith((".pyc", ".DS_Store")):
                continue
            p = os.path.join(dp, f)
            z.write(p, os.path.relpath(p, ROOT))

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    add_tree(z, "aixl")
    for f in ("benchmarks/__init__.py", "benchmarks/metrics.py", "benchmarks/llm_translator_eval.py"):
        if os.path.exists(os.path.join(ROOT, f)):
            z.write(os.path.join(ROOT, f), f)
    z.write(os.path.join(ROOT, "data/config.json"), "data/config.json")
    z.write(os.path.join(ROOT, "data/llm_translator/texts_blind5.json"), "data/llm_translator/texts_blind5.json")
    for f in ("pairs_A5.jsonl", "pairs_B5.jsonl"):
        z.write(os.path.join(ROOT, "data/blind5", f), f"data/blind5/{f}")
    z.write(os.path.join(ROOT, "distill/mlx_data/train.jsonl"), "mlx_data/train.jsonl")
    z.write(os.path.join(ROOT, "distill/mlx_data/valid.jsonl"), "mlx_data/valid.jsonl")
    dev = os.path.join(ROOT, "distill/mlx_data/dev_groups.jsonl")
    if os.path.exists(dev):
        z.write(dev, "mlx_data/dev_groups.jsonl")
    z.write(os.path.join(ROOT, "distill/colab/pipeline.py"), "pipeline.py")
    z.write(os.path.join(ROOT, "distill/colab/sweep.py"), "sweep.py")
    z.write(os.path.join(ROOT, "distill/aixl.gbnf"), "aixl.gbnf")
print(OUT, os.path.getsize(OUT) // 1024, "KB")
