# Auditoría Consejo 5X — aixl-core (2026-10-13)

Objetivo: auditoría completa y ruta de mejora, trabajando en bucle (auditar → corregir el mayor riesgo verificable → re-medir → repetir). Evidencia = ejecución real; cada afirmación marcada CONFIRMADA / PROBABLE / HIPÓTESIS.

## 1. Bucle ejecutado (5 iteraciones, todas con la puerta de 1161 tests + caracterización + arena)
| # | Riesgo atacado | Antes (medido) | Después (medido) | Commit |
|---|---|---|---|---|
| 1 | **Disponibilidad:** un mensaje de 62–120 KB bloqueaba el proceso; ningún servidor acotaba la entrada | 62 KB → 5.1 s; 80–120 KB de años/números → **> 8 s** | entrada > 16 384 car.: rechazo en 0.00 s (gate → NATURAL, sobre → UNVERIFIED) | `3d0a7e4` |
| 2 | Raíz del costo O(n²): `add_node`, un escaneo por *aparición* de año/fecha, regex de racha numérica, `unaccounted_content` | 64 KB `Q1 2026 ×8000` → 9.7 s; 120 KB `1,2,3,…` → > 8 s | 0.29 s (lineal ×2.0 al duplicar); 192 KB numérico → 0.86 s | `3d0a7e4` |
| 3 | Equivalencia con los 2.242 textos (dev + 2.500 reales + mutantes de la arena) | — | **2.242/2.242 idénticos** (huella + formato AIXL + forma canónica), con árboles de código distintos verificados | `3d0a7e4` |
| 4 | **Seguridad del producto publicado:** las herramientas MCP/A2A `aixl_compare` devolvían `equivalent: true, similarity: 1.0` sin aviso | falso "equivalente" con otros autores: **19.7 %** (blind13) y **35.4 %** (blind14); 33 % en pares de la arena | **0 %** en los cuatro corpus (0/232 pares distintos) | este commit |
| 5 | **Hueco nuevo, ninguna capa lo veía:** Y→O ("a Ana y a Luis" → "a Ana o a Luis"): el comparador y **el sobre de integridad** decían EQUIVALENT/MATCH | 8 falsos MATCH en 415 mutantes sin el guard | 0 con el guard; atacante `conj_swap` añadido a la arena | este commit |

Costo declarado de 4–5: recall de paráfrasis verdaderas en texto abierto 22–25 % → 0–2 % (dev set propio 100 % → 76 %). Es coherente con ADR-018: para "¿son iguales dos textos abiertos?" se usa el árbitro 2-de-2, no esta regla.

### Continuación del bucle (iteraciones 6–8, mismo día, pasos 1–3 de la lista)
| # | Paso | Antes | Después (verificado) |
|---|---|---|---|
| 6 | **Autenticación + límite de tasa en A2A** (`aixl/agents/guard.py`) | sin token ni límite; imagen, compose y k8s ligados a `0.0.0.0` | escuchar en interfaz no local **sin `AIXL_A2A_TOKEN` termina con código 2**; por HTTP real: probes y tarjeta 200, RPC y `/metrics` sin token **401**, token malo 401, cuerpo 300 KB **413**, ráfaga sobre 6/min → **429** + `Retry-After`; Docker (`${AIXL_A2A_TOKEN:?…}`) y k8s (Secret `aixl-a2a-auth`) actualizados; 8 tests nuevos + los 19 de protocolo A2A siguen verdes |
| 7 | **Lint de CI bloqueante** | `continue-on-error: true`; solo `aixl benchmarks tests` | bloqueante sobre **todo el repo** (`ruff check .` = 0), ruff fijado a la versión medida, y un job `arena` (`selftest` + `scope`, salida ≠ 0 si hay defecto) como compuerta de release; `check_imports` en el job de tests |
| 8 | **Aviso de uso seguro de `aixl.compare`** | solo en LIMITATIONS | docstring de la función y del paquete, caja en el README y nota en la CLI (por `stderr`; `stdout` y `--json` intactos) |

**Honestidad sobre lo que NO cubre el paso 6:** TLS (debe terminar en el ingress), rotación de token, cuotas por cliente (el límite es por dirección y por proceso: N réplicas = N× el límite), y autorización más fina que "tiene el token". **El token en el entorno es secreto de despliegue: no se probó contra un gestor de secretos real.**

## 2. DATOS CONFIRMADOS frente a SUPOSICIONES
**Confirmado (ejecutado hoy):** estado del repo limpio y sincronizado; 1161 tests; lint 0; cobertura de líneas 88 % (`agents` 19 % sin los tests lentos, `legacy02` 63 %); tiempos de entrada hostil antes/después; falsos equivalentes por capa; el hueco Y/O; README declara honestamente que la ruta de reglas es insegura en texto abierto.
**Suposición / desconocido:** nº de usuarios reales (ninguno medido), disposición de pago, comportamiento del servidor A2A bajo `InputTooLarge` en `aixl_negotiate` (no verificado), costo real en factura de los punteros (solo modelo), seguridad ante prompt-injection de un cliente que *consuma* estos veredictos.

## 3. Puntuación (0–100)
| Área | Antes | Después | Motivo principal |
|---|---|---|---|
| Código / Arquitectura | 72 | **80** | capas como pruebas, sin ciclos de importación; quedan: un patrón superlineal acotado, `legacy02` al 63 % de cobertura, dos comparadores |
| Seguridad | 50 | **76** | entrada acotada; superficie publicada sin falsos "equivalente"; **sin autenticación ni límite de tasa en A2A** (documentado, no resuelto) |
| Producto / UX | 55 | **57** | veredicto honesto y verificable, pero valor estrecho y README denso (HIPÓTESIS: tiempo hasta el primer valor alto) |
| Ventas / Mercado | 35 | **35** | sin evidencia de demanda; el diferenciador medido (verificación) compite con un árbitro LLM que ya hace lo mismo mejor |
| QA / Operaciones | 78 | **84** | arena con 6 errores plantados detectados, congelamiento por hash, caracterización, guardas de escalado; CI de lint aún informativo |
| **Global** | 58 | **67** | **Riesgo considerable**; el riesgo CRÍTICO de mercado no lo oculta el promedio |

## 4. Los 10 mayores riesgos (Probabilidad × Impacto)
| # | Riesgo | P | I | R | Estado |
|---|---|---|---|---|---|
| 1 | Sin demanda demostrada: producto sin mercado o sin disposición de pago | 7 | 9 | **63** | abierto (estrategia, §7) |
| 2 | Servidor A2A expuesto sin autenticación ni límite de tasa | 5 | 8 | **40** | **CERRADO (iteración 6)**: falla cerrado, token Bearer, límite de tasa y de cuerpo; sin TLS ni cuotas por cliente |
| 3 | Quien consume `equivalent` de `aixl.compare` (API, no MCP) confía en un veredicto inseguro en texto abierto | 6 | 7 | **42** | mitigado en MCP/A2A; **aviso de uso seguro en API, paquete, README y CLI (iteración 8)**; el comportamiento de la biblioteca no cambia por compatibilidad |
| 4 | Diferenciador absorbido por árbitros LLM baratos (precio/latencia cayendo) | 6 | 7 | 42 | abierto |
| 5 | Meaning flips aún desconocidos (el Y/O estuvo 5 semanas sin verse) | 6 | 7 | 42 | **mitigado en parte**: arena + scope; semillas de un solo autor |
| 6 | Conclusión cuantitativa sobre un corpus propio / un solo autor | 5 | 6 | 30 | abierto |
| 7 | Agotamiento de CPU por patrón superlineal remanente (124 KB ~ 2.5 s) | 3 | 5 | 15 | acotado por el límite |
| 8 | Deriva documental: 41 docs, claims históricos y vigentes mezclados | 5 | 4 | 20 | abierto |
| 9 | Otra sesión escribe en el mismo repo (conflictos, push de commits ajenos) | 6 | 3 | 18 | proceso, no código |
| 10 | Dependencia de modelos medidos (lista de punteros) cuando salgan versiones nuevas | 4 | 5 | 20 | política falla cerrado |

## 5. Por qué podría fracasar (≥10)
1. Nadie lo necesita: el valor medido es "no decir igual sin prueba", y un LLM de 2 votos ya lo hace. 2. No hay canal de adquisición: ni PyPI ni usuarios medidos. 3. Un incidente público de falso "equivalente" destruye la confianza (el único producto es la confianza). 4. Un modelo más barato/rápido hace innecesario el vocabulario cerrado. 5. El costo de mantener ontología ES/EN/PT crece más que el valor. 6. El A2A abierto se abusa (DoS, extracción). 7. Los resultados de los benchmarks se perciben como autoevaluación. 8. Las extensiones de léxico (mutan tablas en ejecución) producen resultados no reproducibles entre despliegues. 9. La narrativa de investigación (artículo con resultados negativos) aleja a compradores. 10. Dependencia de una sola persona/sesión para decidir qué es verdad. Señales tempranas, prevención y prueba de cada una: ver §6–§8.

## 6. Soluciones (inmediata / corto / medio / estratégica)
- **Inmediata (hecha):** límite de entrada; superficie publicada verificada; guard Y/O; arena sobre las capas publicadas.
- **Corto:** autenticación por token + límite de tasa en A2A; subir lint de CI a bloqueante; `aixl.compare` marcada en la API con aviso de uso (solo vocabulario controlado); versionar el sobre (`AIXL-ENV-2`, porque ahora lleva `or`).
- **Medio:** arreglar el patrón superlineal remanente (frases repetidas); más atacantes por familia de significado (cuantificadores, condicionales, alcance de negación); semillas de otros autores en la arena.
- **Estratégica:** ofrecer **un solo servicio**: *verificación de instrucciones entre agentes* = sobre de integridad + árbitro 2-de-2 + punteros para ahorro (lo único con dinero medido: 17–27 % del costo en sesiones largas), con la arena como motor de calidad compuesto.

## 7. Ruta de mejora "exponencial" (qué compone de verdad)
Nada garantiza crecimiento exponencial; estos son los mecanismos que **se acumulan** en vez de sumarse:
1. **La arena como motor:** cada defecto hallado se vuelve semilla permanente, un oráculo y una prueba (hoy: 6 familias de oráculo, 20 atacantes). Costo marginal por defecto → ≈ 0.
2. **Superficie publicada que degrada a "no sé":** cada hueco nuevo reduce afirmaciones en vez de añadir falsas, así la confianza solo sube.
3. **Datos reales como corpus:** las transcripciones propias ya dieron 3 hallazgos que ningún benchmark propio dio (punteros, AND/OR, entrada larga).
4. **Ahorro de costo medible (punteros)** como razón de pago, no la equivalencia.
5. **Congelamiento + preregistro** como activo: resultados negativos creíbles son diferenciador frente al ruido del sector.

## 8. Pruebas y métricas
**Pruebas (existentes):** caracterización de 247 textos; arena `selftest` (6 plantados) y `scope` (1036 mutantes); `compare_verified_eval` (4 corpus); guardas de escalado; equivalencia old/new sobre 2.242 textos. **Faltan:** carga concurrente real contra el servidor A2A (10×), prueba de recuperación ante caída del proceso, fuzz de `decode` con gramática, prueba de wheel instalado de extremo a extremo.
**Métricas a vigilar:** falsos equivalentes por capa publicada (objetivo 0 en `scope`), p95 de latencia del gate (hoy ~0.5 ms; 0.21 s peor caso), tasa de `UNVERIFIED/INCONCLUSIVE` en tráfico real (indicador de utilidad), tamaño de entrada p99, defectos nuevos de la arena por 1000 mutantes, y —las que no existen— usuarios activos y tasa de reutilización.

## 9. Decisión del Consejo
**GO CON CONDICIONES** como **herramienta experimental de verificación local / entre agentes propios**, con las condiciones: (1) A2A no se expone a red sin autenticación y límite de tasa **(cumplida en el código; falta TLS en el ingress)**; (2) no se afirma equivalencia de texto abierto; (3) cada release corre `scope` en cero.
**NO-GO** para posicionarlo como probador general de equivalencia semántica o desplegarlo públicamente sin esas condiciones.

## 10. Próximos 10 pasos
1. ~~Autenticación + límite de tasa en A2A~~ **hecho (iteración 6)**; falta TLS en el ingress. 2. ~~Lint de CI bloqueante~~ **hecho (iteración 7)**. 3. ~~Aviso de uso seguro en `aixl.compare`~~ **hecho (iteración 8)**. 4. `AIXL-ENV-2` y compatibilidad del campo `or`. 5. Corregir el patrón superlineal remanente. 6. Atacantes de cuantificadores/condicionales/alcance de negación en la arena. 7. Semillas de otros autores (Opus/Sonnet sin acceso al repo) para la arena. 8. Prueba de carga concurrente del servidor y de recuperación. 9. Construir y probar un wheel limpio. 10. Decidir con el dueño el producto único (verificación + punteros) y medir interés real con 3–5 usuarios antes de invertir más.
