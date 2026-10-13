"""Input-size guard (consejo-5x audit 2026-10-13). `to_graph` is O(n^2): a 62 KB text takes ~5 s and 80-120 KB of repeated years/numbers takes > 8 s,
and none of the servers (MCP, A2A, API) bounded the input, so ONE request could block the process. Real instructions are short; refusing a huge
input is the fail-closed answer. The limit is a *safety* bound, not a quality one: just under it the worst measured pattern costs well under a second."""
import os

DEFAULT_MAX_INPUT_CHARS = 16_384


class InputTooLarge(ValueError):
    """The text exceeds the analysis limit. Callers on the shipped path (gate, envelope) degrade to NATURAL / UNVERIFIED instead of raising."""


def max_input_chars() -> int:
    try:
        return max(1, int(os.environ.get("AIXL_MAX_INPUT_CHARS", DEFAULT_MAX_INPUT_CHARS)))
    except ValueError:
        return DEFAULT_MAX_INPUT_CHARS


def check_size(text: str) -> None:
    cap = max_input_chars()
    if len(text) > cap:
        raise InputTooLarge(f"input is {len(text):,} characters; the analysis limit is {cap:,} (override with AIXL_MAX_INPUT_CHARS)")
