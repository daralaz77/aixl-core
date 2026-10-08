# AIXL v1.0 — informe final (2026-10-08)

Auditoría del prompt "AIXL Interoperability Translator v1.0" contra `aixl-core`, con mediciones sobre tráfico real. Detalle completo y cifras de cada paso en `docs/V1_PROMPT_AUDIT.md`. Todo está en `main` (commits `c171498` … `c2fc5de`).

## 1. Conclusión en cinco líneas
1. El prompt v1.0 ya estaba casi todo construido; faltaba el **gate de tokens** (usar AIXL solo si ahorra y es seguro), que ahora existe y es verificado.
2. Con la sintaxis AIXL 0.3, **una instrucción humana suelta casi nunca ahorra tokens** (2% del dev set, 0 de 1468 mensajes reales con el gate estricto).
3. El valor medido de AIXL es **detectar pérdida y verificar equivalencia**, no comprimir.
4. El 95.6% de los tokens de tu tráfico está en mensajes largos pegados, y el 79% del texto de las sesiones son salidas de herramientas: ahí está la palanca real.
5. Las **referencias a contenido ya enviado** ahorran 17.3% del texto de tus sesiones y no degradan a un modelo fuerte (Sonnet), pero **sí degradan a uno débil (Haiku)**.

## 2. Qué se construyó (todo con tests; suite 1084 pasan)
| Pieza | Archivo | Qué hace |
|---|---|---|
| Gate de tokens | `aixl/gate.py` | MODE=NATURAL salvo que: ahorre tokens, el fingerprint sobreviva la vuelta y la codificación sea completa. Incluye `strict_complete` y la lista `AFFIRM`. |
| Forma telegráfica (opción A) | `aixl/telegraph.py` | `analyze sales q1-2026`; vocabulario cerrado de la ontología; palabra desconocida falla cerrado. |
| Almacén de referencias (opción C) | `aixl/refstore.py` | Bloques ya enviados en la conversación → puntero `⟦=msg:a-b⟧`, verificado por decodificación. |
| Benchmarks | `benchmarks/v1_*.py` | dev set, tráfico real, telegráfico, refstore, calidad y razonamiento con punteros. |

## 3. Defectos reales encontrados y corregidos
- **Gate de tokens ausente**: el wire AIXL era más largo que el texto.
- **"Hola" → AIXL vacío** (sobrecodificación).
- **Pérdida silenciosa**: "…conserva solamente lo más importante" se descartaba sin aviso.
- **Mensajes cortos**: `check_completeness` eximía la *primera* palabra como "verbo" (así "creo que ya revisa" → `A:CHECK`) y daba por contabilizada cualquier palabra conocida aunque no estuviera en el grafo ("redacta el correo" → `A:GENERATE`). Corregido con `strict_complete`: el verbo exento es el que la regex de acciones detectó, y el resto de palabras debe estar en el grafo.
- **Afirmaciones descartadas**: "sí muestrame" → `A:GET`. Corregido con `AFFIRM`.
- Mis propios bugs, atrapados por la verificación de fingerprint: decodificador telegráfico (abreviaturas y mayúsculas) y un calificador con prefijo `N<tab>`.

## 4. Resultados medidos
**Gate (tokenizador real o200k_base, no el de Claude).**
- Dev set (228 textos propios): AIXL en 5 casos (2%), ahorro medio 16.4%.
- Tráfico real (1468 mensajes tuyos): **6 → 1 → 0** usos conforme se cerraron los huecos; los 6 primeros eran pérdidas disfrazadas de ahorro.

**Diccionario de sesión y átomos nuevos (prompt §10/§21).** Diccionario: 11.7% (3 msgs), 18.4% (5), 27% (10), en sesiones construidas para repetir objetivo. Átomos abreviados: de ≈2% a ≈4% de uso, con partición derivar/evaluar. Marginales; no integrados.

**Opción A — telegráfico.** Dev set: 128/225 usables (57%), **40.8% menos tokens**, 0 desajustes de fingerprint. Tráfico real: 4/1629 (0.25%). Fuera de la ontología no aplica.

**Opción C — referencias.** 409 sesiones, 43.7M caracteres: salidas de herramientas 79%, mensajes tuyos 13%, texto del asistente 8%. **17.3% del texto ahorrado** (19.9% en salidas de herramientas), 7899 bloques, 0 fallos de ida y vuelta. En los bloques codificados, −47.4% de tokens.

**Opción C — ¿el modelo entiende los punteros?**
| Prueba | Texto completo | Punteros (leyenda / sin leyenda) |
|---|---|---|
| Línea exacta, Sonnet (24 preguntas) | 23/24 | 22/24 · 24/24 |
| Razonamiento, Sonnet (60) | 52/60 | 59/60 · 59/60 |
| Razonamiento, Haiku (60) | 27/60 | 14/60 · 18/60 |

Fallo observable: contar líneas a través de un puntero (Q2/Q3 de Haiku se derrumban).

## 5. Qué sí y qué no se puede afirmar
**Sí:**
- El gate evita emitir AIXL con pérdida de significado en los casos probados.
- La forma telegráfica ahorra ~41% en instrucciones estructuradas que la ontología cubre, sin pérdida respecto al grafo.
- Los punteros ahorran ~17% del texto de las sesiones y un lector fuerte los usa bien.

**No:**
- Que AIXL comprima tráfico conversacional real (no lo hace).
- Que los punteros sirvan a cualquier receptor: con Haiku empeoran.
- Que el ahorro de tokens se traduzca igual en factura: el prompt caching lo reduce (no medido).
- Equivalencia semántica fuera del dominio acotado: sigue valiendo lo medido antes (árbitro 2-de-2).

## 6. Límites generales de las mediciones
Corpus de dev propio (mismo autor que el código); tokenizador de OpenAI como aproximación; una corrida por celda, 2 modelos, 20–24 casos en las pruebas con modelos; subagentes con instrucción (no obligación técnica) de no usar herramientas de cómputo, aunque cada uno registró solo 2 llamadas de lectura; fidelidad telegráfica solo respecto al grafo del traductor; sin pruebas de edición/resumen, cadenas de punteros ni almacén compartido entre sesiones.

## 7. Siguientes pasos recomendados (por valor/riesgo)
1. **Opción E**: enviar texto natural + huella semántica de ~16 caracteres y verificar al recibir; es lo que AIXL ya hace mejor.
2. **Compuerta por capacidad** para punteros (solo receptores fuertes) o una herramienta de expansión bajo demanda.
3. Medir con el **tokenizador y la facturación reales** (caché incluida) antes de prometer ahorro.
4. Probar punteros en **tareas de edición/resumen** y con cadenas de punteros.
5. Opcional: almacén compartido entre sesiones (hoy solo dentro de una conversación).

## 8. Addendum: next steps 1–5 (completed 2026-10-08)
| Paso | Resultado | Archivo |
|---|---|---|
| 1. Opción E (sobre de integridad) | 0 falsas alarmas en 58 paráfrasis; negación 128/128, acción 89/89 detectadas; verificable solo en 1.2% del tráfico real | `aixl/envelope.py` |
| 2. Compuerta por capacidad | Punteros anotados no rescatan a Haiku (14/60); Sonnet 60/60; política que falla cerrado | `aixl/refpolicy.py` |
| 3. Tokens/facturación reales | 98.7% de tokens son lecturas de caché (82.8% del costo); Claude ≈ 0.47 tok/carácter; punteros ≈ 17–27% del costo ponderado (modelo, no factura) | `benchmarks/v1_billing_eval.py` |
| 4. Edición, extracción, cadenas | Opus 40/40 con punteros (edit 10/10, extract 10/10, cadenas 20/20); **Sonnet bloqueado por un clasificador de seguridad → desconocido**; Opus agregado a la lista | `benchmarks/v1_refedit_*.py` |
| 5. Almacén entre sesiones (potencial) | mismo proyecto +7.3 pts de caracteres (+2.8 pts de costo); entre proyectos solo +0.4 pts → no construir un almacén global | `benchmarks/v1_crosssession_eval.py` |

Receptores con punteros permitidos: Sonnet, Opus (medidos). Haiku: no. Fable y modelos no medidos: texto plano (falla cerrado).
