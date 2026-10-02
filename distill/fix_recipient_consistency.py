"""Deterministic fix for a real consistency bug found by spot-checking corpus_fresh.jsonl (2026-10-01):
the teacher model encoded recipient mentions ("a Marta", "al equipo de soporte", "al gerente", "a
finanzas"...) inconsistently -- only 44% got a proper Y:@NAME token, the rest dropped the recipient
or dumped literal text into F:. Worse, generate_fresh_texts.py's own RECIPIENTS table bundled two
DIFFERENT real-world referents (a person "Marta" and "the support team") into one language-variant
group, and similarly for "the manager" vs "finance" -- so there was never one unambiguous teacher
answer to agree on for every text in that group.

Since we control the generator and the exact literal phrase present in each text, this re-derives the
correct Y: token deterministically (no new API calls) instead of trusting the teacher's handling of
this one pattern: strips whatever Y:@X the teacher wrote plus any F: token that is just that recipient
phrase dumped as a literal, and inserts the single canonical, language-invariant Y: token for the real
entity actually named in the text.

usage: python distill/fix_recipient_consistency.py
Reads/overwrites distill/corpus_fresh.jsonl in place (prints a before/after consistency report).
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aixl.serialization import aixl_codec

# (phrase as it literally appears in generated text, lowercase) -> canonical Y: value
PHRASE_TO_CANONICAL = {
    " a marta": "@MARTA",
    " to marta": "@MARTA",
    " para marta": "@MARTA",
    " al equipo de soporte": "@SUPPORT_TEAM",
    " to the support team": "@SUPPORT_TEAM",
    " al gerente": "@MANAGER",
    " to the manager": "@MANAGER",
    " ao gerente": "@MANAGER",
    " a finanzas": "@FINANCE",
    " to finance": "@FINANCE",
}
# longest phrases first so "a marta" doesn't shadow a longer match (none overlap today, but safe)
ORDERED_PHRASES = sorted(PHRASE_TO_CANONICAL, key=len, reverse=True)

Y_TOKEN_RE = re.compile(r"\bY:[^\s]+")
F_TOKEN_RE = re.compile(r'\bF:[^\s]+')
A_TOKEN_RE = re.compile(r"\bA:[^\s]+")
N_TOKEN_RE = re.compile(r"\bN:[^\s]+")
K_TOKEN_RE = re.compile(r"\bK:[^\s]+")

SEND_VERBS = ["envia", "envía", "envie", "manda", "remite", "notifica", "avisa",
              "comparte con", "reenvía", "reenvia", "send", "notify", "alert",
              "forward", "share with", "dispatch", "relay", "compartilha"]


def strip_spurious_send(text: str, aixl: str):
    """Card rule (card_0.3.md line 36): only the sentence's own main verb decides A: -- a
    recipient mention is not a SEND verb, so A:SEND (and its N:NO_SEND/K:FORBID_SEND pair)
    must not appear unless the text actually contains a real send-verb synonym (line 32)."""
    low = text.lower()
    if any(v in low for v in SEND_VERBS):
        return aixl, False

    a_match = A_TOKEN_RE.search(aixl)
    if not a_match or "SEND" not in a_match.group(0)[2:].split(","):
        return aixl, False

    new_aixl = aixl

    def drop_value(token_re, m_text, value):
        items = [it for it in m_text.split(",") if it != value]
        return ",".join(items)

    a_items = a_match.group(0)[2:].split(",")
    a_items = [it for it in a_items if it != "SEND"]
    a_repl = ("A:" + ",".join(a_items)) if a_items else ""
    new_aixl = new_aixl[:a_match.start()] + a_repl + new_aixl[a_match.end():]

    n_match = N_TOKEN_RE.search(new_aixl)
    if n_match and "NO_SEND" in n_match.group(0)[2:].split(","):
        n_items = [it for it in n_match.group(0)[2:].split(",") if it != "NO_SEND"]
        n_repl = ("N:" + ",".join(n_items)) if n_items else ""
        new_aixl = new_aixl[:n_match.start()] + n_repl + new_aixl[n_match.end():]

    k_match = K_TOKEN_RE.search(new_aixl)
    if k_match and "FORBID_SEND" in k_match.group(0)[2:].split(","):
        k_items = [it for it in k_match.group(0)[2:].split(",") if it != "FORBID_SEND"]
        k_repl = ("K:" + ",".join(k_items)) if k_items else ""
        new_aixl = new_aixl[:k_match.start()] + k_repl + new_aixl[k_match.end():]

    return new_aixl, True


def canonical_for(text: str):
    low = text.lower()
    for phrase in ORDERED_PHRASES:
        if phrase in low:
            return PHRASE_TO_CANONICAL[phrase]
    return None


def fix_line(text: str, aixl: str):
    canonical = canonical_for(text)
    if canonical is None:
        return aixl, False  # no recipient clause in this text at all

    existing = Y_TOKEN_RE.search(aixl)
    already_correct = existing is not None and existing.group(0) == f"Y:{canonical}"

    new_aixl = aixl
    changed = False
    f_match = F_TOKEN_RE.search(new_aixl)
    if f_match:
        value = f_match.group(0)[2:]  # strip "F:"
        items = [it for it in value.split(",") if not (it.startswith('"') and it.endswith('"'))]
        if len(items) != value.count(",") + 1:  # at least one quoted-literal item was dropped
            replacement = ("F:" + ",".join(items)) if items else ""
            new_aixl = (new_aixl[:f_match.start()] + replacement + new_aixl[f_match.end():])
            changed = True
    if existing:
        if not already_correct:
            new_aixl = Y_TOKEN_RE.sub(f"Y:{canonical}", new_aixl, count=1)
            changed = True
    else:
        new_aixl = new_aixl.strip() + f" Y:{canonical}"
        changed = True

    new_aixl, send_changed = strip_spurious_send(text, new_aixl)
    changed = changed or send_changed

    new_aixl = re.sub(r"\s+", " ", new_aixl).strip()
    return new_aixl, changed


def main():
    path = os.path.join(ROOT, "distill", "corpus_fresh.jsonl")
    lines = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]

    n_had_recipient = 0
    n_changed = 0
    n_now_valid = 0
    n_broke = 0
    out_lines = []
    for d in lines:
        new_aixl, changed = fix_line(d["text"], d["aixl"])
        if canonical_for(d["text"]) is not None:
            n_had_recipient += 1
        if changed:
            n_changed += 1
            try:
                aixl_codec.decode(new_aixl)
                n_now_valid += 1
            except Exception as e:
                print(f"BROKE DECODE: {d['text']!r}\n  old: {d['aixl']!r}\n  new: {new_aixl!r}\n  err: {e}")
                n_broke += 1
                new_aixl = d["aixl"]  # keep the original rather than ship something unparseable
                n_changed -= 1
        out_lines.append({"text": d["text"], "aixl": new_aixl})

    with open(path, "w", encoding="utf-8") as out:
        for d in out_lines:
            out.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"texts with a recipient phrase: {n_had_recipient}/{len(lines)}")
    print(f"Y: token corrected/inserted: {n_changed} (decode still valid: {n_now_valid}, reverted due to break: {n_broke})")
    print(f"rewrote {path}")


if __name__ == "__main__":
    main()
