"""The docs cannot drift from the code: every `aixl-example` line, every CLI command named, every required file."""
import os
import re
import subprocess
import sys

import pytest

import aixl
from aixl.legacy02.translators import natural_to_semantic as L

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
REQUIRED = ["README", "PROTOCOL", "SEMANTIC_MODEL", "DEVELOPER_GUIDE", "API_REFERENCE", "CLI_REFERENCE", "BENCHMARK_SPEC",
            "SECURITY_MODEL", "INTEROPERABILITY_GUIDE", "VERSIONING_POLICY", "EXTENSION_GUIDE"]       # master prompt §50


def read(name):
    with open(os.path.join(DOCS, name + ".md"), encoding="utf-8") as fh:
        return fh.read()


@pytest.mark.parametrize("name", REQUIRED)
def test_required_doc_exists_and_is_not_empty(name):
    assert len(read(name)) > 800


def examples():
    out = []
    for name in REQUIRED:
        for block in re.findall(r"```aixl-example\n(.*?)```", read(name), re.S):
            for line in block.strip().splitlines():
                text, line_aixl = [x.strip() for x in line.rsplit(" | ", 1)]
                out.append((name, text, line_aixl))
    return out


@pytest.mark.parametrize("name,text,expected", examples())
def test_every_documented_aixl_example_is_what_the_encoder_emits(name, text, expected):
    assert aixl.to_aixl(text) == expected


def test_at_least_one_example_is_documented():
    assert len(examples()) >= 5


def test_every_cli_command_named_in_the_docs_exists():
    cli = open(os.path.join(ROOT, "cli.py"), encoding="utf-8").read()
    named = set(re.findall(r"^\| `([a-z-]+)` \|", read("CLI_REFERENCE"), re.M))
    assert {"encode", "decode", "validate", "fingerprint", "compare", "drift"} <= named
    for cmd in named:
        assert f'"{cmd}"' in cli, cmd


def test_documented_validate_exit_codes_are_real():
    py = sys.executable
    ok = subprocess.run([py, "cli.py", "validate", "V:AIXL-0.3 A:SEND E:REPORT"], cwd=ROOT, capture_output=True, text=True)
    bad = subprocess.run([py, "cli.py", "validate", "garbage"], cwd=ROOT, capture_output=True, text=True)
    assert ok.returncode == 0 and ok.stdout.strip() == "VALID"
    assert bad.returncode == 1 and bad.stdout.startswith("INVALID INVALID_AIXL")


def test_documented_api_functions_exist():
    for fn in re.findall(r"^\| `([a-z_]+)\(", read("API_REFERENCE"), re.M):
        assert hasattr(aixl, fn), fn


def test_documented_versions_are_the_supported_ones():
    from aixl.legacy02.protocol.versions import SUPPORTED
    assert SUPPORTED == {"AIXL-0.2", "AIXL-0.3"} and "AIXL-0.3" in read("PROTOCOL") and "AIXL-0.2" in read("PROTOCOL")
    with pytest.raises(aixl.serialization.aixl_codec.AixlError) as e:
        aixl.from_aixl("V:AIXL-0.2.5 A:SEND")
    assert e.value.code == "VERSION_MISMATCH"


def test_extension_guide_worked_example_really_works(monkeypatch):
    monkeypatch.setattr(L, "ENTITY_RX", list(L.ENTITY_RX))
    monkeypatch.setattr(L, "NOUN_CANON", dict(L.NOUN_CANON))
    before = aixl.compare("Generate the invoice today.", "Generate the report today.")
    assert before.warnings and before.warnings[0]["type"] == "UNRECOGNIZED_TERMS"
    L.ENTITY_RX.append(("INVOICE", r"\b(facturas?|invoices?|faturas?)\b"))
    L.NOUN_CANON["INVOICE"] = "INVOICE"
    after = aixl.compare("Generate the invoice today.", "Generate the report today.")
    assert not after.equivalent and [d.field for d in after.differences] == ["ENTITIES"]
    assert not [w for w in after.warnings if w["type"] == "UNRECOGNIZED_TERMS"]
    assert aixl.compare("Genera la factura hoy.", "Generate the invoice today.").equivalent


def test_documented_benchmark_numbers_match_the_ratchets():
    from tests.test_sil5x100 import FLOOR
    assert sum(FLOOR.values()) == 497 and "497/500" in read("BENCHMARK_SPEC") and "497/500" in read("README")
