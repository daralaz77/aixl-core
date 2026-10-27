# Informe del piloto de medición — DEMO (sin socio)

> **EJEMPLO DE DEMOSTRACIÓN, no es un resultado de ningún socio.** Se generó con relays escritos por modelos (los de `data/relays`) y con etiquetas conocidas de antemano, solo para mostrar el formato y comprobar el cálculo.

## 1. Resumen
- **Traspasos analizados:** 279.
- **Tasa real estimada de cambio de significado:** **13.4 %** (intervalo 95 %: 10.4 % – 20.4 %).
- **Decisión según la regla acordada** (< 4 % parar · 4–15 % pivotar · ≥ 15 % seguir): **PIVOTAR** — **no concluyente**: el intervalo cruza un umbral; hay que ampliar la muestra etiquetada antes de decidir.

## 2. Método
Un detector sin modelo y sin conexión revisó cada par (origen → reenvío) y señaló los que cambiaron un dato crítico (negación, cifra, fecha, hora, condición, modalidad, nombre, acción, destinatario…). Como las alertas no son cambios reales, dos personas etiquetaron de forma independiente una muestra aleatoria **estratificada** (pares señalados y no señalados, mezclados y sin saber cuáles eran) como CAMBIO o IGUAL. La tasa real combina la precisión de las alertas y la tasa de cambios que el detector no vio, cada una medida en su estrato.

## 3. Resultados
| Medida | Valor |
|---|---|
| Pares señalados por el detector | 56 de 279 (20.1 %) |
| Etiquetados entre los señalados | 56; de ellos CAMBIO real: 30 → precisión de las alertas 53.6 % (IC 95 %: 40.7 % – 66.0 %) |
| Etiquetados entre los NO señalados | 60; de ellos CAMBIO real: 2 → cambios que el detector no vio 3.3 % (IC 95 %: 0.9 % – 11.4 %) |
| **Tasa real de cambio estimada** | **13.4 %** (IC 95 %: 10.4 % – 20.4 %) |

**Qué tipo de dato cambió** (familias señaladas por el detector, sobre los pares señalados):

| Familia | Pares |
|---|---|
| NEGATION | 10 |
| CONDITION_TEXT | 9 |
| CLAUSES | 8 |
| QUANTITY | 7 |
| PRONOUN | 7 |
| COMPARATOR | 7 |
| NUMBER | 6 |
| ACTION | 6 |
| DISJUNCTION | 5 |
| MODIFIER | 3 |
| ONLY | 3 |
| DELEGATION | 3 |

## 4. Qué significa para el socio
- Si la decisión es **SEGUIR**: hay un problema real y frecuente; el siguiente paso es poner la revisión en el punto del flujo donde más cambia (ver familias).
- Si es **PIVOTAR**: el problema existe pero es moderado; conviene limitarlo a los flujos donde un error cuesta mucho.
- Si es **PARAR**: el significado casi no cambia en este flujo; se cierra el piloto y este informe es el resultado.

## 5. Límites
- La muestra es de un solo flujo y de tamaño limitado; el intervalo muestra cuánto se puede confiar en la cifra.
- Las etiquetas son humanas y pueden discrepar. No se aportó la segunda persona: el acuerdo entre etiquetadores no se pudo medir.
- El detector es para traspasos casi literales; en resúmenes que reformulan genera falsas alarmas (por eso la tasa se estima con las etiquetas y no con las alertas).
- No se evaluó a personas ni a agentes individuales, no se entrenó ningún modelo y no se publica nada que identifique al socio sin su autorización escrita.

## 6. Confidencialidad y borrado
Este informe contiene solo conteos y porcentajes. La muestra y la hoja de etiquetado se suprimen dentro del plazo del acuerdo de confidencialidad y se confirma por escrito.
