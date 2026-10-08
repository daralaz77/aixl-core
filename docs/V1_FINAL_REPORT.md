# AIXL v1.0 — informe final (actualizado 2026-10-08)

Auditoría del prompt "AIXL Interoperability Translator v1.0" contra `aixl-core`, más cinco pasos de seguimiento, todo medido sobre tráfico y sesiones reales. El detalle de cada medición está en `docs/V1_PROMPT_AUDIT.md`. Todo está en `main` (commits `c171498` … `a45ec3b`). Suite de pruebas: **1093 pasan**.

## 1. Conclusión
1. El prompt v1.0 ya estaba casi todo construido. Faltaba el **gate de tokens** (usar AIXL solo si ahorra y es seguro); ahora existe y verifica por fingerprint.
2. **AIXL no comprime tráfico real**: 0 de 1468 mensajes tuyos pasan el gate estricto. El valor medido de AIXL es **detectar pérdida y verificar equivalencia**, no comprimir.
3. La palanca de ahorro es otra: el 79% del texto de tus sesiones son salidas de herramientas, y gran parte se repite. **Punteros a contenido ya enviado** ahorran ≈17–18% del texto y ≈17–27% del costo ponderado (modelo, no factura) en sesiones largas.
4. Los punteros **no son seguros para cualquier receptor**: Sonnet y Opus los usan sin pérdida; Haiku empeora (27 → 14–18/60). Hace falta una compuerta por capacidad, que ya existe y falla cerrado.
5. Un almacén **compartido entre sesiones** no compensa: entre sesiones del mismo proyecto suma +7.3 puntos de texto (+2.8 de costo); entre proyectos solo +0.4. No construir uno global.

## 2. Qué se construyó (todo con tests)
| Pieza | Archivo | Qué hace |
|---|---|---|
| Gate de tokens | `aixl/gate.py` | MODE=NATURAL salvo que ahorre tokens, el fingerprint sobreviva la vuelta y la codificación sea completa (`strict_complete`, `AFFIRM`). |
| Forma telegráfica | `aixl/telegraph.py` | `analyze sales q1-2026`; vocabulario cerrado de la ontología; palabra desconocida falla cerrado. |
| Sobre de integridad | `aixl/envelope.py` | texto natural + huella de 8 hex; `verify` → MATCH / MISMATCH / UNVERIFIED (se abstiene fuera del dominio). |
| Almacén de referencias | `aixl/refstore.py` | bloques ya enviados → `⟦=msg:a-b (N lines)⟧`, verificado por decodificación; variante anotada. |
| Compuerta por capacidad | `aixl/refpolicy.py` | punteros solo a receptores medidos seguros (Sonnet, Opus); Haiku, Fable y no medidos reciben texto plano. |
| Benchmarks | `benchmarks/v1_*.py` | dev set, tráfico real, telegráfico, calidad/razonamiento/edición con punteros, facturación, entre sesiones. |

## 3. Defectos reales encontrados y corregidos
- Gate de tokens ausente: el wire AIXL era más largo que el texto.
- "Hola" → AIXL vacío (sobrecodificación).
- Pérdida silenciosa de "…conserva solamente lo más importante".
- Mensajes cortos: `check_completeness` eximía la *primera* palabra como verbo ("creo que ya revisa" → `A:CHECK`) y daba por contabilizada cualquier palabra del léxico aunque no estuviera en el grafo ("redacta el correo" → `A:GENERATE`). Corregido con `strict_complete`.
- Afirmaciones descartadas ("sí muestrame" → `A:GET`). Corregido con `AFFIRM`.
- Errores míos atrapados por las propias verificaciones: decodificador telegráfico (abreviaturas y mayúsculas), calificador con prefijo `N<tab>`, test de número con una palabra no cubierta, una calibración de tokens inválida (5.66 tok/carácter).

## 4. Resultados medidos
**Gate (tokenizador o200k_base).** Dev set (228 textos propios): AIXL en 2%, ahorro 16.4%. Tráfico real (1468 mensajes): 6 → 1 → **0** usos conforme se cerraron los huecos; los primeros 6 eran pérdidas disfrazadas de ahorro.

**Diccionario de sesión y átomos nuevos.** Diccionario: 11.7% (3 msgs), 18.4% (5), 27% (10) solo en sesiones construidas para repetir objetivo. Átomos: ≈2% → ≈4% de uso con partición derivar/evaluar. Marginales, no integrados.

**Opción A — telegráfico.** Dev set: 128/225 usables (57%), **−40.8% de tokens**, 0 desajustes de fingerprint. Tráfico real: 4/1629 (0.25%).

**Opción E — sobre de integridad.** 58 paráfrasis: 46 MATCH, 12 UNVERIFIED, **0 falsas alarmas**. 72 pares distintos: 57 MISMATCH, 0 MATCH erróneos. Corrupciones: negación 128/128, acción→eliminar 89/89, número 32/43 (11 abstenciones), última palabra 69/71. Cobertura: 90% del dev set pero solo **1.2% del tráfico real**.

**Opción C — punteros.**
- Volumen (409 sesiones, 43.7M caracteres): salidas de herramientas 79%, mensajes tuyos 13%, texto del asistente 8%. Ahorro: **17.3%** del texto (19.9% en salidas de herramientas), 0 fallos de ida y vuelta.
- Calidad (recuperar línea exacta, Sonnet): 23/24 texto completo; 22/24 y 24/24 con punteros.
- Razonamiento (60 respuestas por celda):

| Modelo | Texto completo | Punteros + leyenda | Sin leyenda | Anotados |
|---|---|---|---|---|
| Sonnet | 52/60 | 59/60 | 59/60 | 60/60 |
| Opus | — | — | — | 59/60 |
| Haiku | 27/60 | 14/60 | 18/60 | 14/60 |

- Edición, extracción y cadenas de dos niveles (Opus, 10 casos): texto completo 10/10, 10/10, 20/20; **con punteros 10/10, 10/10, 20/20**. **Sonnet no pudo evaluarse**: un clasificador de seguridad cortó ambas corridas al escribir la salida larga; no reformulé la tarea para esquivarlo. Resultado desconocido, no "pasó".
- Fallo observable en Haiku: contar/numerar líneas a través de un puntero (Q2/Q3). La anotación de longitud no lo corrige.

**Facturación real (campo `usage`, 42,240 llamadas).** Lecturas de caché: 98.7% de los tokens y 82.8% del costo ponderado; escrituras 11.7%; salida 5.4%. Claude ≈ **0.47 tokens/carácter**, ≈1.5× más que o200k en este contenido. Punteros: **26.8%** (calibrado) o **17.0%** (0.30 tok/car) del costo ponderado.

**Entre sesiones (techo).**
| Alcance | Texto apuntable | Ahorro de costo |
|---|---|---|
| una sesión | 18.5% | 17.1% |
| mismo proyecto | 25.8% | 19.9% |
| todos los proyectos | 26.2% | 20.0% |

## 5. Qué sí y qué no se puede afirmar
**Sí**
- El gate evita emitir AIXL con pérdida de significado en los casos probados.
- La forma telegráfica ahorra ~41% en instrucciones estructuradas que la ontología cubre, sin pérdida respecto al grafo.
- Los punteros ahorran ~17–18% del texto de las sesiones y Sonnet y Opus los usan bien (búsqueda, razonamiento; Opus también edición, extracción y cadenas).
- El sobre de integridad detecta distorsiones del dominio sin falsas alarmas.

**No**
- Que AIXL comprima tráfico conversacional real (no lo hace).
- Que los punteros sirvan a cualquier receptor: con Haiku empeoran; Fable y otros no están medidos.
- Que Sonnet pase edición/extracción/cadenas: nunca se pudo medir.
- Que el ahorro de costo sea una cifra de factura: es un modelo (supone caché siempre vigente y sin compactación de contexto).
- Que un almacén entre sesiones llegue al techo medido: cada puntero entre sesiones necesita una herramienta de expansión.
- Equivalencia semántica fuera del dominio acotado: sigue valiendo lo medido antes (árbitro 2-de-2).

## 6. Límites generales
Corpus de desarrollo propio (mismo autor que el código); una corrida por celda; 2–3 modelos; 10–24 casos en las pruebas con modelos; mutaciones por reglas simples; subagentes con instrucción (no obligación técnica) de no usar herramientas de cómputo, aunque registraron solo llamadas de lectura; fidelidad telegráfica solo respecto al grafo del traductor; sin resumen con criterio (no tiene calificador objetivo); cadenas de punteros de profundidad 2; pesos de precio supuestos.

## 7. Recomendaciones finales
1. **Producto:** usar AIXL como capa de **verificación** (sobre de integridad + gate), no como compresor.
2. **Ahorro real:** punteros dentro de una sola sesión, solo a receptores de la lista (Sonnet, Opus), con la compuerta fallando cerrado.
3. **No construir** un almacén global entre proyectos. Un almacén por proyecto solo si se resuelve la expansión sin costo (+7 puntos de texto).
4. Antes de afirmar ahorro en dinero: un A/B real sobre facturas, con la caché y la compactación incluidas.
5. Pendientes con valor: medir Sonnet en edición/extracción/cadenas con un diseño que no dispare el clasificador (sin copiar a mano textos largos), medir Fable, y probar tareas de resumen con evaluación humana.
