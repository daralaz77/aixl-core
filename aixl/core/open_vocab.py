"""NOT WIRED INTO ANY PUBLISHED LAYER (negative result, 2026-10-13: LIMITATIONS.md E-OPEN-VOCAB).
Open-vocabulary verification: when the closed lexicon does not account for some words, they are not understood, but they can still be
PROVEN THE SAME on both sides. Rule (all must hold):
  1. the core graphs are equivalent (everything the lexicon models is equal),
  2. neither text has an unreflected marker (negation, quantifier, comparator, condition ... the modelled operators are all carried by the graph),
  3. the ordered sequence of unaccounted tokens is IDENTICAL in A and B (same words, same multiplicity, same order).
Sameness of a word needs no meaning; a word whose role changed between the texts is only possible through a modelled operator (rule 1-2) or a
reorder (rule 3). Residual risk, measured not assumed: benchmarks/open_vocab_eval.py."""
from aixl.core.completeness import _ALLTOK, _norm, check_completeness

_TOK = _ALLTOK


def residue_sequence(text: str, graph) -> tuple | None:
    """Ordered unaccounted tokens of `text`, or None when an operator marker is unreflected (no open-vocabulary claim possible)."""
    r = check_completeness(text, graph)
    if r["unreflected_markers"]:
        return None
    gone = set(r["unaccounted"])
    return tuple(w for w in _TOK.findall(_norm(text)) if w in gone)


def _differing_tokens(text_a: str, text_b: str) -> set:
    from collections import Counter
    ca, cb = Counter(_TOK.findall(_norm(text_a))), Counter(_TOK.findall(_norm(text_b)))
    return set((ca - cb).elements()) | set((cb - ca).elements())


def _operator_words() -> set:
    from aixl.core.completeness import MARKERS
    from aixl.core.lexicon_gaps import FUNCTION_WORDS
    ops = set(FUNCTION_WORDS)
    for words in MARKERS.values():
        for p in words:
            ops |= set(p.split())
    return ops | {"no", "not", "nunca", "never", "jamas", "sin", "without", "nem", "nao", "ni", "y", "e", "o", "ou", "and", "or", "si", "if", "se", "except", "excepto", "salvo"}


def residue_identical(text_a: str, graph_a, text_b: str, graph_b) -> bool:
    """Rule 4: every token that differs between the texts must be CONTENT the lexicon accounts for (a modelled word swapped for a modelled word,
    already compared by the graph) - never a function word / operator, whose count the graph does not track (`never if ...` vs `if ...`)."""
    ra, rb = residue_sequence(text_a, graph_a), residue_sequence(text_b, graph_b)
    if ra is None or rb is None or ra != rb or not ra:
        return False
    return not (_differing_tokens(text_a, text_b) & _operator_words()) and not (set(_differing_tokens(text_a, text_b)) & set(ra))


__all__ = ["residue_sequence", "residue_identical"]
