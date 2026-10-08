"""Option C capability gate. Pointers are used ONLY for receivers measured safe; unknown receivers get plain text (fail closed).
Evidence (docs/V1_PROMPT_AUDIT.md): Sonnet 59-60/60 with pointers (52/60 full text); Haiku 14-18/60 with pointers (27/60 full text), even with legend or length annotation.
Opus: 59/60 reasoning with annotated pointers; 10/10 edit, 10/10 extract, 20/20 two-level chained lines, identical to full text (step 4).
Sonnet: step-4 edit/extract/chain could NOT be run (a safety classifier cut both Sonnet runs); its whitelist entry rests on the lookup and reasoning tests only."""
from aixl.refstore import RefStore

MEASURED = {"sonnet": True, "opus": True, "haiku": False}   # only what was actually measured; fable/others are NOT here on purpose


def pointers_allowed(receiver_model: str) -> bool:
    m = receiver_model.lower()
    for fam, ok in MEASURED.items():
        if fam in m:
            return ok
    return False


class PolicyStore:
    """RefStore that only emits pointers when the receiver is measured safe; otherwise encode() returns the text unchanged."""
    def __init__(self, receiver_model: str, annotate: bool = True):
        self.allowed = pointers_allowed(receiver_model)
        self._rs = RefStore(annotate=annotate)

    def encode(self, text: str) -> str:
        e = self._rs.encode(text)
        return e if self.allowed else text

    def decode(self, enc: str) -> str:
        return self._rs.decode(enc)
