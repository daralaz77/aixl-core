"""Aggregate every existing real-teacher (text -> AIXL) pair already generated in this project's prior
experiments (E-XV sets 6-9, E-INTEROP, the original blind3/blind4 cloud-route accuracy measurements)
into one deduped, validated distillation training corpus, at zero new API cost.

blind5 is deliberately EXCLUDED: it was spent on 2026-10-01 as the honest zero-shot baseline for the
self-hosted qwen2.5:1.5b-instruct model (F1 0.06 vs the rule-based translator's 0.88) and must stay
untouched so it can measure the FINE-TUNED student on the exact same held-out set for an apples-to-apples
comparison. interop1 texts didn't match any tid in its own answer files (different id scheme) and
contributed 0 pairs — harmless, just unused, not worth chasing given 1417 pairs already cleared the
~500-example LoRA minimum several times over.

usage: python distill/build_corpus.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from aixl.serialization import aixl_codec

SOURCES = [
    ("data/llm_translator/texts_set6.json", ["data/xv/answers6_sonnet.txt"]),
    ("data/llm_translator/texts_set7.json", ["data/xv/answers7_sonnet.txt", "data/xv/answers7_sonnet_1.txt", "data/xv/answers7_sonnet_2.txt"]),
    ("data/llm_translator/texts_set8.json", ["data/xv/answers8_sonnet.txt", "data/xv/answers8b_sonnet.txt", "data/xv/answers8_sonnet_1.txt", "data/xv/answers8_sonnet_2.txt"]),
    ("data/llm_translator/texts_set9.json", ["data/xv/answers9_sonnet.txt", "data/xv/answers9_sonnet_1.txt", "data/xv/answers9_sonnet_2.txt"]),
    ("data/interop/texts_interop1.json", ["data/interop/sonnet_answers.txt", "data/interop/gemini_answers_raw.txt"]),
    ("data/llm_translator/texts_blind3.json", ["data/llm_translator/answers/sonnet_1.txt", "data/llm_translator/answers/sonnet_2.txt",
                                                "data/llm_translator/answers/haiku_1.txt", "data/llm_translator/answers/haiku_2.txt"]),
    ("data/llm_translator/texts_blind4.json", ["data/llm_translator/answers4/sonnet_1.txt", "data/llm_translator/answers4/sonnet_2.txt",
                                                "data/llm_translator/answers4/haiku_1.txt", "data/llm_translator/answers4/haiku_2.txt"]),
]


def read_answers(path):
    d = {}
    for l in open(os.path.join(ROOT, path), encoding="utf-8"):
        m = re.match(r"^\s*(t\d{3})\s*::\s*(.+?)\s*$", l)
        if m:
            d[m.group(1)] = m.group(2).strip("`")
    return d


def main():
    pairs = {}
    stats = {"seen": 0, "parse_ok": 0, "parse_fail": 0}
    per_source = []

    for texts_file, answer_files in SOURCES:
        with open(os.path.join(ROOT, texts_file), encoding="utf-8") as f:
            texts = json.load(f)
        by_tid = {t["tid"]: t["text"] for t in texts}
        src_added = 0
        for af in answer_files:
            ans = read_answers(af)
            for tid, text in by_tid.items():
                if text in pairs:
                    continue
                line = ans.get(tid)
                if not line:
                    continue
                stats["seen"] += 1
                try:
                    aixl_codec.decode(line)
                except aixl_codec.AixlError:
                    stats["parse_fail"] += 1
                    continue
                stats["parse_ok"] += 1
                pairs[text] = line
                src_added += 1
        per_source.append((texts_file, src_added))

    out_path = os.path.join(ROOT, "distill", "corpus.jsonl")
    with open(out_path, "w", encoding="utf-8") as out:
        for text, aixl in pairs.items():
            out.write(json.dumps({"text": text, "aixl": aixl}, ensure_ascii=False) + "\n")

    for name, n in per_source:
        print(f"  {name}: {n}")
    print("stats:", stats)
    print("total unique (text, aixl) pairs:", len(pairs))
    print("written to:", out_path)


if __name__ == "__main__":
    main()
