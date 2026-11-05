import importlib.util
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("make_sbom", ROOT / "scripts" / "make_sbom.py")
make_sbom = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make_sbom)


def test_sbom_lists_every_declared_dependency_and_invents_no_version():
    bom = make_sbom.build()
    proj = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    declared = {make_sbom._name(r).lower() for reqs in proj.get("optional-dependencies", {}).values() for r in reqs} | {make_sbom._name(r).lower() for r in proj.get("dependencies", [])}
    assert {c["name"].lower() for c in bom["components"]} == declared
    assert bom["bomFormat"] == "CycloneDX" and bom["specVersion"] == "1.5"
    for c in bom["components"]:
        assert c["purl"].startswith("pkg:pypi/")
        if "version" not in c:
            assert "@" not in c["purl"]            # a version that is not installed is never made up


def test_the_core_has_no_required_runtime_dependency():
    bom = make_sbom.build()
    assert [c["name"] for c in bom["components"] if c["scope"] == "required"] == []
