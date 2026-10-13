"""Disjunction guard (consejo-5x audit 2026-10-13). 'a Ana y a Luis' -> 'a Ana o a Luis' flips AND to OR, yet `y`/`o` are function words: no layer
counted them as content, so the core comparator said EQUIVALENT and the integrity envelope said MATCH. The count of OR tokens is a cheap, conservative
witness: if it differs between two texts, no layer may claim they mean the same.
Deliberately over-cautious: PT article `o` is counted too, so 'o relatório' vs 'relatório' also differs -> the claim is withheld (safe direction)."""
import re

from aixl.core.normalizer import strip_accents

_OR = frozenset({"o", "u", "or", "ou"})


def or_count(text: str) -> int:
    return sum(1 for t in re.findall(r"[a-z]+", strip_accents(text).lower()) if t in _OR)


def disjunction_differs(a: str, b: str) -> bool:
    return or_count(a) != or_count(b)
