"""Architecture fitness test (ADR-022, option A). The layering below was MEASURED on 2026-10-08 and held; this test keeps it true.

  legacy02            leaf: wire syntax, frame, rule tables (historical name, NOT dead code)
  core/translators/   the product; reach legacy02 and each other, never the experimental tracks
  serialization/api/...
  semantic            EXPERIMENTAL 0.3-R track  -> may import only core and the root API
  atoms               EXPERIMENTAL atoms layer  -> may import only semantic (and itself)
  hybrid_protocol     the one deliberate bridge from the product surface (MCP hybrid tool) to `semantic`
"""
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTAL = {"semantic", "atoms"}
BRIDGES = {"aixl.hybrid_protocol"}           # allowed to import the experimental packages
ALLOWED = {"semantic": {"semantic", "core", "(root)"}, "atoms": {"atoms", "semantic"}}


def _modules():
    out = {}
    for f in (ROOT / "aixl").rglob("*.py"):
        rel = f.relative_to(ROOT).with_suffix("")
        parts = list(rel.parts)
        if parts[-1] == "__init__":
            parts.pop()
        out[".".join(parts)] = f
    return out


def _imports(path, lazy):
    """aixl.* modules imported by a file. lazy=False: only import-time statements (module level, including inside if/try)."""
    tree = ast.parse(path.read_text())
    found = set()

    def add(node):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "aixl" and node.level == 0:
            found.add(node.module)
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] == "aixl":
                    found.add(a.name)

    if lazy:
        for n in ast.walk(tree):
            add(n)
    else:
        stack = list(tree.body)
        while stack:
            n = stack.pop()
            add(n)
            if isinstance(n, (ast.If, ast.Try)):
                stack += n.body + n.orelse + [s for h in getattr(n, "handlers", []) for s in h.body] + getattr(n, "finalbody", [])
    return found


def violations(mods, imports_lazy, imports_static):
    """Pure rule engine over {module: set(imported aixl modules)}; returns a list of human-readable violations."""
    bad = []
    def pkg(m):
        return _pkg_of(m, mods)

    for m, targets in imports_lazy.items():
        pm = pkg(m)
        for t in targets:
            pt = pkg(t) if t in mods else _pkg_name(t)
            if pm == "legacy02" and pt != "legacy02":                                                   # R1
                bad.append(f"R1 legacy02 must be a leaf: {m} imports {t}")
            if pt in EXPERIMENTAL and pm not in EXPERIMENTAL and m not in BRIDGES:                      # R2
                bad.append(f"R2 product code must not import experimental code: {m} imports {t}")
            if pm in ALLOWED and pt not in ALLOWED[pm]:                                                 # R3
                bad.append(f"R3 {pm} may import only {sorted(ALLOWED[pm])}: {m} imports {t}")
    for comp in _cycles({m: {t for t in ts if t in mods} - {m} for m, ts in imports_static.items()}):  # R4
        pk = {pkg(m) for m in comp}
        if len(pk) > 1:
            bad.append(f"R4 import-time cycle across packages {sorted(pk)}: {sorted(comp)[:4]}")
    return bad


def _pkg_name(mod):
    parts = mod.split(".")
    return parts[1] if len(parts) > 1 else "(root)"


def _pkg_of(mod, mods):
    parts = mod.split(".")
    if len(parts) == 1:
        return "(root)"
    if len(parts) == 2:
        return parts[1] if (ROOT / "aixl" / parts[1]).is_dir() else "(top:" + parts[1] + ")"
    return parts[1]


def _cycles(graph):
    index, low, st, on, res, c = {}, {}, [], set(), [], [0]
    sys.setrecursionlimit(10000)

    def sc(v):
        index[v] = low[v] = c[0]
        c[0] += 1
        st.append(v)
        on.add(v)
        for w in graph.get(v, ()):
            if w not in index:
                sc(w)
                low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = st.pop()
                on.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                res.append(comp)

    for v in list(graph):
        if v not in index:
            sc(v)
    return res


def test_real_layering_holds():
    mods = _modules()
    lazy = {m: _imports(f, True) for m, f in mods.items()}
    static = {m: _imports(f, False) for m, f in mods.items()}
    assert violations(mods, lazy, static) == []


def test_engine_detects_each_rule_when_broken():
    mods = {"aixl.legacy02.a": 1, "aixl.legacy02": 1, "aixl.core.x": 1, "aixl.semantic.s": 1, "aixl.atoms.t": 1, "aixl.api.service": 1}
    ok = {m: set() for m in mods}
    assert violations(mods, ok, ok) == []
    assert any("R1" in v for v in violations(mods, {**ok, "aixl.legacy02.a": {"aixl.core.x"}}, ok))
    assert any("R2" in v for v in violations(mods, {**ok, "aixl.api.service": {"aixl.semantic.s"}}, ok))
    assert any("R3" in v for v in violations(mods, {**ok, "aixl.semantic.s": {"aixl.api.service"}}, ok))
    assert any("R3" in v for v in violations(mods, {**ok, "aixl.atoms.t": {"aixl.core.x"}}, ok))
    cyc = {**ok, "aixl.core.x": {"aixl.api.service"}, "aixl.api.service": {"aixl.core.x"}}
    assert any("R4" in v for v in violations(mods, ok, cyc))
    assert violations(mods, {**ok, "aixl.hybrid_protocol": {"aixl.semantic.s"}}, ok) == []   # the declared bridge is allowed


def test_plain_import_aixl_does_not_load_experimental_code():          # R5, checked at runtime in a clean interpreter
    code = "import sys, aixl; print([m for m in sys.modules if m.startswith(('aixl.semantic', 'aixl.atoms'))])"
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr[-300:]
    assert r.stdout.strip() == "[]", r.stdout
