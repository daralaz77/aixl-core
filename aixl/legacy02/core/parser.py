"""Encoding layer: AIXL text -> SemanticFrame, with syntax errors (spec §34-35)."""
import re
from aixl.legacy02.core.semantic_frame import SemanticFrame
from aixl.legacy02.protocol.atoms import ATOMS


class AixlError(Exception):
    def __init__(self, code, msg=""):
        super().__init__(f"ERROR:{code} {msg}".strip())
        self.code = code


def _collapse_comparator_space(s):
    """Tolerance fix (E-XV finding, 2026-09-27): several LLM encoders write a stray space between a
    comparator operator and its number, e.g. `H:> .90` or `F:COUNT >= 100`. That space would otherwise
    split into a separate, unparseable token. Collapse it, but only outside quoted literals, and only
    when the operator is directly followed by whitespace then a digit or a decimal point."""
    out, inq, esc = [], False, False
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if esc:
            out.append(ch); esc = False; i += 1; continue
        if ch == "\\" and inq:
            out.append(ch); esc = True; i += 1; continue
        if ch == '"':
            inq = not inq; out.append(ch); i += 1; continue
        if not inq and ch in "<>=" :
            j = i + 1
            if ch in "<>" and j < n and s[j] == "=":
                out.append(s[i:j + 1]); i = j + 1
            else:
                out.append(ch); i += 1
            k = i
            while k < n and s[k].isspace():
                k += 1
            if k > i and k < n and (s[k].isdigit() or s[k] == "."):
                i = k
            continue
        out.append(ch); i += 1
    return "".join(out)


def _split_tokens(s):
    """Split on spaces outside double quotes."""
    toks, cur, inq, esc = [], [], False, False
    for ch in s.strip():
        if esc:
            cur.append(ch); esc = False
        elif ch == "\\" and inq:
            cur.append(ch); esc = True
        elif ch == '"':
            inq = not inq; cur.append(ch)
        elif ch.isspace() and not inq:
            if cur:
                toks.append("".join(cur)); cur = []
        else:
            cur.append(ch)
    if inq:
        raise AixlError("INVALID_AIXL", "unterminated quote")
    if cur:
        toks.append("".join(cur))
    return toks


def _split_items(v):
    """Split on commas outside quotes; unquote/unescape items."""
    items, cur, inq, esc = [], [], False, False
    for ch in v:
        if esc:
            cur.append(ch); esc = False
        elif ch == "\\" and inq:
            esc = True
        elif ch == '"':
            inq = not inq
        elif ch == "," and not inq:
            items.append("".join(cur)); cur = []
        else:
            cur.append(ch)
    items.append("".join(cur))
    return items


def parse(text: str) -> SemanticFrame:
    """Raises AixlError(INVALID_AIXL) on malformed input, VERSION_MISMATCH on bad version."""
    from aixl.legacy02.protocol.versions import check_version
    if not text or not text.strip():
        raise AixlError("INVALID_AIXL", "empty message")
    f = SemanticFrame(version="")
    seen = set()
    for tok in _split_tokens(_collapse_comparator_space(text)):
        m = re.match(r"^([A-Z]):(.*)$", tok, re.S)
        if not m:
            raise AixlError("INVALID_AIXL", f"bad token {tok!r}")
        k, v = m.groups()
        if k not in ATOMS:
            raise AixlError("INVALID_AIXL", f"unknown atom {k}")
        field, is_list = ATOMS[k]
        if k in seen:
            # Tolerance fix (E-XV finding, 2026-09-27): an LLM encoder sometimes repeats a LIST atom
            # letter instead of merging into one comma-separated token (e.g. two `E:` tokens). The
            # card forbids this, but the meaning is unambiguous (union of the values), so merge rather
            # than reject. A repeated SCALAR atom (V, I, T, H, P, G, O... none of them list) stays an
            # error: two different values for a single-value atom is a real conflict, not a formatting slip.
            if not is_list:
                raise AixlError("INVALID_AIXL", f"duplicate atom {k}")
        else:
            seen.add(k)
        if v == "":
            raise AixlError("INVALID_AIXL", f"empty value for {k}")
        items = _split_items(v)
        if is_list:
            setattr(f, field, getattr(f, field) + items)
        else:
            if len(items) != 1 and k != "T":
                raise AixlError("INVALID_AIXL", f"{k} takes one value")
            setattr(f, field, ",".join(items) if k == "T" else items[0])
    if not f.version:
        raise AixlError("INVALID_AIXL", "missing V:")
    if not check_version(f.version):
        raise AixlError("VERSION_MISMATCH", f.version)
    return f
