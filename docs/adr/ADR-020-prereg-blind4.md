# Pre-registration — wrapper replication on blind4 (written 2026-10-05 BEFORE any blind4 text, call or annotation exists)

Protocol identical to ADR-020 / blind3: 150 new texts (author: Sonnet this time; blind3 was written by Opus), two independent wrapper calls per text (Sonnet, Opus, from `build_prompt`, prompt id unchanged), references = two independent annotations (Sonnet, Opus) read from the guide on disk. No change to code, guide, registry or prompt between blind3 and blind4; nothing is tuned on blind4.
Hypotheses (declared success criteria; a failure is reported as such):
* H1 format: ≥ 98 % of responses valid.
* H2 `core` policy: acceptance between 55 % and 80 %; accepted core F1 ≥ 0.88 against the references AND at least 0.15 above the abstained subset's core F1.
* H3 `exact` policy: accepted exact-graph agreement with references ≥ 0.50 and at least 0.25 above the abstained subset.
* H4 single-call baselines are below the accepted subset in core F1 (the filter adds something).
Comparison to blind3 is descriptive (different texts, different author). If H2 or H3 fails, the ADR-020 claim is downgraded to "not replicated".
