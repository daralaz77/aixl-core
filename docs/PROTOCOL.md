# AIXL 0.3 — Protocol specification

Scope: the **serialization** only. Meaning lives in the semantic graph ([SEMANTIC_MODEL.md](SEMANTIC_MODEL.md)); AIXL is one encoding
of it (the other is JSON). Changing this syntax must never change meaning.

## 1. Wire format
A message is one line of tokens separated by single spaces: `ATOM:VALUE ATOM:VALUE ...`.
* `ATOM` is one letter from the table below. Values contain no spaces unless double-quoted (`"a b"`; `\"` and `\\` escape inside quotes).
* **List atoms** hold comma-separated values (`A:SEND,DELETE`); an item containing a comma or space is quoted.
* **Scalar atoms** hold one value. A repeated scalar atom is an error; a repeated list atom is merged (union).
* `V:AIXL-0.3` is mandatory.
* The encoder emits atoms in a fixed canonical order: `V I A D E T L H Y N K F P G O`, so the same meaning always yields the same line.
* Parser tolerance (not part of what the encoder emits): a stray space after a comparator operator (`H:> .90`).

## 2. Atoms (as implemented)
| Atom | Field | Kind | Meaning |
|---|---|---|---|
| `V` | version | scalar | `AIXL-0.3` (encoder output); the parser also accepts `AIXL-0.2`; any other value → `ERROR:VERSION_MISMATCH` |
| `I` | intent | scalar | derived from the action (below) |
| `A` | actions | list | what is requested/forbidden/allowed |
| `D` | data | list | data objects (`SALES`, `DATASET`, aggregates `TOTAL_SALES` …) |
| `E` | entities | list | entities (`REPORT`, `PERSON`, `MODEL` …) |
| `T` | time | scalar | `Q1-2026`, `2026-03-15`, `TODAY`/relative tokens, ranges |
| `L` | location | list | hierarchical `VALLEDUPAR,CESAR,CO` |
| `K` | constraints | list | `QTY=100:RECORDS`, `FORBID_x`, `ALLOW_x`, `VISIBILITY=`, `BEFORE=`/`AFTER=`, `TIME_AT=`, `AGE>N:UNIT`, `SCOPE=`, `LIMIT=`, `WITHOUT=` … |
| `F` | conditions | list | `COUNT>100:RECORDS`, existence/containment, confidence thresholds |
| `P` | priority | scalar | priority words |
| `H` | confidence | scalar | extraction confidence (describes the extraction, **not** the meaning) |
| `Y` | references | list | `@ANA`, `#4` |
| `N` | negations | list | `NO_SEND` (always paired with `K:FORBID_SEND`) |
| `G` | goal | scalar | derived goal |
| `O` | output | list | `PDF`, `JSON`, `CSV`, `TABLE` … |

Intents (`REQUEST_ANALYSIS, REQUEST_COMPARISON, REQUEST_SEARCH, REQUEST_SUMMARY, REQUEST_GENERATION, REQUEST_TRANSLATION,
REQUEST_VALIDATION, REQUEST_EXECUTION, REQUEST_RETRIEVAL, REQUEST_TRANSFORMATION`, plus protocol-level `CAPABILITY_QUERY/RESPONSE`)
are **derived from the actions**, never free text. Actions (25): `ANALYZE COMPARE FIND SEARCH SUMMARIZE GENERATE CREATE CALCULATE
CHECK VALIDATE TRANSLATE GET RETRIEVE DELETE EXECUTE TRANSFORM CLASSIFY EXTRACT PREDICT UPDATE ENABLE DISABLE SEND INCLUDE EXCLUDE`.

## 3. Verified examples
Each line is checked against the real encoder by `tests/test_docs.py` (the docs cannot drift from the code).
```aixl-example
No envíes el informe. | V:AIXL-0.3 I:REQUEST_EXECUTION A:SEND E:REPORT N:NO_SEND K:FORBID_SEND
Analiza 100 registros. | V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE K:QTY=100:RECORDS
Elimina el reporte #4. | V:AIXL-0.3 I:REQUEST_EXECUTION A:DELETE E:REPORT Y:#4
Analiza las ventas de Q1 2026 en JSON. | V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE D:SALES T:Q1-2026 O:JSON
Envía el informe a Ana en PDF. | V:AIXL-0.3 I:REQUEST_EXECUTION A:SEND E:REPORT Y:@ANA O:PDF
Send the report to Ana as a PDF. | V:AIXL-0.3 I:REQUEST_EXECUTION A:SEND E:REPORT Y:@ANA O:PDF
```
(The last two lines show language independence: ES and EN produce the same line.)

## 4. Errors
`ERROR:INVALID_AIXL <detail>` — empty message, bad token, unknown atom, duplicate scalar atom, empty value, scalar with several values,
missing `V:`, unterminated quote. `ERROR:VERSION_MISMATCH <version>` — `V:` is neither `AIXL-0.2` nor `AIXL-0.3` (so `AIXL-0.2.5`–`0.2.7` are rejected explicitly). Both are `AixlError` (`.code`).

## 5. Determinism and round trip
Same text + same reference date ⇒ same line. `decode(encode(g))` reproduces the canonical form (round-trip 100 % on the dev set and the
blind sets, `full_canonical_roundtrip` in `benchmarks/blind_eval.py`). Relative times resolve against the system date unless a
`today` is passed (see §Conformance).

## Conformance with the master prompt
| Master prompt | Implementation | Note |
|---|---|---|
| §8 atom letters `F`=Format, `Y`=Condition, `H`=Context | `F`=conditions, `Y`=references, `H`=confidence, `O`=output | taxonomy inherited from the measured AIXL 0.2; §8 allows evolving it if documented — this is the documentation |
| §9 `I:REQUEST` | `I:REQUEST_EXECUTION` (etc.) | intent is derived from the action |
| §9 `T:TOMORROW` | `T:<ISO date>` | **deviation from §16/§35**: relative days/months/years resolve against the system date (or `today=`) at translation time; the *pair* compare resolves both sides consistently, but the AIXL line itself is date-anchored. Weeks are left unresolved on purpose. |
| §22 six statuses | `ComparisonResult.equivalent` + typed differences | `PARTIALLY_EQUIVALENT`/`CONTRADICTORY`/`AMBIGUOUS` are derived (benchmark mapping, `detect_*`), not a single status field |
| §32 REST endpoints | not implemented | Python API, CLI, MCP and A2A instead |
| §37 compatibility with 0.2/0.2.5–0.2.7 | 0.2 parser vendored (`aixl/legacy02`); accepts `AIXL-0.2` and `AIXL-0.3` | 0.2.5–0.2.7 and everything else are rejected explicitly (`VERSION_MISMATCH`), never silently accepted; 0.3-only atoms in a 0.2 reader are not negotiated (no capability handshake) |
| §52–§54 registry / handshake / negotiation of features | not implemented; message-level *negotiation* (disagreement resolution) is | see INTEROPERABILITY_GUIDE.md |
