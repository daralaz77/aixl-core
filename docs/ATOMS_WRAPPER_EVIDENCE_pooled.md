# AIXL 0.4 LLM wrapper with abstention — pooled blind3 + blind4 (benchmarks/atoms_wrapper_eval.py pooled)

prompt id `ea45a318912c` (guide + registry 0.3.0); 300 unseen texts; two independent calls per text (Sonnet, Opus).

Parse/validation of the NEW calls: Sonnet valid 299/300, Opus valid 299/300 (invalid or missing: 1 / 1).

## Single call vs references (agreement with an independent annotation of the same text; mean over the two references)
| call | valid n | agreement with references |
|---|---|---|
| new Sonnet | 299 | exact 0.343 | F1 0.821 | core 0.811 |
| new Opus | 299 | exact 0.411 | F1 0.855 | core 0.853 |

## Wrapper, policy `exact`: ACCEPT 101 / 300 (33.7%), ABSTAIN 197, invalid-call 2
| subset | n | agreement of the accepted/first graph with references |
|---|---|---|
| accepted | 101 | exact 0.648 | F1 0.919 | core 0.920 |
| abstained (first call's graph, for contrast) | 197 | exact 0.188 | F1 0.772 | core 0.760 |

Accepted graphs identical to at least one reference: 83/101 (82.2%); identical to BOTH references where the references agree: 48/57.

## Wrapper, policy `core`: ACCEPT 181 / 300 (60.3%), ABSTAIN 117, invalid-call 2
| subset | n | agreement of the accepted/first graph with references |
|---|---|---|
| accepted | 181 | exact 0.464 | F1 0.876 | core 0.921 |
| abstained (first call's graph, for contrast) | 117 | exact 0.158 | F1 0.744 | core 0.698 |

Accepted graphs identical to at least one reference: 112/181 (61.9%); identical to BOTH references where the references agree: 56/79.
Accepted by core agreement only (auxiliary links differ): 80

Context: the two references agree with each other at: exact 0.370 | F1 0.835 | core 0.825
