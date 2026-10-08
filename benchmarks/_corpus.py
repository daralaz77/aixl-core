"""Shared access to the local Claude Code transcripts used by the real-traffic benchmarks (was copy-pasted in 8 scripts).
Read locally only; nothing here sends data anywhere. `transcript_files()` keeps glob's native order on purpose: several seeded
scripts shuffle that list, so sorting it would change their (recorded) results.
The location can be overridden with AIXL_TRANSCRIPTS_GLOB (used by the tests)."""
import glob
import json
import os


def transcript_files():
    return glob.glob(os.environ.get("AIXL_TRANSCRIPTS_GLOB") or os.path.expanduser("~/.claude/projects/*/*.jsonl"))


def blocks(path):
    """Yield (kind, text) for every text block of a transcript: kind is user_text | assistant_text | tool_result."""
    for line in open(path, errors="ignore"):
        try:
            o = json.loads(line)
        except Exception:
            continue
        m = o.get("message")
        if not isinstance(m, dict):
            continue
        c, role = m.get("content"), o.get("type")
        if isinstance(c, str):
            yield "user_text" if role == "user" else "assistant_text", c
        elif isinstance(c, list):
            for b in c:
                if not isinstance(b, dict):
                    continue
                t = b.get("type")
                if t == "text":
                    yield ("user_text" if role == "user" else "assistant_text"), b.get("text", "")
                elif t == "tool_result":
                    x = b.get("content")
                    if isinstance(x, list):
                        x = "\n".join(y.get("text", "") for y in x if isinstance(y, dict) and y.get("type") == "text")
                    if isinstance(x, str):
                        yield "tool_result", x


def tool_results(path):
    return (t for k, t in blocks(path) if k == "tool_result")


def real_user_messages(skip_meta=False):
    """The user's own typed messages (plain strings), stripped, without system reminders / pasted wrappers / commands / bracketed tool echoes.
    skip_meta=True also drops records flagged isMeta (what v1_real_eval always did; the envelope/telegraph evals never did)."""
    out = set()
    for f in transcript_files():
        for line in open(f, errors="ignore"):
            try:
                o = json.loads(line)
            except Exception:
                continue
            if skip_meta and o.get("isMeta"):
                continue
            c = o.get("message", {}).get("content") if o.get("type") == "user" else None
            if isinstance(c, str):
                c = c.strip()
                if c and not c.startswith(("<", "[", "/")) and "system-reminder" not in c and "pasted_content" not in c:
                    out.add(c)
    return out
