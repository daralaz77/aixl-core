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
| H4 | ~~Trabajo duplicado en el gate~~ **CORREGIDO en la Fase 3**: `strict_complete` llama a `check_completeness` con un texto DISTINTO (el original sin el verbo detectado), así que no había repetición exacta que eliminar. Medido tras mover el código: 0.635 vs 0.638 ms/texto, sin cambio. | `gate.py`, perf_baseline | ninguno: el valor de la fase es de acoplamiento, no de velocidad |
| H5 | `aixl/translators/natural_to_semantic.py` (0.3) depende de `aixl/legacy02/…` (6 tablas + `analyze`) y otros 6 módulos de `core` importan legacy02 | grafo de imports | "legacy" no se puede borrar; dos fuentes de verdad para `DATA_RX`, `ENTITY_RX`, `MONTHS` |
| H6 | 36 de 60 scripts de `benchmarks/` sin `if __name__ == "__main__"`; el cargador de transcripciones está copiado en 8 | grep | importar un módulo dispara minutos de cómputo; correcciones hay que repetirlas 8 veces |
| H7 | Claves duplicadas en diccionarios (mismo valor): `todo`, `caracteres`, `cliente`, `ingles`; sets con duplicados; `derive_goal` redefinida | ruff F601/B033/F811 | ruido; un cambio futuro de valor en una sola copia sería un bug silencioso |
| H8 | Parámetro muerto `min_sim_fp` en `translate_gated`; imports sin uso (`Callable`, `type_of`, …) | vulture/ruff F401 | confunde a quien lee la API |
| H9 | Micro-rendimiento: 41 473 búsquedas `re._compile` por 110 textos (regex construidas en la llamada), `strip_accents` con generador (66 659 pasos/110 textos), `canonical()` recalculada 656 veces/110 textos | cProfile | solo velocidad; irrelevante en absoluto |
| H10 | Suite: 14.6 s, ~5 s son 3 tests de MCP con subprocesos reales | `--durations` | lento en CI, no crítico |
| H11 | ~~`aixl/adapters/` sin uso~~ **REFUTADO en la Fase 2**: lo usan `tests/test_a2a_adapter.py` y `tests/test_mcp_adapter.py` y contiene los adaptadores MCP y A2A reales. Mi búsqueda inicial miró solo `aixl/` y el CLI, no los tests. | grep ampliado | ninguno: NO se retira |
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

## 6. Estado de ejecución
### Fase 0 — HECHA (2026-10-08)
- **Prueba de caracterización:** `benchmarks/characterization.py` + `tests/test_characterization.py` + `tests/golden/characterization.json`. Fija, para 243 textos (dev set + 25 casos borde; sin mensajes de usuario reales), el fingerprint, la forma compacta, el resultado del gate, la forma telegráfica y el sobre de integridad, con la fecha congelada (`2026-10-08`). Verificado: es determinista entre corridas; el parche de fecha surte efecto; el test **falla** si se altera el golden y vuelve a pasar al restaurarlo. Para un cambio intencional: `python -m benchmarks.characterization --write` y revisar el diff.
- **Lint fijado:** `[tool.ruff]` en `pyproject.toml` con solo reglas de corrección (`F`, `E9`, `B`, `I`) y `line-length = 200`. Línea base: **aixl 106 · benchmarks 132 · tests 51** avisos (los avisos de la sección 2 contaban con un conjunto de reglas más amplio, por eso las cifras difieren). Paso `lint` en CI **informativo** (`continue-on-error`); pasar a bloqueante al llegar a 0.
- **Línea base de rendimiento:** `benchmarks/perf_baseline.py` (243 textos): importar traductor 55 ms · `to_graph` 0.33 ms/texto · `translate_gated` 0.64 ms/texto · `seal` 0.56 ms/texto · suite 14.4 s (1093 tests + 1 de caracterización).
- **Hallazgo lateral:** `gate.fingerprint_graph` y `envelope` usan la fecha del sistema para textos con tiempo relativo ("hoy", "esta semana"), así que `seal` hoy y `verify` mañana pueden dar MISMATCH. Es semánticamente defendible (el "hoy" cambió) pero conviene decidirlo: pasar `today` explícito en el sobre.

### Fase 1 — HECHA (2026-10-08), en 3 commits reversibles
Puerta aplicada en cada subpaso: 1094 tests (incluida la caracterización) + `benchmarks/check_imports.py` (verifica que cada `from aixl… import nombre` del repo —benchmarks, CLI, lab, ejemplos incluidos— sigue resolviendo; base: 637 imports, 0 sin resolver) + humo de CLI/lab/servidores.
- **1a** (`aa6ec5e`): 54 imports sin uso / elementos duplicados / redefinición (F401, B033, F811) en 43 archivos.
- **1b** (`e4e2bcd`): ordenar imports (I001), 175 correcciones en 144 archivos. Excepciones documentadas en `pyproject.toml`: `cli.py` y `examples/*.py` (líneas compactas deliberadas como `import os, sys; sys.path.insert(…)`), `B905` (cambiar `zip` a `strict=True` alteraría semántica).
- **1c:** claves duplicadas con valor idéntico (`todo`, `caracteres`, `cliente`, `ingles`), anotaciones sin definir en `api/service.py` (`TYPE_CHECKING`), re-export explícito de `HybridDecision`, `raise … from e` en `cli.py`, `raise AssertionError` en un test, 2 imports sin uso en `lab/render.py`, `force-exclude` para `distill/`, y `F403/F405` permitidos en 2 scripts de benchmarks que usan `import *` a propósito.
- **Resultado:** avisos de lint **253 → 36** (todos F841 variables sin uso ×28 y B007 ×8, que son de la Fase 2 porque quitar una asignación puede quitar un efecto secundario).
- Lección registrada: `ruff --fix` se ejecuta solo sobre archivos versionados (`git ls-files`) para no tocar trabajo ajeno sin commit.

### Fase 2 — HECHA (2026-10-08)
- **Lint: 36 → 0 avisos** (`ruff check` limpio sobre todos los archivos versionados). Se aplicó el arreglo "inseguro" de ruff para F841/B007 y se revisó el diff a mano: ruff había dejado expresiones puras sueltas (`[t.f for t in toks]`, `getattr(…)`, `re.findall(…)`, `self.by_id()`, `_action_positions(s)`), que se borraron tras comprobar que no tienen efectos; y 3 variables de bucle se simplificaron (`enumerate` innecesario) o renombraron (`_act`).
- **Ramas muertas de `atoms/extract.py` (H2) eliminadas:** `… if True else None`, `… if False else None` (×2) y el bucle protegido por `… and False`. Con la salida de vulture como justificación; la prueba de caracterización confirma que el comportamiento no cambió.
- **Trampa evitada:** `elif f in ("it", "ele", "ela"): pass` parecía código muerto tras quitar `ref_subject`, pero **la rama hay que conservarla**: consume el caso e impide que ramas posteriores de la cadena `elif` lo traten. Quedó con un comentario que lo explica.
- `min_sim_fp` (parámetro muerto de `translate_gated`) eliminado; ningún llamador lo usaba.
- **H11 refutado** (ver tabla): `aixl/adapters/` se queda.
- Puerta: 1094 tests (incluida la caracterización) + `check_imports` (621 imports, 0 sin resolver).
- **Residual consciente (vulture al 100%):** 3 parámetros `request` de manejadores HTTP (los exige el framework: falso positivo) y 3 parámetros no usados de firmas internas (`_is_prop_like(f, pend)`, `_items_cmp(…, act_a, …)`, `anchored(extra, ctx_items)`). Se dejan: quitarlos obliga a tocar a todos los llamadores, con riesgo y sin ganancia medible.

### Fase 3 — HECHA (2026-10-08)
- **API pública de cobertura:** `aixl.core.completeness.is_complete(text, graph) -> bool` es ahora la única condición bajo la que AIXL puede reemplazar al texto natural (completitud base **y** estricta). `strict_complete` y `AFFIRM` viven en `completeness.py`.
- **Acoplamiento:** `gate.py` pasó de importar 8 nombres privados (`_ALLTOK`, `_CLOSED`, `_CONCEPT`, `_evidence_tokens`, `_forms`, `_norm`, `_known`, `_stem`) y 5 módulos auxiliares a importar **una** función pública (`is_complete`). `envelope.py` y `benchmarks/v1_telegraph_eval.py` dejan de repetir la combinación `check_completeness(...) and strict_complete(...)`. Imports privados entre módulos que quedan en `aixl/`: solo `autonomous_negotiation → _negotiate_core` y los de `completeness → lexicon_gaps` (misma capa `core`); el resto son alias `as _x`, no nombres privados.
- **Rendimiento:** sin cambio medible (`translate_gated` 0.635 ms/texto vs 0.638). Era lo esperado tras corregir H4.
- Tests nuevos: `tests/test_is_complete.py` (10 casos, incluido que la combinación pública equivale exactamente a la anterior).
- Puerta: 1104 tests (incluida la caracterización) + `check_imports` (611 imports, 0 sin resolver) + lint en 0.
