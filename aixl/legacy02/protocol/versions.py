"""Protocol layer: versions and compatibility."""
CURRENT = "AIXL-0.2"
SUPPORTED = {"AIXL-0.2", "AIXL-0.3"}


def check_version(v: str) -> bool:
    return v in SUPPORTED
