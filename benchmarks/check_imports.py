"""Refactor gate (docs/CLEANUP_ROADMAP.md): every `from aixl... import name` / `import aixl...` anywhere in the repo must still resolve.
Covers benchmarks/, cli.py, scripts, tests, which the unit tests do not import.  python -m benchmarks.check_imports"""
import ast
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".venv", ".venv-mlx", "distill", ".git", "__pycache__", "node_modules"}


def py_files():
    for p in ROOT.rglob("*.py"):
        if not (set(p.relative_to(ROOT).parts) & SKIP_DIRS):
            yield p


def main():
    sys.path.insert(0, str(ROOT))
    bad, checked = [], 0
    for f in py_files():
        try:
            tree = ast.parse(f.read_text())
        except SyntaxError as e:
            bad.append((f, 0, f"syntax error: {e}")); continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.level == 0 and node.module.split(".")[0] == "aixl":
                try:
                    mod = importlib.import_module(node.module)
                except Exception as e:
                    bad.append((f, node.lineno, f"cannot import module {node.module}: {type(e).__name__}: {e}")); continue
                for a in node.names:
                    checked += 1
                    if a.name != "*" and not hasattr(mod, a.name):
                        try:
                            importlib.import_module(f"{node.module}.{a.name}")   # a submodule import
                        except Exception:
                            bad.append((f, node.lineno, f"{node.module} has no name {a.name!r}"))
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.split(".")[0] == "aixl":
                        checked += 1
                        try:
                            importlib.import_module(a.name)
                        except Exception as e:
                            bad.append((f, node.lineno, f"cannot import {a.name}: {type(e).__name__}"))
    for f, ln, msg in bad:
        print(f"{f.relative_to(ROOT)}:{ln}: {msg}")
    print(f"{checked} aixl imports checked across the repo, {len(bad)} unresolved")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
