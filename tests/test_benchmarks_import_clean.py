"""Phase 4 gate: importing ANY benchmarks module must be side-effect free (no output, no work, no error). Run in one subprocess so a stray
experiment cannot pollute the test session. Experiments live under `if __name__ == "__main__":`."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCRIPT = r'''
import contextlib, glob, importlib, io, os, sys
sys.path.insert(0, ".")
bad = []
for f in sorted(glob.glob("benchmarks/*.py")):
    m = os.path.basename(f)[:-3]
    if m == "__init__":
        continue
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            importlib.import_module("benchmarks." + m)
        err = None
    except BaseException as e:
        err = type(e).__name__ + ": " + str(e)[:80]
    if buf.getvalue() or err:
        bad.append((m, err, len(buf.getvalue())))
print(repr(bad))
'''


def test_every_benchmark_module_imports_silently():
    r = subprocess.run([sys.executable, "-c", SCRIPT], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-300:]
    assert r.stdout.strip().splitlines()[-1] == "[]", f"modules that run code or fail on import: {r.stdout.strip().splitlines()[-1]}"
