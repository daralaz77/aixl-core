"""Runtime resources shipped INSIDE the package (config.json = weights/severities/irreversible actions; arbiter_rules_v1.txt = the strict-arbiter rules).
They used to live in the repo's top-level data/ directory, outside the package: a built wheel (`pip install aixl-0.5.0-py3-none-any.whl`) therefore failed on
EVERY call with FileNotFoundError (found 2026-10-13 by installing the wheel in an empty venv). Declared as package-data in pyproject.toml."""
import os

DIR = os.path.dirname(os.path.abspath(__file__))


def path(name: str) -> str:
    return os.path.join(DIR, name)
