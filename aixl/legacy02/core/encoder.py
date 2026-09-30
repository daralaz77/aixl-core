"""Encoding layer: SemanticFrame -> AIXL text (spec §17)."""
import re
from aixl.legacy02.core.semantic_frame import SemanticFrame
from aixl.legacy02.core.normalizer import normalize
from aixl.legacy02.protocol.atoms import ATOMS, ORDER

_BARE = re.compile(r'^[^\s",\\]+$')


def quote_item(s: str) -> str:
    if _BARE.match(s):
        return s
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def encode(frame: SemanticFrame, do_normalize=True) -> str:
    f = normalize(frame) if do_normalize else frame
    toks = []
    for letter in ORDER:
        field, is_list = ATOMS[letter]
        v = getattr(f, field)
        if is_list:
            if not v:
                continue
            toks.append(f"{letter}:" + ",".join(quote_item(x) for x in v))
        else:
            if not v:
                continue
            toks.append(f"{letter}:{v if letter == 'T' and re.match(r'^[^\s\"\\\\]+$', v) else quote_item(v)}")
    return " ".join(toks)
