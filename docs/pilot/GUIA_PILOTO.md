# Guía del piloto de medición (4–6 semanas)

**Qué se mide:** con qué frecuencia cambia el significado de una instrucción cuando pasa de un agente a otro agente o a una persona, en UN flujo que elige el socio.
**Qué se entrega al final:** un informe con la tasa real de cambio, su intervalo de confianza, el tipo de datos que cambian y la decisión según la regla acordada (< 4 % parar · 4–15 % pivotar · ≥ 15 % seguir).
**Qué NO se hace:** no se evalúa a personas ni a agentes, no se entrena ningún modelo, no se publica nada que identifique al socio sin autorización escrita.

## Calendario
| Semana | Qué pasa | Quién |
|---|---|---|
| 0 | Acuerdo de confidencialidad firmado (revisado por abogado). Se elige el flujo y se fija la regla de decisión por escrito, **antes** de medir. | Ambos |
| 1 | El socio entrega 200–300 pares anonimizados (Anexo A del acuerdo) y firma la confirmación de anonimización. | Socio |
| 1–2 | Análisis automático (offline, sin modelo) y hoja de etiquetado. | Daralaz |
| 2–3 | **Dos personas etiquetan, cada una por separado,** la hoja (≈ 120 pares). Idealmente una del socio y una de Daralaz. | Ambos |
| 4 | Informe borrador. Si el resultado es no concluyente, se amplía la muestra etiquetada (otros 120 pares). | Daralaz |
| 5–6 | Informe final, decisión, **borrado de la muestra** y confirmación por escrito. | Ambos |

## Formato de entrega de los datos
Un archivo `pairs.jsonl`, una línea por traspaso:
`{"id": "T001", "source": "<lo que dijo el agente o el cliente>", "relay": "<lo que recibió el siguiente>", "flow": "<nombre del flujo>"}`
Sin nombres, documentos, cuentas, teléfonos ni correos (marcas neutras `[PERSONA_1]`, `[DOC]`…). Las cifras, fechas y condiciones **se conservan**: son lo que se mide.

## Comandos (en el equipo cifrado de Daralaz, sin conexión de los datos a terceros)
```bash
python -m benchmarks.pilot_report analyze pairs.jsonl --out piloto/ --sample 60
#  -> piloto/results.jsonl y piloto/labeling_sheet.csv (60 señalados + 60 no señalados, mezclados)
#  Cada etiquetador devuelve un CSV con dos columnas: id,label   (label = CAMBIO o IGUAL)
python -m benchmarks.pilot_report report piloto/ etiquetador1.csv --labels2 etiquetador2.csv --partner "NOMBRE DEL SOCIO"
#  -> piloto/informe.md
```
El árbitro de dos jueces es opcional y **solo con autorización escrita del socio** (usa modelos externos, con las claves del socio): `--judges juez1.tsv juez2.tsv`.

## Cómo etiquetar (para las dos personas)
Para cada fila compara **origen** y **reenvío** y responde:
- **CAMBIO** si el reenvío haría que quien lo recibe actúe distinto: se perdió o invirtió una negación, cambió una cifra, fecha u hora, desapareció o cambió una condición, cambió quién hace qué o a quién, cambió el alcance (todos/algunos, solo/también), o se añadió o quitó una instrucción.
- **IGUAL** si quien recibe actuaría igual, aunque las palabras sean otras, el orden cambie o falte un detalle sin consecuencias.
- Ante la duda razonable: **CAMBIO** y anota el motivo en la hoja (columna libre). No hay "no sé".
No miren qué pares marcó el detector: la hoja viene mezclada y sin esa información. No comenten las respuestas hasta entregar ambas.

## Ejemplos de etiquetado
| Origen | Reenvío | Etiqueta |
|---|---|---|
| No me llamen después de las 6 pm | Cliente pide llamadas después de las 6 pm | CAMBIO (negación) |
| No me llamen después de las 6 pm | El cliente solicita que no se le contacte después de las 18:00 | IGUAL |
| Cancelo solo si no me aplican el descuento del 30 % | Cliente cancela el servicio | CAMBIO (condición) |
| Pague en catorce días | Pague en 14 días | IGUAL |
| Pague en catorce días | Pague en quince días | CAMBIO (cifra) |

## Cómo leer el resultado
- La **tasa real** no es la proporción de alertas: se estima con las etiquetas humanas (precisión de las alertas + cambios que el detector no vio).
- El informe dice **"no concluyente"** cuando el intervalo cruza un umbral (4 % o 15 %): en ese caso se amplía la muestra etiquetada; no se decide.
- Si el desacuerdo entre las dos personas es alto (> 15 % de los pares), la definición de CAMBIO no está clara: se aclara en una reunión y se re-etiqueta.

## Qué puede salir mal
| Riesgo | Mitigación |
|---|---|
| La muestra no representa el flujo | Que el socio la saque al azar de un período (no "casos interesantes"); documentar cómo la eligió |
| Las alertas son muchas y falsas (resúmenes que reformulan) | Es esperable: por eso la tasa se estima con etiquetas; si el flujo reformula siempre, el árbitro es la herramienta |
| Datos personales en la muestra | Se suspenden, se avisa y se borran (cláusula 5 del acuerdo) |
| Se mueve la regla de decisión tras ver los datos | Queda firmada en la semana 0 |
