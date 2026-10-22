#!/bin/zsh
# Refactor/audit gate: tests + import resolution + lint. Exit 1 on any failure.   scripts/gate.sh
# A failing pytest run is RECORDED (.gate_logs/): the full output plus, in flaky.log, the time, load average and the FAILED lines -- so a test that fails once and
# passes on the rerun (2026-10-22: one such failure was seen and never identified because nothing was kept) can be named afterwards.
setopt shwordsplit 2>/dev/null   # zsh: split $GATE_PYTEST_ARGS into words (bash does it already)
cd "$(dirname "$0")/.." || exit 2
PY=.venv/bin/python
mkdir -p .gate_logs
full=$(mktemp)
$PY -m pytest tests -q -rfE $GATE_PYTEST_ARGS > "$full" 2>&1
out=$(tail -1 "$full"); echo "$out"
if [[ "$out" == *failed* || "$out" == *error* ]]; then
  ts=$(date +%Y%m%dT%H%M%S)
  cp "$full" ".gate_logs/pytest_fail_$ts.log"
  { echo "== $ts load: $(uptime | sed 's/.*load averages*: //') head: $(git rev-parse --short HEAD 2>/dev/null)"; grep -E "^(FAILED|ERROR)" "$full"; } >> .gate_logs/flaky.log
  echo "pytest failures recorded: .gate_logs/pytest_fail_$ts.log (summary in .gate_logs/flaky.log)"
  grep -E "^(FAILED|ERROR)" "$full" | head -10
fi
rm -f "$full"
imp=$($PY -m benchmarks.check_imports 2>&1 | tail -1); echo "$imp"
lint=$(git ls-files '*.py' benchmarks/_corpus.py | sort -u | xargs $PY -m ruff check 2>&1 | tail -1); echo "lint: $lint"
[[ "$out" != *passed* || "$out" == *failed* || "$out" == *error* || "$imp" != *" 0 unresolved" || "$lint" != "All checks passed!" ]] && { echo "GATE FAILED"; exit 1; }
echo "GATE OK"
