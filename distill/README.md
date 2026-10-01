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
