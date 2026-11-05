"""Generate a CycloneDX 1.5 SBOM (JSON) for aixl-core from pyproject.toml, using only the standard library.

The core has no runtime dependency; the optional extras (mcp, a2a, llm, signing, otel, dev) are listed as components with the version actually
installed when there is one ("version" is omitted otherwise, never invented). usage: python scripts/make_sbom.py [out.json]
"""
import json
import re
import sys
import tomllib
import uuid
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _name(req: str) -> str:
    return re.split(r"[\[<>=!~; ]", req.strip(), maxsplit=1)[0]


def build(pyproject: Path = ROOT / "pyproject.toml") -> dict:
    proj = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]
    comps, seen = [], set()
    groups = [("required", proj.get("dependencies", []))] + [(f"extra:{k}", v) for k, v in proj.get("optional-dependencies", {}).items()]
    for group, reqs in groups:
        for req in reqs:
            name = _name(req)
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            comp = {"type": "library", "name": name, "scope": "required" if group == "required" else "optional",
                    "properties": [{"name": "aixl:group", "value": group}, {"name": "aixl:declared", "value": req}]}
            try:
                comp["version"] = metadata.version(name)
                comp["purl"] = f"pkg:pypi/{name.lower()}@{comp['version']}"
            except metadata.PackageNotFoundError:
                comp["purl"] = f"pkg:pypi/{name.lower()}"
            comps.append(comp)
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{uuid.uuid4()}", "version": 1,
            "metadata": {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                         "component": {"type": "application", "name": proj["name"], "version": str(proj.get("version", "0"))}},
            "components": comps}


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "sbom.cdx.json"
    out.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(build()['components'])} components)")
