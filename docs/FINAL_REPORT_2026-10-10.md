# aixl-core — informe final consolidado (8–10 octubre 2026)

Resume todo el trabajo hecho en esta sesión sobre `aixl-core`: la auditoría del prompt AIXL v1.0 con sus cinco pasos de seguimiento, el camino de limpieza (fases 0–6), la decisión de arquitectura (ADR-022), el empaquetado, y la ejecución del experimento preregistrado blind5. Cada cifra tiene su detalle y su método en los documentos enlazados. Todo está en `main` salvo lo indicado en la sección 7.

## 1. Resumen ejecutivo
1. **AIXL no comprime tráfico real; su valor medido es verificar.** 0 de 1468 mensajes tuyos reales pasan el gate estricto. Donde sí hay ahorro es en **punteros a contenido ya enviado**: ≈17–18% del texto de las sesiones, ≈17–27% del costo ponderado (modelo, no factura).
2. **Los punteros solo son seguros para receptores medidos:** Sonnet y Opus sin pérdida; Haiku empeora (27 → 14–18 de 60). La política falla cerrado para modelos no medidos.
3. **El código quedó más limpio y más barato de mantener:** lint de 289 avisos a 0, 36 scripts que ejecutaban al importarse a 0, una red de seguridad por caracterización, y la arquitectura convertida en pruebas.
4. **blind5 (preregistrado) dio 2 hipótesis cumplidas y 2 no:** la forma normal sube el acuerdo entre modelos (+6.7 pts); exponer los 93 conceptos aprendidos **no** lo mejora (estimación puntual negativa) y el pipeline combinado no llega al 60% de aceptación. Las afirmaciones ligadas a H2 y H4 quedan retiradas.
5. **Errores míos hubo varios, y las propias verificaciones los atraparon:** están listados en la sección 5 con su corrección.

## 2. Auditoría AIXL v1.0 y pasos 1–5 (detalle: `docs/V1_FINAL_REPORT.md`, `docs/V1_PROMPT_AUDIT.md`)
| Tema | Resultado medido |
|---|---|
| Gate de tokens (`aixl/gate.py`) | `MODE=NATURAL` salvo que ahorre tokens, el fingerprint sobreviva la vuelta y la codificación sea completa. Mensajes reales: 6 → 1 → **0** usos conforme se cerraron huecos (los 6 primeros eran pérdidas disfrazadas de ahorro) |
| Forma telegráfica (`telegraph.py`) | −40.8% de tokens, 57% de usables en el dev set, **0.25%** en tráfico real |
| Sobre de integridad (`envelope.py`) | 0 falsas alarmas en 58 paráfrasis; negación 128/128, acción 89/89 detectadas; verificable en **1.2%** del tráfico real |
| Punteros (`refstore.py`) | 17.3% del texto de 409 sesiones (79% del volumen son salidas de herramientas); 0 fallos de ida y vuelta |
| Calidad con punteros | Sonnet 59–60/60 (texto completo 52/60); Opus 59/60 y 40/40 en edición/extracción/cadenas; Haiku 14–18/60 |
| Facturación real (campo `usage`) | 98.7% de los tokens son lecturas de caché (82.8% del costo); Claude ≈ 0.472 tokens/carácter (≈1.5× lo que cuenta o200k) |
| Almacén entre sesiones (techo) | mismo proyecto +7.3 pts de texto (+2.8 de costo); entre proyectos +0.4 → no construir uno global |

## 3. Camino de limpieza, fases 0–6 (detalle: `docs/CLEANUP_ROADMAP.md`)
| Fase | Qué se hizo | Resultado |
|---|---|---|
| 0 | prueba de caracterización (243 textos, fecha congelada), lint fijado, línea base de rendimiento | la red de seguridad falla si se altera el golden; determinista |
| 1 | imports sin uso, orden de imports, claves duplicadas, anotaciones sin definir | 3 commits reversibles; verificador `check_imports` (621 imports, 0 sin resolver) |
| 2 | variables sin uso, ramas muertas de `atoms/extract.py`, parámetro muerto | **lint 0**; `aixl/adapters/` conservado (mi hipótesis H11 era falsa) |
| 3 | API pública `is_complete`; `gate.py` deja de importar 8 nombres privados | sin cambio de velocidad (mi hipótesis H4 era falsa) |
| 4 | 34 scripts de benchmarks con guarda `__main__`; cargador común `_corpus.py` | 64 módulos importan sin salida; defecto de reproducibilidad hallado y corregido |
| 5 | caché de `_known` consciente de la versión del léxico, evidencia una vez, camino rápido ASCII, regex precompiladas | gate 0.649 → **0.504 ms (−22%)**, sobre −26%; suite rápida 9.4 s frente a 15.3 s |
| 6 | análisis → ADR-022; opción A aplicada | ver sección 4 |

## 4. Arquitectura y empaquetado
- **ADR-022:** `legacy02` **no** es código muerto: es la base del producto (sintaxis AIXL, `SemanticFrame`, tablas de reglas; `import aixl` carga 8 de sus 14 archivos). El grafo de paquetes es casi acíclico y lo experimental (`semantic/`, `atoms/`) ya está aislado de `import aixl`. Aplicada la **opción A**: `tests/test_architecture.py` hace cumplir 5 reglas (probadas contra violaciones inyectadas), etiquetas de estado en los tres paquetes y sección de capas en `ARCHITECTURE.md`. Opciones B (renombrar) y C (extra opcional) siguen abiertas.
- **Empaquetado:** `aixl/atoms/` no tenía `__init__.py` y sus JSON no viajaban. Verificado con setuptools 84: 13 → 14 paquetes; con `package-data`, un wheel desempaquetado fuera del repo carga **93 conceptos** y los alias (el wheel anterior cargaba 0, en silencio). Guarda: `tests/test_packaging.py`.

## 5. blind5 — experimento preregistrado (detalle: `docs/ATOMS_AB_EVIDENCE_blind5.md`, ADR-021)
Congelado por hash (30 archivos, `data/atoms/FREEZE_blind5.json`) antes de pedir respuestas; 12 agentes independientes produjeron 8 respuestas y 4 anotaciones, todas validadas (75 líneas, ids correctos).
| Hipótesis | Veredicto | Números |
|---|---|---|
| H1 forma normal | **Cumplida** | acuerdo exacto 0.282 → 0.349 |
| H2 exponer conceptos aprendidos | **No cumplida** | 0.349 → 0.300; aceptación 58.7% → 51.3% (cambios pareados 16 vs 23, p = 0.34) |
| H3 sin daño | Cumplida, **sin ser mejora** | F1 aceptado 0.878 → 0.949, pero con un subconjunto aceptado más pequeño |
| H4 combinado | **No cumplida** | aceptación 51.3% < 60% |
Retiradas por la regla fijada de antemano: "los conceptos aprendidos mejoran acuerdo y aceptación" y "el pipeline combinado llega a 60%". Techo observado: Sonnet y Opus producen el mismo grafo en 30–35% de los textos.

## 6. Errores míos y su corrección
| Error | Cómo se detectó | Corrección |
|---|---|---|
| Hipótesis H4, H5, H11, H12 del roadmap eran falsas o imprecisas | mediciones posteriores | corregidas en el roadmap y en ADR-022 |
| El transformador de guardas dejó `msgs = sorted(msgs)` dependiente de un bucle movido, y rompió `_corpus.py` | comparación sobre datos congelados | regla corregida; módulo reparado; test que ejecuta el cargador |
| Mi primera comparación quedó enmascarada por archivos viejos | la salida estándar difería | comparación con datos congelados y stdout |
| El cargador común no filtraba `isMeta` | stdout de `v1_real_eval` | parámetro `skip_meta` |
| Una caché de `_known` rompió 2 tests (el mecanismo de extensiones muta los léxicos) y un commit salió con tests rojos porque el script de puerta no devolvía error | suite completa | clave por versión del léxico; el script ya devuelve código 1 |
| `git add -A` preparó archivos ajenos | `git status` | deshecho antes de commitear |
| Transformé `benchmarks/atoms_ab_eval.py` (no versionado, de otra sesión) | revisión conjunta | comportamiento verificado igual; luego congelado y versionado |
| Código de `atoms/` editado tras el preregistro de blind5 | revisión conjunta | evidencia de equivalencia (1.648/1.648 textos, 4/4 prompts, 8/8 respuestas) y addendum en ADR-021 |

## 7. Incidentes y cosas ajenas
- **Clasificador de seguridad:** cortó dos corridas de Sonnet (edición/extracción/cadenas) al escribir salidas largas. No reformulé la tarea para esquivarlo; el resultado de Sonnet en esa prueba es **desconocido**.
- **Límite de sesión:** los 12 agentes de blind5 fallaron a la primera (429); se relanzaron por tandas tras el reinicio. No quedaron archivos parciales.
- **Otra sesión trabaja en este repo** (`lab/arena`, relation5, decodificación estricta). Un `git push` mío subió dos commits suyos (`96eb618`, `720b062`) que ya estaban en la rama local; dejaron 3 avisos de lint, corregidos en `f7e0d59` sin cambio de comportamiento. Sus cambios sin commitear (`aixl/gate.py`, `aixl/translators/natural_to_semantic.py`, `lab/arena/`, `data/arena/`, `tests/test_arena.py`) siguen intactos y fuera de mis commits.

## 8. Estado final
- Remoto (`main`) en `f7e0d59`; este documento está en el commit local siguiente. El rango `c171498` … `f7e0d59` tiene **36 commits: 34 míos y 2 de la otra sesión**; 207 archivos tocados.
- **1129 tests pasan** en el estado commiteado, 627 imports resueltos, lint en 0.
- blind5: congelamiento íntegro; resultados versionados.

## 9. Pendientes y decisiones abiertas
1. **ADR-022 B/C:** renombrar `legacy02`/mover lo experimental, o separar lo experimental como extra opcional (esto quitaría la herramienta MCP híbrida del servidor por defecto).
2. **Sonnet en edición/extracción/cadenas** sin medir; **Fable** y otros modelos sin medir para la lista de punteros.
3. **Un A/B real sobre facturas** (caché y compactación incluidas) antes de prometer ahorro en dinero.
4. **Resumen con criterio** y **cadenas de punteros profundas** sin probar.
5. **blind5 tras la limpieza:** cualquier edición de los 30 archivos congelados lo anula; si hay que limpiar `aixl/semantic/`, regenerar el congelamiento con un addendum.
6. **Integrar o descartar el trabajo de `lab/arena`** (otra sesión): hoy está sin commitear.
7. **Construir y probar un wheel completo** antes del próximo release (verificado el contenido de `atoms`, no una instalación limpia de extremo a extremo).

## 10. Mapa de documentos
`docs/V1_FINAL_REPORT.md` (auditoría v1.0), `docs/V1_PROMPT_AUDIT.md` (mediciones por paso), `docs/CLEANUP_ROADMAP.md` (fases 0–6), `docs/adr/ADR-022.md` (capas), `docs/adr/ADR-021-prereg-blind5.md` (preregistro, addendum y resultado), `docs/ATOMS_AB_EVIDENCE_blind5.md` (evidencia blind5), `ARCHITECTURE.md` (capas y estados).
