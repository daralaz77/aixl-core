"""Calls the real cloud LLM route (aixl/translators/llm_translator.py, now with prompt caching) to label
every text in distill/fresh_texts.json with its real AIXL encoding -- the actual data-generation step
for the fresh (non-recycled) training corpus. For EQUIVALENT pairs, both sides are labeled independently
first, then the pair's shared target is resolved the same way build_consistency_corpus.py already does
(prefer side a's label if it decodes, else side b's) so the two outputs feed the same proven
consistency-training mechanism.

usage: ANTHROPIC_API_KEY=sk-ant-... python distill/label_fresh_corpus.py [--limit N]
Writes distill/corpus_fresh.jsonl -- same {"text", "aixl"} schema as distill/corpus.jsonl, ready to merge.
"""
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aixl.serialization import aixl_codec
from aixl.translators.llm_translator import translate_via_llm


def label(text, api_key):
    g = translate_via_llm(text, api_key=api_key, timeout=20.0)
    if g is None:
        return None
    return aixl_codec.encode(g)


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set"); sys.exit(1)

    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    data = json.load(open(os.path.join(ROOT, "distill", "fresh_texts.json"), encoding="utf-8"))
    items = data["items"][:limit] if limit else data["items"]
    pairs = data["pairs"][:limit // 4] if limit else data["pairs"]

    results = {}  # text -> aixl
    t0 = time.time()
    total = len(items) + 2 * len(pairs)
    done = 0

    def process(text):
        nonlocal done
        if text in results:
            return
        aixl = label(text, api_key)
        results[text] = aixl
        done += 1
        if done % 25 == 0 or done == total:
            elapsed = time.time() - t0
            print(f"[{done}/{total}] {elapsed:.0f}s elapsed, ok={sum(1 for v in results.values() if v)}", flush=True)

    for item in items:
        process(item["text"])
    for p in pairs:
        process(p["a"])
        process(p["b"])

    # resolve consistency pairs: force both sides to the same (valid) target
    forced = 0
    for p in pairs:
        a_label, b_label = results.get(p["a"]), results.get(p["b"])
        canonical = a_label or b_label
        if canonical is None:
            continue
        if results.get(p["a"]) != canonical or results.get(p["b"]) != canonical:
            forced += 1
        results[p["a"]] = canonical
        results[p["b"]] = canonical

    out_path = os.path.join(ROOT, "distill", "corpus_fresh.jsonl")
    n_ok = 0
    with open(out_path, "w", encoding="utf-8") as out:
        for text, aixl in results.items():
            if aixl is None:
                continue
            out.write(json.dumps({"text": text, "aixl": aixl}, ensure_ascii=False) + "\n")
            n_ok += 1

    print(f"\nlabeled {n_ok}/{len(results)} texts successfully ({forced} pairs forced to a shared target)")
    print(f"written to {out_path}")


if __name__ == "__main__":
    main()
