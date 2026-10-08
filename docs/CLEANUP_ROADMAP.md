# Camino de limpieza y rendimiento — aixl-core (revisión 2026-10-08)

Revisión con mediciones (ruff, vulture, cProfile, pytest --durations, grafo de imports). No se cambió código al hacerla. Línea base: **1093 tests pasan en 14.6 s**.

## 1. Veredicto en tres líneas
1. **El rendimiento no es el problema.** `to_graph` ≈ 0.4 ms/texto, el gate completo ≈ 0.8 ms/texto, importar el traductor 59 ms. Optimizar velocidad no da valor visible; el dinero está en los tokens, no en la CPU.
2. **El problema es mantenibilidad:** código muerto y ramas inalcanzables, acoplamiento por nombres privados, un traductor "legacy" del que depende el nuevo, y 36 de 60 scripts de benchmarks que ejecutan el experimento al importarse (me pasó dos veces en esta sesión).
3. **Hay que proteger la semántica antes de tocar nada:** una prueba de caracterización (huellas de las salidas) hace que cualquier refactor sea demostrablemente neutro.

## 2. Hallazgos con evidencia
| # | Hallazgo | Evidencia | Riesgo si se ignora |
|---|---|---|---|
| H1 | Sin lint configurado ni en CI; 254 avisos en `aixl/` (135 autocorregibles) y 501 en benchmarks/tests | `ruff check aixl --statistics`; `tests.yml` solo corre pytest; sin `[tool.ruff]` | deuda crece sin freno |
| H2 | Ramas muertas / "cicatrices" en `aixl/atoms/extract.py` (757 líneas): `… if False else None`, `… and False`, `True if x or True else False`; 14 variables locales sin uso | vulture 100% de confianza en líneas 561, 627, 657, 721; ruff F841 | ocultan lógica que parece activa y no lo está |
| H3 | `gate.py` importa 8 nombres privados (`_evidence_tokens`, `_ALLTOK`, `_norm`, `_CLOSED`, `_forms`, `_CONCEPT`, `_known`, `_stem`) de `completeness`/`lexicon_gaps` | `aixl/gate.py:10-12` | cualquier renombre interno rompe el gate en silencio |
| H4 | Trabajo duplicado: `translate_gated` llama `check_completeness` y luego `strict_complete` lo vuelve a llamar | `gate.py` | 2× el costo de la parte más cara del gate |
| H5 | `aixl/translators/natural_to_semantic.py` (0.3) depende de `aixl/legacy02/…` (6 tablas + `analyze`) y otros 6 módulos de `core` importan legacy02 | grafo de imports | "legacy" no se puede borrar; dos fuentes de verdad para `DATA_RX`, `ENTITY_RX`, `MONTHS` |
| H6 | 36 de 60 scripts de `benchmarks/` sin `if __name__ == "__main__"`; el cargador de transcripciones está copiado en 8 | grep | importar un módulo dispara minutos de cómputo; correcciones hay que repetirlas 8 veces |
| H7 | Claves duplicadas en diccionarios (mismo valor): `todo`, `caracteres`, `cliente`, `ingles`; sets con duplicados; `derive_goal` redefinida | ruff F601/B033/F811 | ruido; un cambio futuro de valor en una sola copia sería un bug silencioso |
| H8 | Parámetro muerto `min_sim_fp` en `translate_gated`; imports sin uso (`Callable`, `type_of`, …) | vulture/ruff F401 | confunde a quien lee la API |
| H9 | Micro-rendimiento: 41 473 búsquedas `re._compile` por 110 textos (regex construidas en la llamada), `strip_accents` con generador (66 659 pasos/110 textos), `canonical()` recalculada 656 veces/110 textos | cProfile | solo velocidad; irrelevante en absoluto |
| H10 | Suite: 14.6 s, ~5 s son 3 tests de MCP con subprocesos reales | `--durations` | lento en CI, no crítico |
| H11 | `aixl/adapters/` sin referencias desde `aixl/`, `cli.py` ni tests (stubs A2A/REST/GraphQL) | grep | posible código muerto, a confirmar |
| H12 | Tres representaciones semánticas conviven (`core/`, `semantic/` 1462 líneas, `atoms/` 1636 líneas) | LOC + imports (`semantic` solo lo usan `hybrid_protocol`, `atoms/extract`, `cli`) | decisión de arquitectura pendiente |

## 3. El camino (de menor a mayor riesgo; cada fase tiene su puerta)
**Regla de oro:** una fase solo se da por terminada si (a) los 1093 tests pasan, (b) la prueba de caracterización de la Fase 0 da salida idéntica, (c) se hace commit propio y reversible.

**Fase 0 — Red de seguridad (½ día).**
- Prueba de caracterización: guardar `fingerprint`, forma compacta y modo del gate para los ~228 textos del dev set y un subconjunto fijo de mensajes reales; test que falla si cambia cualquier salida.
- `[tool.ruff]` en `pyproject.toml` con reglas F/E9/B/I/RUF; paso de lint en CI en modo *informativo*.
- Script de rendimiento (`benchmarks/perf_baseline.py`) que imprime ms/texto, import y suite.
- *Puerta:* la prueba de caracterización pasa sobre el código actual.

**Fase 1 — Mecánica sin riesgo (½ día).** `ruff --fix` solo con reglas seguras (imports sin uso/ordenados, claves y elementos duplicados, redundancias): ≈135 correcciones. *Puerta:* regla de oro. Resuelve H7, parte de H1 y H8.

**Fase 2 — Código muerto (1 día).** Eliminar ramas `if False`/`and False`, variables sin uso y condiciones insatisfacibles de `atoms/extract.py` (H2), `min_sim_fp`, la redefinición de `derive_goal`; confirmar y retirar `aixl/adapters/` si nada lo usa (H11). Cada eliminación se justifica con la salida de vulture o ruff. *Puerta:* regla de oro; el diff debe ser solo borrado.

**Fase 3 — API pública de cobertura (½ día).** Mover `strict_complete` y sus ayudantes a `aixl/core/completeness.py` con una función pública única (`coverage(text, graph) -> {complete, strict, …}`) que calcula todo en una pasada; `gate.py` deja de importar privados. Resuelve H3 y H4. Medido: `strict_complete` ocupa el 44% del tiempo del gate (0.040 s de ~0.09 s por 110 textos) y repite `check_completeness`; eliminar la repetición ahorraría del orden del 20% del gate (estimación, no medida tras el cambio). *Puerta:* regla de oro + tests de `gate`.

**Fase 4 — Higiene de benchmarks (½ día).** `benchmarks/_corpus.py` con el cargador de transcripciones y de mensajes reales; guardas `__main__` en los 36 scripts; los 8 duplicados importan del módulo común. Resuelve H6. *Puerta:* ningún `import benchmarks.x` ejecuta código; `python -m benchmarks.x` da el mismo resultado que antes.

**Fase 5 — Rendimiento (opcional, ½ día).** Compilar regex a nivel de módulo, `lru_cache` en `strip_accents`/`normalize`, memoizar `canonical()` por grafo (H9); marcar los 3 tests de MCP como `slow` (H10). Solo se acepta si `perf_baseline` muestra mejora medible; la ganancia esperada es una estimación (no medida), sobre una base de 0.4 ms/texto, es decir, sin impacto práctico. *Puerta:* regla de oro + mejora medida.

**Fase 6 — Arquitectura (decisión tuya, 3–5 días).** (a) Mover a `core/ontology` las tablas de `legacy02` que el traductor 0.3 aún usa y dejar `legacy02` como cascarón congelado, luego borrar sus traductores duplicados (H5). (b) Decidir el destino de `semantic/` y `atoms/` (H12): consolidar, aislar como paquetes opcionales o archivar; requiere un ADR. *Puerta:* ADR aprobado + regla de oro + benchmarks de equivalencia sin regresión.

## 4. Orden recomendado y estimación
Fases 0 → 1 → 2 → 3 → 4 en ≈3 días de trabajo dejan el código sin muertos, sin acoplamiento privado y sin experimentos al importar. La Fase 5 es opcional y la 6 es una decisión de producto/arquitectura, no de limpieza.

## 5. Qué NO hacer
- No reescribir `atoms/extract.py` ni el traductor: tienen cobertura por tests golden y reescribirlos arriesga la equivalencia medida.
- No optimizar rendimiento antes de la Fase 0: sin red de seguridad no se puede demostrar que el resultado no cambió.
- No borrar `legacy02` antes de mover las tablas que aún se usan.
