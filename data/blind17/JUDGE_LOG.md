# Judge protocol log (blind17)
* Sonnet judge: one pass, TSV as requested (judge_sonnet.tsv, verbatim).
* Haiku judge: FIRST answer was a prose summary with no per-pair verdicts (invalid; arbiter retry path, `aixl.arbiter` docs: a dropped/invalid output is retried). The same agent was asked once to re-emit
  the 70 lines. Its second answer was a markdown table (not TSV) with one verdict per id; it is kept verbatim in judge_haiku_RAW_markdown.txt and mechanically converted to judge_haiku.tsv
  (ids and totals checked: 38 SAME / 32 DIFFERENT / 0 UNSURE, equal to the judge's own summary). No verdict was added or changed.
* Judges saw only rules_v1.txt and (id, a, b), in shuffled order; never labels, families or the semantic output.
