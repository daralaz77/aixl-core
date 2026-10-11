# Audit: "AIXL Evolution Engine 1.0" prompt vs aixl-core (2026-10-10)
Method: each Fase run against real code; only confirmed defects listed.

| Fase | Requisito | Estado |
|---|---|---|
| I/II auditoría + refactor mínimo | reglas duplicadas, símbolos ambiguos | no se halló duplicación nueva en esta pasada; sin refactor (principio: no reconstruir) |
| III/IV motor semántico, optimizador de tokens | flujo + AHORRO NETO | cubierto (graph, gate.py; ver V1_PROMPT_AUDIT.md: ahorro real rara vez) |
| V "símbolo desconocido no se interpreta con suposición silenciosa" | **DEFECTO CONFIRMADO → cerrado** | ver abajo |
| VI equivalencia con veredicto estructurado | cubierto (Verdict + relation5) | |
| VII/VIII evolución y autorreparación | cubierto por Evolution Engine/Genome (proyecto aparte) | |

## Defecto confirmado (Fase V)
`decode("... A:ANALYZE D:SALES N:NO_DELETE K:FORBID_DELETE")` devolvía un grafo con huella idéntica a la línea SIN prohibición:
el grafo solo sostiene una prohibición a través de su nodo de acción, así que `N:NO_x`/`K:FORBID_x` sin `A:x` se perdía en silencio.
Línea auto-generada nunca lo dispara (el traductor siempre añade la acción), pero un emisor externo sí.
Arreglo mínimo (`aixl_codec._check`): `ORPHAN_NEGATION` siempre; `UNKNOWN_ATOM_VALUE` solo con `strict=True`.
## Descartado con evidencia
Rechazar valores desconocidos por defecto rompió 16 tests (I:UNKNOWN legítimo, bug032 documentado como tolerancia deliberada) → opt-in.
## Limitación
Tolerar `A:FOOBAR` por defecto sigue siendo "suposición" parcial: se compara como no-equivalente, no se ejecuta como acción conocida. 1127 tests pasan.
