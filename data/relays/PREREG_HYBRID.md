# Preregistration — hybrid (relay_check as evidence for the 2-of-2 arbiter), 2026-10-22, evaluated ONCE

Pairs: the 360 (source, relay) pairs of data/relays (120 sources x {faithful_light, faithful_heavy, corrupted}); label SAME for the two faithful kinds, DIFF for corrupted.
`judge_key.json` (id -> label/kind) is NOT shown to the judges. Judges: Sonnet and Haiku, each reads ONLY the arbiter rules (rules_v1.txt) and (id, a, b) lines, 4 chunks of 90, TSV `id<TAB>SAME|DIFFERENT|UNSURE<TAB>reason`.
Arbiter = 2-of-2 (SAME only if both say SAME; DIFFERENT if any says DIFFERENT; else UNSURE) — aixl.arbiter.consensus, unchanged.

Arms (decided now):
 A  arbiter alone
 B  hybrid-hard: SAME from the arbiter is downgraded to ESCALATE when `relay_check` raises a violation in a HARD-FACT family — NUMBER, DATE, WEEKDAY, CLOCK, NAME,
    COMPARATOR, QUANTITY, UNIT, DAY_OF_MONTH (digits, dates, names, bounds: facts a rewording cannot legitimately change). Chosen by principle, before any judge output exists.
 C  hybrid-all: downgrade on ANY relay_check violation (reference only; expected to destroy faithful recall on reworded relays)
Metrics: on corrupted: share accepted as SAME (false SAME) per arm; on faithful (light and heavy): share proven SAME (kept) per arm; ESCALATE counts as not-SAME.
Hypotheses:
 H5  arm A false-SAME on corrupted is >= 5 % (otherwise there is nothing for the hybrid to fix; reported either way)
 H6  arm B reduces arm A's false-SAME by >= 30 % relative (or to 0)
 H7  arm B keeps >= 97 % of arm A's proven-SAME on faithful relays (loses <= 3 %)
 H8  arm C loses > 10 % of arm A's proven-SAME on faithful_heavy (confirms why the full veto is not offered)
Frozen: code hashes in FREEZE_hybrid.json; the judge inputs hash in JUDGE_IN_SHA256.txt. No family set, threshold or arm is changed after reading the judgments.
