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


def test_runtime_resources_are_inside_the_package_and_declared():
    cfg = tomllib.loads((ROOT / "pyproject.toml").read_text())
    patterns = cfg["tool"]["setuptools"]["package-data"]["aixl.resources"]
    base = ROOT / "aixl" / "resources"
    files = [p.name for p in base.iterdir() if p.is_file() and p.suffix != ".py"]
    assert {"config.json", "arbiter_rules_v1.txt"} <= set(files)
    assert not [f for f in files if not any(fnmatch.fnmatch(f, pat) for pat in patterns)]
    from aixl.core import ontology
    from aixl.resources import path
    assert path("config.json").startswith(str(ROOT / "aixl"))               # inside the package, not the repo's top-level data/
    assert ontology.load_config()["weights"]
