# Audit: "AIXL 1.1 — Prompt Maestro" vs aixl-core (2026-10-10)

| Módulo | Requisito | Estado | Evidencia |
|---|---|---|---|
| 1, 2, 4, 6 | Fidelidad, normalización, canónica, round-trip | cubierto | semantic model + fingerprint + `validate/round_trip` (0.4.0) |
| 3 | 5 relaciones EQUIVALENT/COMPATIBLE/PARTIAL/CONTRADICTORY/UNDETERMINED | **AUSENTE → cerrado** (`aixl/relation5.py`, solo re-etiqueta el Verdict; nunca promueve a EQUIVALENT) | `tests/test_relation5.py` (9) |
| 5, 10 | Costo con overhead de protocolo, "NATURAL si no hay ahorro", ahorro estimado si no hay tokenizador real | cubierto (`aixl/gate.py`, auditoría v1.0) | ver V1_PROMPT_AUDIT.md |
| 7 | Handshake, fallback | cubierto | `aixl_negotiate*` |
| 8 | Registro de errores tipado (CASE_ID…VERSION, 10 tipos) | **AUSENTE → cerrado** (`ErrorRecord`, `append_jsonl`) | distingue FALSE_CONFIDENCE (inseguro) de EQUIVALENCE_ERROR (fallo seguro) |
| 9 | TRAIN/VALIDATION/TEST | cubierto (golden/blind sets) | |
| 11 | CHANGE_ID/APPROVAL_STATUS por cambio | parcial (ADRs + SEMANTIC_CHANGELOG) | no se añadió plantilla nueva |

## Hallazgo medido con los ejemplos del propio prompt
El comparador de reglas queda **INCONCLUSIVE (→ UNDETERMINED)** en los 3 ejemplos que el prompt da como canónicos:
ES↔EN "resume en cinco puntos", "traduce el texto al inglés"↔"Translate the text into English", y la prueba de contraste
"duplicados"/"que no estén duplicados". Es fallo seguro (nunca EQUIVALENT falso), pero significa que esos casos solo los resuelve el
árbitro LLM 2-de-2, no las reglas. COMPATIBLE se deriva solo cuando cada lado añade algo y nada choca; "resume" vs "traduce" cae en PARTIAL
(el motor lo ve como ADDITION), diferencia conocida con la etiqueta esperada.
