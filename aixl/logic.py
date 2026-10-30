"""Logical-skeleton equivalence: do two instructions that reuse the SAME clauses say the same thing about how those clauses combine?

`logic_compare(a, b)` parses each text into a propositional formula over its CLAUSES (atoms) and decides by truth table (at most 10 atoms):
  EQUIVALENT_LOGIC  both parse, the atoms are the same set, and the formulas agree on every assignment (De Morgan, double negation, `if X, Y` = `Y if X`, contrapositive, distribution, `Y unless X` = `Y if not X`)
  DIFFERENT_LOGIC   both parse, the atoms are the same set, and some assignment separates them (converse, `only if` vs `if`, regrouped and/or, negation scope), with the counter-example
  ABSTAIN           anything else: a parse failure, mixed `and`/`or` without parentheses, nested conditionals, or atoms that differ (the engine does NOT claim anything about vocabulary)
Fail-closed by construction: it never proves two texts equal unless the clauses are textually identical (after lower-casing, accent stripping and article removal) and the logic matches.
Scope: propositional structure only. It does not understand what a clause means, numbers inside a clause are just text, and clauses are assumed logically independent. ES / EN / PT."""
import itertools
import re

from aixl.core.limits import check_size
from aixl.core.normalizer import strip_accents

MAX_ATOMS = 10


class Abstain(Exception):                                                  # noqa: N818 — control flow, not an error
    pass


# SCOPE negators open a clause and negate the WHOLE clause level that follows (`it is not true that we ship and we invoice` = NOT(ship AND invoice)).
_SCOPE_NEG = tuple(sorted((
    "it is not true that", "it's not true that", "it is false that", "it's false that", "it is not the case that", "it's not the case that",
    "no es cierto que", "no es verdad que", "es falso que", "no es el caso que",
    "nao e verdade que", "e falso que", "nao e o caso que",
), key=len, reverse=True))
# bare negators: used to recognise `not (A or B)` and to strip a negation inside one clause
_MODALS = frozenset(("must should shall may might can could need needs necessary required mandatory allowed permitted forbidden optional ought "
                     "debe deben debes deber debo debemos puede pueden puedes necesario necesaria obligatorio obligatoria permitido permitida prohibido prohibida conviene "
                     "deve devem deves pode podem precisa precisam necessario necessaria obrigatorio obrigatoria proibido proibida").split())
_BARE_NEG = frozenset(("not", "no", "nao", "never", "nunca", "jamas", "don't", "dont", "do not", "does not"))
_ARTICLES = {"en": frozenset("the a an".split()), "es": frozenset("el la los las un una unos unas lo".split()), "pt": frozenset("o os a as um uma uns umas".split())}
_AND = {"en": ("and",), "es": ("y", "e"), "pt": ("e",)}
_OR = {"en": ("or",), "es": ("o", "u"), "pt": ("ou",)}
_CUES = {"en": "the and if or not unless to of is are when".split(), "es": "el la los las de y si que no se un una cuando".split(), "pt": "o os as de e se que não nao uma quando um".split()}

_IFF = (("if", "and", "only", "if"), ("si", "y", "solo", "si"), ("si", "y", "solamente", "si"), ("se", "e", "somente", "se"))
_ONLYIF = (("only", "if"), ("solo", "si"), ("solamente", "si"), ("somente", "se"), ("apenas", "se"))
_UNLESS = (("unless",), ("a", "menos", "que"), ("a", "no", "ser", "que"), ("salvo", "que"), ("a", "nao", "ser", "que"))
_IF = (("if",), ("when",), ("whenever",), ("as", "long", "as"), ("provided", "that"), ("si",), ("cuando",), ("siempre", "que"), ("siempre", "y", "cuando"),
       ("se",), ("quando",), ("sempre", "que"), ("desde", "que"), ("contanto", "que"))
_THEN = ("then", "entonces", "entao")


def _lang(text: str) -> str:
    words = re.findall(r"[a-zà-ÿ']+", text.lower())
    score = {k: sum(1 for w in words if w in set(v)) for k, v in _CUES.items()}
    return max(score, key=lambda k: (score[k], k == "en"))


def _norm(text: str) -> str:
    t = re.sub(r"(?<!\w)é(?!\w)", "eh", text.lower())                       # Portuguese `é` (is) must not become `e` (and) when the accents are stripped
    t = strip_accents(t).replace("’", "'").replace("‘", "'")
    t = re.sub(r"[\"“”]", "", t)
    t = t.replace("(", " ( ").replace(")", " ) ").replace(",", " , ")
    return re.sub(r"\s+", " ", t).strip()


def _strip_neg(ws, lang):
    """Remove ONE negation from a clause (any position) and say whether it was there; two negations in one clause -> abstain (ambiguous)."""
    ws = list(ws)
    neg_idx = [i for i, w in enumerate(ws) if w in ("not", "n't") or (lang != "en" and w in ("no", "nao")) or w in ("never", "nunca", "jamas")
               or (w.endswith("n't") and len(w) > 3)]
    if not neg_idx:
        return ws, False
    if len(neg_idx) > 1:
        raise Abstain("two negations in one clause")
    i = neg_idx[0]
    w = ws[i]
    if w.endswith("n't") and w not in ("n't",):
        base = {"don't": None, "doesn't": None, "didn't": None, "isn't": "is", "aren't": "are", "wasn't": "was", "weren't": "were", "can't": "can", "won't": "will", "cannot": "can"}
        if w not in base:
            raise Abstain("an unrecognised contraction")
        if base[w] is None:
            del ws[i]
        else:
            ws[i] = base[w]
        return ws, True
    if w == "not" and i > 0 and ws[i - 1] in ("do", "does", "did"):
        del ws[i - 1:i + 1]
        return ws, True
    del ws[i]
    return ws, True


def _atom(words, lang):
    """A clause -> atom, with its negation peeled. `words` is a list of words, no connectives."""
    if any(w in _MODALS for w in words):
        ws, neg = list(words), False                      # `not necessary to restart` != `necessary not to restart`: with a modal the negation's POSITION matters, so it stays in the text
    else:
        ws, neg = _strip_neg(words, lang)
    ws = [w for w in ws if w not in _ARTICLES[lang] and w not in ("that", "que")]
    if not ws:
        raise Abstain("empty clause")
    node = ("atom", " ".join(ws))
    return ("not", node) if neg else node


def _tokens(s, lang):
    out, chunk = [], []
    for w in s.split():
        if w in ("(", ")") or w == "," or w in _AND[lang] or w in _OR[lang]:
            if chunk:
                out.append(("T", chunk))
                chunk = []
            out.append((w if w in ("(", ")", ",") else ("AND" if w in _AND[lang] else "OR"), None))
        else:
            chunk.append(w)
    if chunk:
        out.append(("T", chunk))
    return out


def _is_neg_only(words, lang):
    t = " ".join(words)
    return t in _BARE_NEG and not (lang == "en" and t in ("no", "nao", "nunca", "jamas"))


def _level(toks, i, lang):
    items, ops = [], []
    n_comma = 0
    while i < len(toks):
        kind, val = toks[i]
        if kind == ")":
            break
        if kind in ("AND", "OR"):
            ops.append(kind)
            i += 1
            continue
        if kind == ",":
            n_comma += 1
            i += 1
            continue
        if kind == "(":
            node, i = _level(toks, i + 1, lang)
            if i >= len(toks) or toks[i][0] != ")":
                raise Abstain("unbalanced parentheses")
            i += 1
            items.append(node)
            continue
        # a text chunk; it may be a bare negation applying to a following group
        if i + 1 < len(toks) and toks[i + 1][0] == "(" and _is_neg_only(val, lang):
            node, j = _level(toks, i + 2, lang)
            if j >= len(toks) or toks[j][0] != ")":
                raise Abstain("unbalanced parentheses")
            items.append(("not", node))
            i = j + 1
            continue
        items.append(_atom(val, lang))
        i += 1
    kinds = set(ops)
    if not items:
        raise Abstain("empty")
    if len(items) == 1 and not kinds and not n_comma:
        return items[0], i
    if len(kinds) > 1:
        raise Abstain("mixed and/or without parentheses")
    if not kinds:
        raise Abstain("a comma list without a connective")
    total = len(ops) + n_comma
    if len(items) < 2 or total not in (len(items) - 1, len(items)):          # `A and B`, `A, B and C`, `A, B, and C`
        raise Abstain("malformed list")
    return ("and" if "AND" in kinds else "or", items), i


def _parse_bool(words, lang):
    s = " ".join(words)
    for p in _SCOPE_NEG:
        if s.startswith(p + " "):
            return ("not", _parse_bool(s[len(p) + 1:].split(), lang))
    toks = _tokens(s, lang)
    if not toks:
        raise Abstain("empty")
    node, i = _level(toks, 0, lang)
    if i != len(toks):
        raise Abstain("unbalanced parentheses")
    return node


def _find(words, phrases):
    """Earliest top-level (parenthesis depth 0) occurrence of any phrase: (index, phrase) or None; longest phrase wins at a position."""
    depth = 0
    for i, w in enumerate(words):
        if w == "(":
            depth += 1
        elif w == ")":
            depth -= 1
        elif depth == 0:
            best = None
            for p in phrases:
                if tuple(words[i:i + len(p)]) == p and (best is None or len(p) > len(best)):
                    best = p
            if best:
                return i, best
    return None


def _split_top(words, sep_words):
    depth = 0
    for i, w in enumerate(words):
        if w == "(":
            depth += 1
        elif w == ")":
            depth -= 1
        elif depth == 0 and w in sep_words:
            return i
    return None


def _parse_sentence(words, lang):
    if not words:
        raise Abstain("empty sentence")
    all_if = _IF + _ONLYIF + _UNLESS + _IFF
    if any(" ".join(words).startswith(p + " ") for p in _SCOPE_NEG) and _find(words, all_if):
        raise Abstain("a clause-level negation before a conditional: ambiguous scope")
    # prefix forms: `if X, Y` / `unless X, Y`
    for p in sorted(_IF + _UNLESS, key=len, reverse=True):
        if tuple(words[:len(p)]) == p:
            rest = words[len(p):]
            k = _split_top(rest, (",",) + _THEN)
            if k is None:
                raise Abstain("a prefix condition without a comma")
            ante, cons = rest[:k], rest[k + 1:]
            if not ante or not cons:
                raise Abstain("empty antecedent or consequent")
            if _find(ante, all_if) or _find(cons, all_if):
                raise Abstain("nested conditionals")
            x, y = _parse_bool(ante, lang), _parse_bool(cons, lang)
            return ("imp", ("not", x), y) if p in _UNLESS else ("imp", x, y)
    # mid forms: `Y if X`, `Y only if X`, `Y unless X`, `Y if and only if X`
    for group, kind in ((_IFF, "iff"), (_ONLYIF, "onlyif"), (_UNLESS, "unless"), (_IF, "if")):
        hit = _find(words, group)
        if hit:
            i, p = hit
            # an earlier hit of a different group wins (e.g. `only if` contains `if`): take the earliest overall
            earliest = min((h for h in (_find(words, g) for g in (_IFF, _ONLYIF, _UNLESS, _IF)) if h), key=lambda h: (h[0], -len(h[1])))
            if earliest[0] != i or len(earliest[1]) != len(p):
                continue
            ys, xs = words[:i], words[i + len(p):]
            while ys and ys[-1] == ",":
                ys = ys[:-1]
            if not ys or not xs:
                raise Abstain("empty side of a conditional")
            if _find(xs, all_if) or _find(ys, all_if):
                raise Abstain("nested conditionals")
            y, x = _parse_bool(ys, lang), _parse_bool(xs, lang)
            return {"iff": ("iff", y, x), "onlyif": ("imp", y, x), "unless": ("imp", ("not", x), y), "if": ("imp", x, y)}[kind]
    return _parse_bool(words, lang)


def _sentences(text):
    out, cur, depth = [], [], 0
    for w in text.split():
        if w == "(":
            depth += 1
        elif w == ")":
            depth -= 1
        stripped = w
        end = False
        while stripped and stripped[-1] in ".;!?":
            stripped, end = stripped[:-1], True
        if stripped:
            cur.append(stripped)
        if end and depth == 0:
            if cur:
                out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def parse(text: str, lang: str | None = None):
    check_size(text)
    t = _norm(text)
    lang = lang or _lang(t)
    sents = _sentences(t)
    if not sents:
        raise Abstain("empty text")
    nodes = [_parse_sentence(s, lang) for s in sents]
    return nodes[0] if len(nodes) == 1 else ("and", nodes)


def _atoms(node, acc):
    k = node[0]
    if k == "atom":
        acc.add(node[1])
    elif k == "not":
        _atoms(node[1], acc)
    elif k in ("and", "or"):
        for c in node[1]:
            _atoms(c, acc)
    else:
        _atoms(node[1], acc)
        _atoms(node[2], acc)
    return acc


def _eval(node, env):
    k = node[0]
    if k == "atom":
        return env[node[1]]
    if k == "not":
        return not _eval(node[1], env)
    if k == "and":
        return all(_eval(c, env) for c in node[1])
    if k == "or":
        return any(_eval(c, env) for c in node[1])
    if k == "imp":
        return (not _eval(node[1], env)) or _eval(node[2], env)
    return _eval(node[1], env) == _eval(node[2], env)


def _show(node):
    k = node[0]
    if k == "atom":
        return node[1]
    if k == "not":
        return f"NOT({_show(node[1])})"
    if k in ("and", "or"):
        return "(" + f" {k.upper()} ".join(_show(c) for c in node[1]) + ")"
    return f"({_show(node[1])} {'->' if k == 'imp' else '<->'} {_show(node[2])})"


def _actions(node, out):
    """Atoms in ACTION position, in order: the consequent of a conditional, or the clauses of a plain sentence. The antecedent is a boolean condition, so its order never matters."""
    k = node[0]
    if k == "atom":
        out.append(node[1])
    elif k == "not":
        _actions(node[1], out)
    elif k in ("and", "or"):
        for c in node[1]:
            _actions(c, out)
    elif k == "imp":
        _actions(node[2], out)
    else:
        _actions(node[1], out)
    return out


def logic_compare(a: str, b: str) -> dict:
    """See the module docstring. Never raises on a text it cannot read: it abstains."""
    try:
        la, lb = _lang(_norm(a)), _lang(_norm(b))
        lang = la if la == lb else None
        if lang is None:
            raise Abstain("the two texts do not look like the same language")
        fa, fb = parse(a, lang), parse(b, lang)
    except Abstain as e:
        return {"verdict": "ABSTAIN", "reason": str(e)}
    except Exception as e:                                                   # noqa: BLE001 — fail closed
        return {"verdict": "ABSTAIN", "reason": f"not analysed: {type(e).__name__}"}
    aa, ab = _atoms(fa, set()), _atoms(fb, set())
    if aa != ab:
        return {"verdict": "ABSTAIN", "reason": "the clauses differ (the engine only compares texts that reuse the same clauses)", "only_in_a": sorted(aa - ab), "only_in_b": sorted(ab - aa)}
    atoms = sorted(aa)
    if len(atoms) > MAX_ATOMS:
        return {"verdict": "ABSTAIN", "reason": f"more than {MAX_ATOMS} clauses"}
    for bits in itertools.product((False, True), repeat=len(atoms)):
        env = dict(zip(atoms, bits))
        if _eval(fa, env) != _eval(fb, env):
            return {"verdict": "DIFFERENT_LOGIC", "atoms": atoms, "counterexample": env, "formula_a": _show(fa), "formula_b": _show(fb),
                    "a_holds": _eval(fa, env), "b_holds": _eval(fb, env)}
    sa, sb = _actions(fa, []), _actions(fb, [])
    if (len(sa) >= 2 or len(sb) >= 2) and sa != sb:
        return {"verdict": "ABSTAIN", "reason": "the order of the actions may matter (`fetch X and generate Y` is not `generate Y and fetch X`)", "order_a": sa, "order_b": sb}
    return {"verdict": "EQUIVALENT_LOGIC", "atoms": atoms, "formula_a": _show(fa), "formula_b": _show(fb)}
