#!/bin/zsh
# Refactor/audit gate: tests + import resolution + lint. Exit 1 on any failure.   scripts/gate.sh
cd "$(dirname "$0")/.." || exit 2
PY=.venv/bin/python
out=$($PY -m pytest tests -q 2>&1 | tail -1); echo "$out"
imp=$($PY -m benchmarks.check_imports 2>&1 | tail -1); echo "$imp"
lint=$(git ls-files '*.py' benchmarks/_corpus.py | sort -u | xargs $PY -m ruff check 2>&1 | tail -1); echo "lint: $lint"
[[ "$out" == *failed* || "$out" == *error* || "$imp" != *" 0 unresolved" || "$lint" != "All checks passed!" ]] && { echo "GATE FAILED"; exit 1; }
echo "GATE OK"
