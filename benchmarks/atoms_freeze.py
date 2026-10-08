"""Write the freeze manifest of a pre-registered atoms experiment:  python -m benchmarks.atoms_freeze blind5
Hashes everything that defines the state being tested (code, guide, registry data, cases, batches, prompts, the evaluation script itself).
atoms_ab_eval.py refuses to run if any hash differs: the experiment is then void (same discipline as data/blind14..18/CODE_FREEZE.json)."""
import glob
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def files_for(set_name):
    pats = ["aixl/atoms/*.py", "aixl/atoms/data/*.json", "aixl/semantic/*.py", "docs/ATOM_MODEL.md",
            "benchmarks/atoms_ab_eval.py", "benchmarks/atoms_gold.py", "benchmarks/atoms_sources.py", "benchmarks/atoms_freeze.py",
            f"data/atoms/{set_name}_cases.json", f"data/atoms/batches/{set_name}_b*.json", f"data/atoms/llm/prompt_{set_name}_*.txt"]
    return sorted({os.path.relpath(p, ROOT) for pat in pats for p in glob.glob(os.path.join(ROOT, pat))})


def sha(path):
    return hashlib.sha256(open(os.path.join(ROOT, path), "rb").read()).hexdigest()


def manifest_path(set_name):
    return os.path.join(ROOT, "data", "atoms", f"FREEZE_{set_name}.json")


def check(set_name):
    """Return the list of problems (empty = frozen state intact)."""
    p = manifest_path(set_name)
    if not os.path.exists(p):
        return [f"no freeze manifest at {os.path.relpath(p, ROOT)}"]
    want = json.load(open(p))
    bad = [f"{f}: {'missing' if not os.path.exists(os.path.join(ROOT, f)) else 'changed'}" for f, h in want.items()
           if not os.path.exists(os.path.join(ROOT, f)) or sha(f) != h]
    extra = [f for f in files_for(set_name) if f not in want]
    return bad + [f"{f}: new file not in the freeze" for f in extra]


if __name__ == "__main__":
    s = sys.argv[1] if len(sys.argv) > 1 else "blind5"
    m = {f: sha(f) for f in files_for(s)}
    json.dump(m, open(manifest_path(s), "w"), indent=1, sort_keys=True)
    open(manifest_path(s), "a").write("\n")
    print(f"froze {len(m)} files -> {os.path.relpath(manifest_path(s), ROOT)}")
