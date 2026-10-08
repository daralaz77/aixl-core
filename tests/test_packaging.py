"""Packaging guard: files that code reads relative to its own location must be declared as package-data, or an installed wheel loses them
(for aixl.atoms that was SILENT: registry._load_learned() returns [] when its JSON is missing)."""
import fnmatch
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_every_atoms_data_file_is_declared_as_package_data():
    cfg = tomllib.loads((ROOT / "pyproject.toml").read_text())
    patterns = cfg["tool"]["setuptools"]["package-data"]["aixl.atoms"]
    base = ROOT / "aixl" / "atoms"
    data_files = [p.relative_to(base).as_posix() for p in (base / "data").rglob("*") if p.is_file()]
    assert data_files, "expected data files under aixl/atoms/data"
    missing = [f for f in data_files if not any(fnmatch.fnmatch(f, pat) for pat in patterns)]
    assert not missing, f"not covered by package-data (would be missing from the wheel): {missing}"
