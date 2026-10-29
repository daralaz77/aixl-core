"""Evidence tier of a SAME claim, with the error rate MEASURED for that tier (not a probability, not calibrated for your traffic).

`claim_tier(verified, relay, votes)` -> {"tier", "false_same_measured", "n", "ci95", "scope"}.
Tiers: P  deterministic proof (`compare_verified` verified EQUIVALENT) | J+ every judge SAME and `relay_check` ok | J every judge SAME but `relay_check` flagged
| split judges disagree | N every judge says different | none no judge output.
The numbers come from `python -m benchmarks.risk_coverage` (blind17 + blind18, 115 pairs of other authors, judges Sonnet/Haiku, 2026-10-29): small samples, wide intervals, ES/EN/PT
open-domain text. Finding kept on purpose: `relay_check` ok does NOT make a unanimous SAME safer (J+ 1/18 vs J 1/36); the signal is the judges' agreement."""
_TABLE = {   # tier: (false-SAME count, n, (ci_low, ci_high) as fractions)
    "J+": (1, 18, (0.010, 0.258)), "J": (1, 36, (0.005, 0.142)), "split": (9, 11, (0.523, 0.949)), "N": (50, 50, (0.929, 1.0)),
}
SCOPE = "blind17+blind18 (115 labelled pairs, other authors, ES/EN/PT open domain); wide intervals; not calibrated on your traffic"


def claim_tier(verified: dict, relay: dict, votes) -> dict:
    """`votes`: the judges' verdicts, e.g. ["SAME", "SAME"]; empty/unknown entries count as no output."""
    vs = [str(v).strip().upper() for v in (votes or []) if str(v).strip()]
    if verified.get("equivalent") and verified.get("verified"):
        return {"tier": "P", "false_same_measured": 0.0, "n": None, "ci95": None, "scope": "deterministic proof inside the controlled vocabulary (0 false EQUIVALENT in 318 labelled DIFF pairs)"}
    if not vs:
        return {"tier": "none", "false_same_measured": None, "n": 0, "ci95": None, "scope": "no judge output: no claim of sameness can be made"}
    if set(vs) == {"SAME"}:
        t = "J+" if relay.get("ok") else "J"
    elif set(vs) <= {"DIFFERENT", "DIFF"}:
        t = "N"
    else:
        t = "split"
    k, n, ci = _TABLE[t]
    return {"tier": t, "false_same_measured": round(k / n, 3), "n": n, "ci95": ci, "scope": SCOPE}
