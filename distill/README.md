# Traductor AIXL propio — distillation hacia un modelo pequeño self-hosted

## Por qué existe esto

El traductor por reglas se estancó en ~88% (E-XV/E-CODEC/E-DATE). La ruta cloud (Anthropic/OpenAI/Gemini vía `card_0.3.md` como prompt) mide 93.5-96.5% pero depende de una API de pago por llamada — no es "propio".

Primer intento de self-hosting en este Mac (Apple M1, 8GB RAM):
- `qwen2.5:7b-instruct` vía Ollama: nunca completa una generación (se queda colgado, probablemente por falta de RAM).
- `qwen2.5:1.5b-instruct` vía Ollama, usando `card_0.3.md` completo como system prompt (igual que la ruta cloud): rápido (1-4s/petición), pero **F1 = 0.06** contra el blind set 5 — el modelo es demasiado pequeño para seguir de forma confiable un prompt de ~19.500 caracteres; inventa campos y genera acciones contradictorias.

## El camino elegido: distillation

En vez de pedirle al modelo pequeño que lea la tarjeta completa en cada petición, le enseñamos las reglas por fine-tuning (LoRA), con una instrucción corta fija en inferencia. Esto además lo hace más rápido (menos tokens de prompt).

### 1. Corpus de entrenamiento — `corpus.jsonl` (`build_corpus.py`)

1417 pares (texto → AIXL correcto) reunidos de experimentos previos del proyecto (E-XV sets 6-9, E-INTEROP, las mediciones originales blind3/blind4) — **cero costo nuevo de API**, ya estaban pagados y verificados contra el comparador real.

`blind5` queda **intacto** a propósito: es el set que ya usamos para medir el modelo base sin fine-tuning (F1 0.06), así que sirve como comparación limpia y honesta para el modelo afinado.

Regenerar el corpus si cambian las fuentes:
```bash
python distill/build_corpus.py
```

### 2. Fine-tuning — `train_colab.ipynb`

Este Mac no tiene GPU CUDA, así que el entrenamiento no puede correr aquí. El notebook está listo para **Google Colab, GPU T4 gratis** (sin necesidad de crear cuentas de pago ni tarjetas de crédito):

1. Abre `train_colab.ipynb` en [Google Colab](https://colab.research.google.com/) (subir el archivo, o `Archivo > Subir notebook`).
2. `Entorno de ejecución > Cambiar tipo de entorno de ejecución` → GPU (T4).
3. Ejecuta las celdas en orden. Cuando pida un archivo, sube `distill/corpus.jsonl`.
4. Entrena `Qwen2.5-1.5B-Instruct` con QLoRA (~10-20 min en T4 para 1417 ejemplos, 4 épocas).
5. Exporta a GGUF cuantizado (`q4_k_m`) y lo descarga automáticamente al navegador.

### 3. Servir localmente con Ollama

```bash
# mueve el .gguf descargado a esta carpeta, luego:
cat > distill/Modelfile << 'EOF'
FROM ./aixl-qwen15-distilled.gguf
SYSTEM """You are an AIXL 0.3 encoder. Given an instruction in Spanish, English or Portuguese, output its AIXL encoding as exactly one line starting with V:AIXL-0.3. Output only that line, nothing else."""
EOF
cd distill && ollama create aixl-distilled -f Modelfile
```

### 4. Medición honesta — `eval_distilled.py`

```bash
python distill/eval_distilled.py aixl-distilled
python -m benchmarks.llm_translator_eval aixl-distilled distill/answers_aixl-distilled.txt --set5
```

Compara el F1 resultante contra:
- Reglas: 88%
- Base 1.5B sin fine-tuning (mismo blind5): F1 0.06
- Ruta cloud (Sonnet/Haiku/Gemini/ChatGPT vía card): 93.5-96.5%

Si el resultado se acerca al rango 90-95%, este modelo fine-tuned pasa a ser una tercera opción real en `aixl/translators/auto.py` (modo `AIXL_TRANSLATOR_MODE=local`, pendiente de implementar una vez haya un número real que justifique el trabajo). Si se queda muy por debajo, el corpus de 1417 ejemplos es probablemente insuficiente y el siguiente paso sería generar más pares sintéticos o probar un modelo base un poco más grande (3B) con QLoRA en el mismo notebook.

## Resultado real (2026-10-01, primera corrida)

Qwen2.5-1.5B-Instruct + LoRA (r=16, 4 épocas, 1276 ejemplos de entrenamiento, 141 de validación), exportado a GGUF q4_k_m, servido vía Ollama, medido contra blind5 con la misma metodología que las otras dos rutas:

| Ruta | F1 (blind5) | Formato válido |
|---|---|---|
| Reglas | 0.88 (aprox., otra metodología) | 100% |
| 1.5B zero-shot (card completa como prompt) | **0.06** | 91% (364/400) |
| **1.5B fine-tuned (distillation, prompt corto)** | **0.6056** | **100% (400/400)**, 10 fallos de decode estricto |
| Cloud (Sonnet/Haiku/Gemini/ChatGPT vía card) | 0.935–0.965 | ~100% |

Pérdida de entrenamiento: 0.354 train / 0.220 val (4 épocas, sin señal de overfitting — val loss bajó en paralelo con train loss).

**Lectura honesta**: el salto de 0.06 → 0.6056 (10x) prueba que la distillation es el camino correcto — el modelo pasó de "roto" a "funcional". Pero todavía está lejos del 90-95% objetivo y de las otras dos rutas. El parseo sintáctico llegó a 100%, así que los errores restantes son semánticos (elige el verbo/campo equivocado), no de formato. Candidatos para la siguiente vuelta: más datos de entrenamiento (1417 ejemplos es el mínimo citado en la literatura, no el óptimo), más épocas, o un modelo base un poco más grande (3B) con el mismo pipeline de Colab.

El `.gguf` entrenado NO se versiona en git (956MB, demasiado grande) — `distill/*.gguf` está en `.gitignore`. Para reproducir: repetir el notebook de Colab con `corpus.jsonl` (sí versionado).

## Segunda vuelta (2026-10-02): GPU real + corpus ampliado — bug de exportación sin resolver

El usuario invirtió en Colab Pro (GPU A100) y dio una API key propia, de un solo uso, para generar un corpus genuinamente nuevo (no reciclado) via la ruta cloud real.

**Corpus**: `corpus_merged.jsonl`, 4031 líneas = `corpus_consistent.jsonl` (3017, de la primera vuelta) + `corpus_fresh.jsonl` (2614 textos nuevos, generados con `distill/generate_fresh_texts.py` + etiquetados con `distill/label_fresh_corpus.py`, 2619 llamadas reales, 99.8% de éxito). Antes de fusionar, un spot-check encontró y corrigió dos bugs reales de consistencia del maestro sin gastar llamadas extra (`distill/fix_recipient_consistency.py`, determinístico):
- Destinatarios (`Y:`) codificados de forma distinta según el idioma de la frase (`@GERENTE` en ES/PT vs `@MANAGER` en EN) — se forzó un token canónico único por referente real, independiente del idioma.
- Acción `SEND` espuria añadida solo por mencionar un destinatario, violando la regla explícita de la tarjeta (línea 36: solo el verbo principal decide la acción) — eliminada en los 371 casos afectados.

**Entrenamiento**: Qwen2.5-3B-Instruct + LoRA (r=32, lora_alpha=32, batch efectivo 32, 8 épocas, 912 pasos) en A100, loss final 0.084 train / 0.241 val. El sanity-check dentro de la sesión de Colab (modelo PyTorch en memoria, antes de exportar) dio salidas correctas: `"Analiza las ventas de Q1 2026." -> V:AIXL-0.3 I:REQUEST_ANALYSIS A:ANALYZE D:SALES T:Q1-2026`.

**Bug real, sin resolver**: la exportación a GGUF (`model.save_pretrained_gguf(..., quantization_method="q4_k_m")`) se completó sin errores y el archivo pasó una verificación de integridad en tres puntos (SHA256 idéntico en Colab, en el Mac vía `shasum`, y en la capa que registra Ollama) — así que NO es corrupción de transferencia. Pero el modelo servido por Ollama produce salidas incoherentes (repite fragmentos del system prompt, nunca genera AIXL válido), incluso con el prompt ChatML crudo (`raw: true`, sin pasar por el TEMPLATE de Ollama). Se intentó aislar si el bug está en el merge LoRA→fp16 o en la cuantización/conversión GGUF cargando el merge limpio (`model.save_pretrained_merged(save_method="merged_16bit")`) de forma independiente, pero no se pudo verificar: cargarlo con `transformers` puro choca con los parches globales de Unsloth (`AttributeError` en `max_seq_length`, luego `rotary_emb`), y cargarlo con el propio `FastLanguageModel` de Unsloth funcionó pero no fue posible leer el resultado de la generación por fallas repetidas del entorno de Colab/navegador (lectura de outputs en iframe, descarga del `.ipynb` rota tras varios intentos).

**Decisión**: no se midió un F1 real para esta vuelta — no se inventa un número. La ruta cloud (93.5-96.5%, ver tabla arriba) sigue siendo la de producción (`AIXL_TRANSLATOR_MODE=llm`). El modelo auto-hospedado queda pausado como "entrenamiento probadamente correcto, exportación con bug sin diagnosticar" — candidato a retomar en una sesión de Colab fresca (runtime limpio, sin el conflicto de parches de Unsloth) cuando se priorice de nuevo.


## Tercera vuelta (2026-10-02): pipeline autoverificable — el bug de GGUF quedó resuelto

**Diagnóstico**: `llama.cpp` directo sobre el GGUF viejo (sin Ollama) también daba basura, así que el archivo exportado por Unsloth estaba roto; el fallo estaba en el camino Unsloth + base 4-bit + merge/export, no en el aprendizaje ni en Ollama. Entrenar en el Mac con MLX se descartó con medición: ~99 tok/s en un M1 (límite de cómputo, ~2.4 h por época del 1.5B).

**Solución**: `distill/colab/pipeline.py` (un solo comando en Colab; `make_bundle.py` empaqueta código real del comparador + blind5 + datos). Entrena LoRA sobre base **bf16** con PEFT (sin Unsloth ni 4-bit), mide F1 real en blind5 en cada etapa (adaptador -> fusionado y recargado desde disco -> GGUF), y exporta con el conversor de llama.cpp. Datos: `build_mlx_data.py` canonicaliza cada etiqueta con el codec real (1350 de 4031 venían en serializaciones distintas del mismo significado) y mantiene el sobremuestreo x3 de pares equivalentes.

**Resultado real** (Qwen2.5-3B-Instruct, r=32, 3 épocas, 1398 pasos, 8.4 min en A100, blind5, 200 pares):

| Etapa | F1 | Precisión | Recall |
|---|---|---|---|
| Referencia anterior (1.5B, Unsloth, medido en Ollama) | 0.693 | 0.946 | 0.546 |
| Adaptador bf16 | 0.773 | 0.955 | 0.650 |
| Fusionado y recargado (bf16) | 0.745 | 0.938 | 0.619 |
| **GGUF Q4_K_M servido localmente (llama-server)** | **0.726** | 0.950 | 0.588 |

SHA256 del GGUF verificado igual en Colab y en el Mac. 400/400 respuestas con línea AIXL; 7 fallos de decodificación estricta; detección de deriva crítica 93.4 %. Pérdida por fusionar (bf16) ~0.03 F1 y por cuantizar Q4_K_M ~0.02.

**Dónde está el techo ahora**: de los 43 errores, 30 son pares `EQUIVALENT/PARAPHRASE` que el modelo codifica distinto (recall); la precisión ya es 0.95. Próximas palancas medibles: más pares parafraseados con objetivo forzado idéntico, más épocas/rango, fusión en fp32 y Q8_0, y un 7B en Colab como cota superior. Nota metodológica: blind5 se usa como set de desarrollo; cada iteración extra sobre él reduce su valor como medida independiente.


## Cuarta vuelta (2026-10-02): datos de paráfrasis con consenso

`distill/gen_paraphrase_groups.py`: para 1200 semillas del corpus ya validado (nunca de blind5) Haiku genera 3 variantes de igual significado (traducciones a los otros 2 idiomas + reformulación), el maestro cloud etiqueta las 4, y el comparador del propio proyecto elige la etiqueta por mayoría; se descartan los miembros discrepantes y los grupos sin mayoría (597 de 1200 sobreviven, 2074 textos), y todos los miembros se fuerzan a la MISMA etiqueta canónica y se sobremuestrean x3. Que el maestro necesite descartar la mitad de los grupos mide su propia inconsistencia entre idiomas. 80 grupos (279 textos) quedan fuera del entrenamiento como set de desarrollo propio, para no seguir iterando sobre blind5. Costo real de API: ~6000 llamadas con Haiku 4.5.

Mismo modelo y receta (Qwen2.5-3B, r=32, 3 épocas), 11 668 filas de entrenamiento:

| Etapa | F1 | Precisión | Recall | Exactitud |
|---|---|---|---|---|
| Ronda 3 (sin paráfrasis) GGUF local | 0.726 | 0.950 | 0.588 | 0.785 |
| Adaptador bf16 | **0.833** | 0.986 | 0.722 | - |
| Fusionado y recargado | 0.819 | 0.986 | 0.701 | 0.850 |
| **GGUF Q4_K_M local (llama-server)** | **0.775** | 0.984 | 0.639 | 0.820 |

Set de desarrollo (grupos retenidos): 0.785 de equivalencia con el adaptador. SHA256 del GGUF idéntico en Colab y en el Mac. 11 fallos de decodificación estricta; deriva crítica 58/61. Pérdida por empaquetar: fusionar ~0.014 F1, cuantizar a Q4_K_M ~0.044 F1. Errores restantes (43 -> 36): 26 siguen siendo parafraseos equivalentes codificados distinto; solo 1 falso positivo.

Referencia de techo (memoria del proyecto): los encoders cloud con la tarjeta completa miden en blind5 una EXACTITUD de 96.5 % (Haiku/Sonnet), 95.0 % (Gemini), 93.5 % (ChatGPT). Ningún sistema medido ha superado 96.5 % en ese set.


## Quinta vuelta (2026-10-02): barrido de empaquetado + decodificación con gramática

`distill/colab/sweep.py` mide en la A100, con el `llama-server` CUDA y el prompt exacto de entrenamiento, 8 variantes del MISMO adaptador: fusión bf16 o fp32 x {Q4_K_M, Q6_K, Q8_0, f16}. Luego se repite con una gramática GBNF (`distill/aixl_grammar.py` -> `distill/aixl.gbnf`, derivada solo de los corpus de entrenamiento) que hace imposibles los fallos de formato (átomos inventados, `V:AIXL-1.0`, duplicados) y cierra los vocabularios de I/A/D/E/P/G/O.

| Config | F1 sin gram. | F1 con gram. | Exactitud con gram. | Dev con gram. | Fallos de parseo (sin -> con) | GB |
|---|---|---|---|---|---|---|
| fp32 Q8_0 | 0.793 | 0.790 | 0.825 | 0.778 | 16 -> 0 | 3.29 |
| bf16 Q4_K_M | 0.755 | 0.788 | 0.825 | 0.767 | 7 -> 0 | 1.93 |
| fp32 f16 | 0.793 | 0.783 | 0.820 | 0.778 | 15 -> 1 | 6.18 |
| fp32 Q4_K_M | 0.805 | 0.783 | 0.825 | 0.760 | 7 -> 0 | 1.93 |
| bf16 Q8_0 | 0.770 | 0.776 | 0.815 | 0.778 | 13 -> 1 | 3.29 |
| bf16 f16 | 0.785 | 0.776 | 0.815 | 0.778 | 14 -> 1 | 6.18 |
| fp32 Q6_K | 0.755 | 0.765 | 0.810 | 0.781 | 13 -> 0 | 2.54 |
| bf16 Q6_K | 0.755 | 0.761 | 0.805 | 0.778 | 12 -> 0 | 2.54 |

Lectura honesta:
- El ruido de medición es ~±0.02 F1 (1 par = 0.005 de exactitud). Las 8 variantes con gramática caen en 0.761-0.790: **no hay una ganadora real**; la precisión y la fusión (bf16/fp32) no importan a este nivel. Se conserva **Q4_K_M** (1.93 GB), que con gramática en el Mac midió F1 0.788 / exactitud 0.825, idéntico al valor de Colab.
- La gramática elimina los fallos de formato (de 7-16 a 0-1) y da ~+0.01-0.03 F1; ya no es el cuello de botella.
- El cuello es el **recall** (0.64-0.68) con precisión 0.94-0.98: el modelo codifica distinto parafraseos equivalentes. Es un problema semántico de generalización, no de empaquetado ni de formato.
- Experimento de empaquetado (paso 1): perder 0.04-0.06 F1 entre adaptador (0.833) y GGUF no se debe a la precisión numérica, y queda al nivel del ruido.


## Sexta vuelta (2026-10-02): recetas (épocas, rank, 7B) y normalizador determinista

Mismos datos (11 668 filas), misma gramática, Q4_K_M fusionado en bf16, blind5 + dev retenido (`distill/colab/sweep.py --rank/--epochs/--model`):

| Receta | Adaptador F1 | Adaptador dev | GGUF+gram. F1 | P | R | Exact. | Dev | GB |
|---|---|---|---|---|---|---|---|---|
| 3B, r32, 3 épocas (base) | 0.833 | 0.785 | 0.788 | 0.956 | 0.670 | 0.825 | 0.767 | 1.93 |
| 3B, r64, 5 épocas | 0.765 | 0.785 | 0.778 | 0.969 | 0.649 | 0.820 | 0.756 | 1.93 |
| 7B (Qwen2.5-7B), r32, 3 épocas | 0.821 | 0.785 | 0.793 | 0.970 | 0.670 | 0.830 | 0.774 | 4.68 |

Conclusión (con datos): **ninguna receta mueve la aguja**. Más épocas y más rank sobreajustan (pérdida final 0.002, dev sin cambio). Un modelo 2.3x mayor tampoco mejora (+0.005 F1, dentro del ruido de ±0.02) y las 3 recetas dan exactamente el mismo dev del adaptador (0.785). El techo ~0.79 F1 / 0.83 exactitud no es de capacidad ni de empaquetado ni de formato: es de **datos** (qué paráfrasis equivalentes ve el modelo y qué tan consistente es la etiqueta que se le enseña). No se descargó el 7B: no gana lo suficiente para justificar 4.7 GB en un Mac de 8 GB.

### Normalizador determinista: descartado con evidencia
Análisis campo a campo de los 32 falsos negativos de blind5 (GGUF Q4_K_M + gramática): las diferencias se reparten E 12, A 9, G 9, D 9, K 9, I 5, Y 5, F 4, P 4 (un par suele diferir en varios). Son omisiones o adiciones de átomos opcionales y sinónimos de acción (`TRANSLATE` vs `TRANSFORM`), no variantes sintácticas, y el comparador ya ignora los campos derivados (intención, meta). No existe una regla determinista que las repare sin riesgo de crear falsos positivos; la gramática ya cubre los fallos sintácticos. Palancas que quedan: más y mejores datos (paráfrasis nuevas, pares casi-iguales NO equivalentes para sostener la precisión, consenso de varios maestros) y, sobre todo, un set ciego NUEVO: blind5 ya se usó para elegir configuraciones y para decidir 99 % haría falta medir contra un set no visto.
