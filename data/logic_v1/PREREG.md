# Preregistration — aixl.logic (propositional-skeleton equivalence) on a FRESH set (2026-10-30), evaluated ONCE

Why: the arbiter (and the comparator) mislabelled logic-structure rewrites — a double negation (`No es cierto que no debas X` = `Debes X`) came out as a false SAME in the project's own data, and the closed-vocabulary comparator
compares condition TEXT, not condition STRUCTURE. A small decision procedure can PROVE or REFUTE equivalence of the logical arrangement when two texts reuse the same clauses. Method of the engine: `aixl/logic.py` (parse into a boolean formula
over clauses, truth table over at most 10 clauses; abstain on anything it cannot read, on mixed and/or without parentheses, on nested conditionals, on clauses that differ, on a changed ORDER of actions, on a negation that crosses a modal).
Two real defects were found and fixed BEFORE this freeze using older, independent labelled pairs (not this data): action order (`fetch X and generate Y` != `generate Y and fetch X`) and negation across a modal (`not necessary to restart` != `necessary not to restart`).
On those older pairs the engine gives 0 false EQUIVALENT_LOGIC and 0 false DIFFERENT_LOGIC (55 DIFFERENT_LOGIC and 11 EQUIVALENT_LOGIC correct; the rest abstain). Code frozen by hash BEFORE the data exist (FREEZE.json).
Authors: THREE models (Opus -> out_A, Sonnet -> out_B, Haiku -> out_C), NOT given the repository, the code or any previous data. Each writes 60 fresh pairs (es 18, en 18, pt 24): 30 EQUIVALENT and 30 DIFFERENT. In every pair BOTH texts reuse the SAME
clauses, copied word for word; only the logical wording and arrangement change (this is the engine's declared scope, so the set tests the engine where it claims to work, and COVERAGE tells how often real rewrites stay inside it).
Subtypes — EQUIVALENT: de_morgan, double_negation, conditional_order (`if X, Y` = `Y if X`), contrapositive, unless_as_if_not, distribution, commutation_of_conditions. DIFFERENT: converse, only_if_vs_if, regrouped_and_or (parentheses), negation_scope, and_or_swap,
dropped_negation, unless_vs_if.
Fields: `a`, `b`, `label` (EQUIVALENT|DIFFERENT), `subtype`, `lang`. Outputs are written before anyone reads them; only line counts are reported back.
Hypotheses (decided now):
 L1  false EQUIVALENT_LOGIC (label DIFFERENT) = 0 of 90   (one is a failure: the engine must never prove a false equivalence)
 L2  false DIFFERENT_LOGIC (label EQUIVALENT) <= 3 of 90
 L3  coverage: pairs with a verdict (not ABSTAIN) >= 50 % of 180
 L4  accuracy among the pairs with a verdict >= 95 %
 L5  older labelled pairs (every set under data/): 0 false EQUIVALENT_LOGIC and 0 false DIFFERENT_LOGIC (checked before the freeze: 0 / 0)
Reported regardless: coverage and errors per subtype and language, the histogram of abstention reasons, every wrong verdict, and the baselines on the same pairs: `compare_verified` (how many EQUIVALENT pairs it proves, how many DIFFERENT pairs it calls
EQUIVALENT) and `relay_check` (how many DIFFERENT pairs it flags, how many EQUIVALENT pairs it flags). A failing hypothesis is reported, not repaired; no tuning after reading.
