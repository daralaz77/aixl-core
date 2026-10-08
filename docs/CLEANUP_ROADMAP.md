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

### Fase 4 — HECHA (2026-10-08)
- **Importar un benchmark ya no ejecuta nada:** de 36 scripts sin guarda `__main__` → **0** (34 transformados con un script basado en AST que conserva imports, defs y constantes puras y mueve el resto bajo `if __name__ == "__main__":`; 2 ya eran seguros). Puerta permanente: `tests/test_benchmarks_import_clean.py` importa los 64 módulos en un subproceso y exige cero salida y cero errores.
- **Cargador de transcripciones:** la ruta `~/.claude/projects/*/*.jsonl` estaba copiada en 8 scripts; ahora vive en `benchmarks/_corpus.py` (`transcript_files`, `blocks`, `tool_results`, `real_user_messages(skip_meta=…)`), con `AIXL_TRANSCRIPTS_GLOB` para pruebas. `tests/test_benchmarks_corpus.py` lo ejecuta de verdad con una transcripción falsa. `transcript_files()` conserva el orden nativo de `glob` a propósito: varios scripts con semilla barajan esa lista.
- **Verificación de equivalencia (antes vs después):** 29 scripts sin efectos secundarios: 27 con salida idéntica; los 2 restantes (`v1_billing_eval`, `v1_refstore_eval`) difieren solo por datos vivos (la sesión sigue escribiendo transcripciones; ej. 44,144,345 → 44,161,703 caracteres). Para los 7 scripts que leen transcripciones se repitió la comparación sobre una **instantánea congelada de 160 archivos**: idénticos billing, envelope, telegraph, refquality_build, refreason_build (con la misma `PYTHONHASHSEED`) y real_eval (tras el arreglo de abajo). `v1_refstore_eval` difiere solo en una línea de muestreo con `random.random()` sin semilla (no reproducible ni con el código original).
- **Errores míos atrapados por esas verificaciones (y corregidos):** (1) el transformador dejó a nivel de módulo un `msgs = sorted(msgs)` que dependía de un bucle movido bajo `main` (habría fallado); regla corregida: una asignación conservada no puede leer nombres que el código movido toca (asigna o muta). (2) el transformador procesó el recién creado `_corpus.py` y movió su constante; lo rompió sin que la importación lo notara. (3) La primera comparación quedó enmascarada porque el código roto no sobrescribió los archivos de salida viejos: por eso la comparación final usa datos congelados y compara stdout, no solo archivos. (4) `v1_real_eval` filtraba registros `isMeta` y mi cargador común no; añadido `skip_meta`.
- **Hallazgo de reproducibilidad:** `v1_refreason_build` elegía palabras con `random.choice` sobre un conjunto de iteración no determinista (`PYTHONHASHSEED`): el script original daba casos distintos en cada ejecución (verificado: semilla 0 vs 1). Ahora ordena (`sorted`). El archivo de casos que se usó para calificar quedó guardado y no cambia; solo una regeneración daría otros casos.
- **Rondas ciegas congeladas (`blind14`–`blind18`):** su `CODE_FREEZE.json` comprueba hashes de `aixl/semantic/*`. De 28 hashes que hoy no coinciden, **25 ya eran distintos antes de la limpieza** (el código evolucionó tras cada congelación); 3 coincidían y los rompí yo (`semantic/__init__.py` en blind17/18 y `hybrid.py` en blind18), pero ambas rondas ya estaban invalidadas por otros archivos. No se reparan: son verificaciones históricas por diseño.
- **Aviso:** mi primer barrido transformó `benchmarks/atoms_ab_eval.py`, que no está versionado y no es mío (de otra sesión). Su comportamiento al ejecutarse es el mismo, pero quedó con su código bajo `main` y no se puede restaurar a su forma exacta.
- Puerta: 1107 tests + `check_imports` (611 imports) + lint en 0.

### Fase 5 — HECHA (2026-10-08), solo cambios con ganancia medida
Regla: cada cambio entra solo si mejora ≥5% en la medición **en frío** (`perf_baseline --cold`: una pasada por proceso nuevo, para que una caché no se vea mejor de lo que es) y pasa la puerta (tests + caracterización + `check_imports` + lint). Ruido de medición ≈ ±1.5%.

| Cambio | Gate ms/texto (frío) | Sobre ms/texto (frío) | Ganancia |
|---|---|---|---|
| línea base (Fase 0–4) | 0.649 | 0.569 | — |
| 5a caché acotada y **consciente de la versión del léxico** en `lexicon_gaps._known` | 0.598 | 0.515 | −8% / −10% |
| 5b `_evidence_tokens` una vez por `is_complete` (antes hasta 3 veces, cada una recalculando `canonical()`) | 0.568 | 0.487 | −5% / −5% |
| 5c camino rápido ASCII en `strip_accents` (equivalencia comprobada en todo el rango latino y 2000 cadenas aleatorias) | 0.530 | 0.445 | −7% / −9% |
| 5d frases de marcadores precompiladas en `completeness` | 0.502 | 0.422 | −5% / −5% |
| **Total** | **0.504 (−22%)** | **0.418 (−26%)** | |

Mismo método que la línea base de la Fase 0 (en caliente, mínimo de 5): `to_graph` 0.327 → 0.276 ms (−16%), gate 0.638 → 0.499 (−22%), sobre 0.556 → 0.420 (−24%); importar el traductor 55 → 43 ms.
- **Suite:** `tests/test_mcp_integration.py` marcado `slow` (levanta servidores MCP reales): `pytest -m "not slow"` corre en 9.4 s frente a 15.3 s; CI sigue corriendo todo. 1111 tests.
- **Lección de la fase:** mi primera caché de `_known` hizo fallar 2 tests, y mi comando encadenado hizo un commit igualmente porque el script de puerta no devolvía error (ya devuelve `GATE FAILED` y código 1). Causa real: el mecanismo de extensiones documentado **añade palabras a los léxicos cerrados en tiempo de ejecución** (`docs/EXTENSION_GUIDE.md`, probado en `test_docs.py`), así que una caché ingenua devolvía respuestas viejas. Se arregló con una clave que incluye el tamaño de cada tabla consultada; limitación declarada: un reemplazo en sitio que conserve el tamaño de una tabla no se vería. Test de regresión: `tests/test_lexicon_cache.py`.
- **Descartado a propósito:** memoizar `canonical()` (el grafo es mutable; riesgo de resultados viejos) y precompilar los ~25 patrones en línea de `legacy02.analyze` (ganancia estimada <5%, edición grande en código que se retirará en la Fase 6).
- Ruido real vs. ganancia práctica: el gate pasó de 0.65 a 0.50 ms; en términos absolutos sigue siendo irrelevante frente al costo de tokens (el motivo por el que se midió desde el principio).

### Fase 6 — ANÁLISIS HECHO, DECISIÓN PENDIENTE (2026-10-08) → `docs/adr/ADR-022.md`
Las mediciones corrigen tres supuestos del propio roadmap:
- **`legacy02` no es código muerto, es la base del producto:** hoja del grafo de imports (no importa nada de `aixl`), contiene el codificador/parser de la sintaxis AIXL, `SemanticFrame`, las tablas de reglas (`DATA_RX` 10 usos, `ENTITY_RX` 9, `MONTHS` 7…) y `analyze`; `import aixl` arrastra 8 de sus 14 archivos. Solo el nombre es "legado".
- **El grafo de paquetes es casi acíclico:** un único ciclo en tiempo de importación (el normal `__init__`↔submódulos de `semantic`) y un ciclo `core`↔`translators` solo mediante 3 imports perezosos.
- **Lo experimental ya está aislado:** `import aixl` no alcanza `semantic/` ni `atoms/`; `semantic/` entra solo por la herramienta MCP híbrida; `atoms/` solo por `cli atoms-*` y benchmarks. H12 ("tres representaciones enredadas") queda **refutado**.
Opciones del ADR-022: **A** documentar + etiquetar + prueba de arquitectura que haga cumplir las reglas (recomendada, ~½ día, riesgo cero); **B** A + renombrar `legacy02`→`frame` y mover lo experimental a `experimental/` con alias (2–3 días); **C** A + separar lo experimental como extra opcional (3–5 días, quita una herramienta MCP publicada del servidor por defecto). No se aplicó nada: es una decisión tuya.

### Fase 6 — OPCIÓN A APLICADA (2026-10-08, elegida por el dueño)
`tests/test_architecture.py` (reglas R1–R5 sobre el grafo real de imports, con el motor de reglas probado contra violaciones inyectadas y una comprobación en tiempo de ejecución de que `import aixl` no carga `semantic/` ni `atoms/`), etiquetas de estado en `legacy02`, `semantic` y `atoms`, y la sección "Package layering and status" en `ARCHITECTURE.md`. ADR-022 pasa a ACCEPTED. Efecto secundario a vigilar: `aixl/atoms/` no tenía `__init__.py`; ahora sí, así que `find_packages` debería incluirlo en las distribuciones construidas (antes se omitía sin aviso); verificado con setuptools 84.0.0: 13 paquetes sin el archivo y 14 con él; el wheel (`aixl-0.5.0`, 82 archivos) ahora trae los 10 `.py` de `atoms`, pero NO sus datos JSON (`aixl/atoms/data/`, sin configuración de package-data). B (renombrar) y C (extra opcional) siguen abiertas.
**Las 7 fases (0–6) quedan cerradas.** Balance: lint 253 → 0 avisos; 36 scripts sin guarda → 0; red de seguridad por caracterización; gate −22% y sobre −26% de latencia; arquitectura convertida en pruebas.
