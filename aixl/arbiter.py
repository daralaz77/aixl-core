"""Arbiter protocol helpers (AIXL 0.5, ADR-018): the audit layer around a full-text LLM arbiter.

WHY this exists (docs/EVIDENCE.md): for open-domain text the measured way to decide "do these two instructions mean the
same?" is a strict full-text arbiter — two independent judges, "same" only if BOTH say SAME. Its errors are systematic
(the same pair wrong on every run) and the verdict of a single pair can flip between runs (Sonnet 1.2 %, Haiku 6.1 %, the
2-of-2 1.2 %), so a decision must be STORED and reused, never re-derived. This module provides exactly that, and nothing else:

* `rules_text()` / `rules_id()` — the versioned arbiter rules (`aixl/resources/arbiter_rules_v1.txt`); the id is the sha256 of the bytes.
* `consensus(verdicts)` — SAME only if every judge says SAME (and there are at least two for `ok`); DIFFERENT if any says DIFFERENT.
* `parse_judge_lines(text, expected_ids)` — validates a judge's `id<TAB>verdict<TAB>reason` output; reports missing/invalid ids
  (one dropped line in 410 judgments was observed, so callers need a retry path).
* `DecisionMemo` — append-only JSONL of decisions keyed by (texts, rules id, judge names); texts are stored only as hashes unless asked.
* `decide(a, b, judges, memo)` — runs the judges (CALLABLES supplied by the caller: no provider is imported here, the core never
  calls an LLM), applies consensus, records `sanitize_input` findings for audit, stores and reuses the decision.

It does not call any model, does not judge anything itself and does not execute any action. Judge quality is the caller's
responsibility; the evidence in EVIDENCE.md is for Sonnet 5/Haiku 4.5-class judges under `rules_v1.txt` on ES/EN/PT instructions."""
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field

from aixl.core.normalizer import sanitize_input

VERDICTS = ("SAME", "DIFFERENT", "UNSURE")
from aixl.resources import path as _resource  # noqa: E402

_RULES_PATH = _resource("arbiter_rules_v1.txt")


def rules_text() -> str:
    with open(_RULES_PATH, encoding="utf-8") as fh:
        return fh.read()


def rules_id() -> str:
    """sha256 (16 hex) of the exact rules bytes: any edit to the rules changes the id, so stored decisions are never reused across rule changes."""
    with open(_RULES_PATH, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def _h(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def pair_key(a: str, b: str, judges, rules: str | None = None) -> str:
    """Key of a decision. ORDERED on purpose (a, b) and computed on the RAW texts: a homoglyph/zero-width variant is a different pair,
    and whether the judges are symmetric in (a, b) was not measured. Judge names are part of the key (sorted)."""
    payload = json.dumps([_h(a), _h(b), rules or rules_id(), sorted(judges)], ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_verdict(raw: str) -> str | None:
    v = (raw if isinstance(raw, str) else "").strip().upper()          # a judge returning a non-string is an INVALID answer, never a crash
    return v if v in VERDICTS else None


def consensus(verdicts: dict) -> dict:
    """verdicts: {judge_name: raw verdict}. Returns {"verdict": SAME|DIFFERENT|UNSURE, "ok": bool, "invalid": [judges]}.
    SAME only if at least TWO judges answered validly and ALL say SAME; DIFFERENT as soon as one says DIFFERENT (even with a single judge: a
    dissent always blocks "same"); otherwise UNSURE. `ok` is False when fewer than two valid judges answered or any answer was invalid."""
    norm = {j: normalize_verdict(v) for j, v in verdicts.items()}
    invalid = sorted(j for j, v in norm.items() if v is None)
    valid = [v for v in norm.values() if v is not None]
    if "DIFFERENT" in valid:
        verdict = "DIFFERENT"
    elif len(valid) >= 2 and not invalid and all(v == "SAME" for v in valid):
        verdict = "SAME"                                     # "same" needs at least TWO valid judges, all SAME (single judges erred; the 2-of-2 did not)
    else:
        verdict = "UNSURE"
    return {"verdict": verdict, "ok": len(valid) >= 2 and not invalid, "invalid": invalid}


def parse_judge_lines(text: str, expected_ids) -> dict:
    """Validate a judge's output (`id<TAB>verdict<TAB>reason`, one line per input). Returns
    {"verdicts": {id: verdict}, "missing": [ids absent], "invalid": [ids with a verdict outside SAME/DIFFERENT/UNSURE], "unexpected": [ids not asked]}."""
    expected = list(expected_ids)
    got, invalid, unexpected = {}, [], []
    for line in (text or "").splitlines():
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 2:
            continue
        i, v = parts[0].strip(), normalize_verdict(parts[1])
        if i not in expected:
            unexpected.append(i)
        elif v is None:
            invalid.append(i)
        else:
            got[i] = v
    missing = [i for i in expected if i not in got and i not in invalid]
    return {"verdicts": got, "missing": missing, "invalid": invalid, "unexpected": unexpected}


class DecisionMemo:
    """Append-only JSONL memo of decisions. `get(key)` returns the stored record or None; `put(record)` appends it. Texts are stored only
    as sha256 unless `store_texts=True` (the memo may otherwise hold sensitive instructions)."""

    def __init__(self, path: str | None = None, store_texts: bool = False):
        self.path, self.store_texts, self._rows = path, store_texts, {}
        self.skipped = 0                          # unreadable lines found on load (e.g. a write cut short by a crash); they are only a cache miss
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                for n, line in enumerate(fh, 1):
                    if line.strip():
                        try:
                            r = json.loads(line)
                            self._rows[r["key"]] = r
                        except (ValueError, KeyError, TypeError):
                            self.skipped += 1
                            logging.getLogger("aixl.arbiter").warning("decision memo %s: line %d is unreadable and was skipped (the decision will be re-made)", path, n)

    def get(self, key: str):
        return self._rows.get(key)

    def put(self, record: dict) -> None:
        self._rows[record["key"]] = record
        if self.path:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    def __len__(self):
        return len(self._rows)


@dataclass
class Decision:
    verdict: str                      # SAME | DIFFERENT | UNSURE
    ok: bool                          # >= 2 valid judges agreed on the process (see consensus)
    per_judge: dict
    key: str
    from_memo: bool
    obfuscation: list = field(default_factory=list)   # sanitize_input findings on a and b, recorded for audit (not used to decide)
    retries: int = 0


def decide(a: str, b: str, judges: dict, memo: DecisionMemo | None = None, retries: int = 1) -> Decision:
    """judges: {name: callable(a, b) -> raw verdict string}. A stored decision for the same raw texts, rules id and judge names is returned
    without calling any judge. An invalid answer (not SAME/DIFFERENT/UNSURE, or an exception) is retried `retries` times, then counts as invalid
    (so the consensus is UNSURE and `ok` is False): the arbiter never invents a verdict."""
    key = pair_key(a, b, judges.keys())
    if memo is not None:
        hit = memo.get(key)
        if hit is not None:
            return Decision(hit["verdict"], hit["ok"], hit["per_judge"], key, True, hit.get("obfuscation", []), hit.get("retries", 0))
    per_judge, used = {}, 0
    for name, fn in judges.items():
        raw = None
        for attempt in range(retries + 1):
            try:
                raw = fn(a, b)
            except Exception:                                  # noqa: BLE001 — a failing judge is an invalid answer, never a verdict
                raw = None
            if normalize_verdict(raw) is not None:
                break
            used += attempt < retries
        per_judge[name] = normalize_verdict(raw) or "INVALID"
    c = consensus(per_judge)
    obf = sorted(set(sanitize_input(a)[1]) | set(sanitize_input(b)[1]))
    d = Decision(c["verdict"], c["ok"], per_judge, key, False, obf, used)
    if memo is not None:
        rec = {"key": key, "verdict": d.verdict, "ok": d.ok, "per_judge": per_judge, "rules_id": rules_id(),
               "a_sha256": _h(a), "b_sha256": _h(b), "obfuscation": obf, "retries": used, "ts": int(time.time())}
        if memo.store_texts:
            rec["a"], rec["b"] = a, b
        memo.put(rec)
    return d


@dataclass
class Layered:
    """Result of `layered_decide`: `verdict` SAME | DIFFERENT | UNSURE, `source` which layer decided (deterministic | arbiter | none)."""
    verdict: str
    source: str
    deterministic: str                      # compare_verified verdict that routed the pair
    arbiter: "Decision | None" = None
    reason: str = ""


def layered_decide(a: str, b: str, judges: dict, memo: "DecisionMemo | None" = None, retries: int = 1) -> Layered:
    """Deterministic proof first, the full-text arbiter for everything else.

    1. `compare_verified` EQUIVALENT (complete on both sides, no connective conflict) -> SAME without a judge.
    2. anything else -> `decide()`: SAME only when EVERY judge says SAME (>= 2), DIFFERENT if any says DIFFERENT, else UNSURE.
    A deterministic NOT_EQUIVALENT is NOT final and NOT a veto: measured on 600 labelled pairs of other authors it is right only ~50 % of the
    time (it means "not proven equal": paraphrase, cross-language, vocabulary), so using it as a verdict destroyed the arbiter's recall
    (13/54 proven SAME vs 52/54 in benchmarks/layered_eval.py). It is reported in `deterministic` as a hint for the audit trail.
    The deterministic layers never produce SAME without proof. Judges are caller-supplied callables (no provider is imported here)."""
    from aixl.api.service import compare_verified
    d = compare_verified(a, b)
    v = d.get("verdict") or "INCONCLUSIVE"
    if v == "EQUIVALENT" and d.get("verified"):
        return Layered("SAME", "deterministic", v, None, "proved equal over a completely accounted vocabulary")
    arb = decide(a, b, judges, memo, retries)
    if arb.verdict == "SAME" and arb.ok:
        return Layered("SAME", "arbiter", v, arb, "no deterministic proof; every judge says SAME")
    if arb.verdict == "DIFFERENT":
        return Layered("DIFFERENT", "arbiter", v, arb, "a judge says DIFFERENT")
    return Layered("UNSURE", "none", v, arb, "judges not unanimous or invalid")
