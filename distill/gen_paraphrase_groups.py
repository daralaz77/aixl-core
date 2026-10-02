"""Builds cross-lingual PARAPHRASE GROUPS with consensus labels -- the data that attacks the dominant error of the
distilled translator (paraphrase recall: 30 of its 43 blind5 errors were equivalent texts encoded differently).

For each seed text (taken from the already-validated training corpus, never from blind5):
  1. Haiku writes 3 variants with EXACTLY the same meaning: a translation into each of the other two languages
     (ES/EN/PT) + one same-language rewording.
  2. The real teacher (card_0.3.md via translate_via_llm, prompt-cached) labels the seed and every variant.
  3. Consensus with the project's OWN comparator: the label equivalent to the most others is the group's target;
     members whose label disagrees with that majority are DROPPED (a drifted paraphrase or a teacher slip), and
     groups with no majority are dropped. Surviving members are all forced to the SAME canonical target string.
Results are cached per seed (resumable; an interrupted run never repays for finished seeds).

usage: ANTHROPIC_API_KEY_FILE=path python distill/gen_paraphrase_groups.py [--n 1200] [--workers 6] [--limit 20]
"""
import json
import os
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from aixl.core.comparator import compare_graphs  # noqa: E402
from aixl.serialization import aixl_codec  # noqa: E402
from aixl.translators.llm_translator import translate_via_llm  # noqa: E402

CACHE = os.path.join(ROOT, "distill", "paraphrase_cache.jsonl")
MODEL = "claude-haiku-4-5-20251001"
GEN_SYSTEM = (
    "You rewrite short software/data instructions. Given one instruction (Spanish, English or Portuguese), produce "
    "exactly 3 variants that keep the EXACT same meaning, as a JSON object and nothing else: "
    '{"seed_lang":"es|en|pt","variants":[{"lang":"..","text":".."},{"lang":"..","text":".."},{"lang":"..","text":".."}]}. '
    "Variant 1 and 2: faithful translations into each of the OTHER two languages. Variant 3: a natural rewording in the "
    "SAME language as the seed (different wording/word order, same meaning). Hard rules: keep every number, quantity, "
    "date/time expression, #reference id, proper name and file/format name unchanged; keep every negation, condition "
    "(if/when/unless), priority and recipient; do not add, drop or soften anything; keep the imperative register; "
    "one sentence each; no explanations.")


def key():
    kf = os.environ.get("ANTHROPIC_API_KEY_FILE")
    return open(kf).read().strip() if kf else os.environ["ANTHROPIC_API_KEY"]


def call_variants(seed, api_key):
    for attempt in range(4):
        try:
            r = httpx.post("https://api.anthropic.com/v1/messages",
                           headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                           json={"model": MODEL, "max_tokens": 500, "temperature": 0.3, "system": GEN_SYSTEM,
                                 "messages": [{"role": "user", "content": seed}]}, timeout=40)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** attempt * 2)
                continue
            r.raise_for_status()
            txt = r.json()["content"][0]["text"]
            m = re.search(r"\{.*\}", txt, re.S)
            d = json.loads(m.group(0))
            vs = [v["text"].strip() for v in d["variants"] if v.get("text", "").strip()]
            return d.get("seed_lang"), vs
        except Exception:  # noqa: BLE001
            time.sleep(1 + attempt)
    return None, []


def label(text, api_key):
    for attempt in range(4):
        g = translate_via_llm(text, api_key=api_key, timeout=40.0)
        if g is not None:
            return aixl_codec.encode(g)
        time.sleep(1 + attempt)
    return None


def consensus(texts, labels):
    graphs = []
    for l in labels:
        try:
            graphs.append(aixl_codec.decode(l) if l else None)
        except Exception:  # noqa: BLE001
            graphs.append(None)
    n = len(texts)
    agree = [[False] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j and graphs[i] is not None and graphs[j] is not None:
                agree[i][j] = bool(compare_graphs(graphs[i], graphs[j]).equivalent)
    scores = [sum(row) for row in agree]
    best = max(range(n), key=lambda i: (scores[i], i == 0))
    members = [best] + [j for j in range(n) if agree[best][j]]
    if graphs[best] is None or len(members) < n // 2 + 1:
        return None
    return sorted(members), labels[best]


def process(seed, api_key):
    lang, variants = call_variants(seed, api_key)
    texts = [seed] + variants
    labels = [label(t, api_key) for t in texts]
    return {"seed": seed, "seed_lang": lang, "texts": texts, "labels": labels}


def main():
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 1200
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    api_key = key()

    rows = [json.loads(l) for l in open(os.path.join(ROOT, "distill", "corpus_consistent.jsonl"), encoding="utf-8") if l.strip()]
    fresh = [json.loads(l) for l in open(os.path.join(ROOT, "distill", "corpus_fresh.jsonl"), encoding="utf-8") if l.strip()]
    pool = sorted({r["text"] for r in rows})
    pool_fresh = sorted({r["text"] for r in fresh})
    blind5 = {t["text"].strip().lower() for t in json.load(open(os.path.join(ROOT, "data/llm_translator/texts_blind5.json"), encoding="utf-8"))}
    rng = random.Random(7)
    rng.shuffle(pool)
    rng.shuffle(pool_fresh)
    n_fresh = int(n * 0.15)
    seeds = [s for s in pool[: n - n_fresh] + pool_fresh[:n_fresh] if s.strip().lower() not in blind5]
    if limit:
        seeds = seeds[:limit]

    done = set()
    if os.path.exists(CACHE):
        for l in open(CACHE, encoding="utf-8"):
            if l.strip():
                done.add(json.loads(l)["seed"])
    todo = [s for s in seeds if s not in done]
    print(f"seeds {len(seeds)}  cached {len(done)}  to do {len(todo)}  workers {workers}", flush=True)

    lock = threading.Lock()
    counter = {"n": 0}
    t0 = time.time()

    def work(seed):
        rec = process(seed, api_key)
        with lock:
            with open(CACHE, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            counter["n"] += 1
            if counter["n"] % 25 == 0:
                print(f"[{counter['n']}/{len(todo)}] {time.time()-t0:.0f}s", flush=True)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, todo))

    build_output(blind5)


def build_output(blind5):
    out_path = os.path.join(ROOT, "distill", "corpus_paraphrase.jsonl")
    kept_groups = dropped_groups = dropped_members = 0
    seen_text = set()
    with open(out_path, "w", encoding="utf-8") as out:
        for line in open(CACHE, encoding="utf-8"):
            if not line.strip():
                continue
            rec = json.loads(line)
            res = consensus(rec["texts"], rec["labels"]) if len(rec["texts"]) >= 3 else None
            if res is None:
                dropped_groups += 1
                continue
            members, target = res
            try:
                target = aixl_codec.encode(aixl_codec.decode(target))
            except Exception:  # noqa: BLE001
                dropped_groups += 1
                continue
            dropped_members += len(rec["texts"]) - len(members)
            good = [rec["texts"][i] for i in members
                    if rec["texts"][i].strip().lower() not in blind5 and rec["texts"][i] not in seen_text]
            if len(good) < 2:
                dropped_groups += 1
                continue
            kept_groups += 1
            for t in good:
                seen_text.add(t)
                out.write(json.dumps({"text": t, "aixl": target, "group": rec["seed"]}, ensure_ascii=False) + "\n")
    print(f"groups kept {kept_groups}  dropped {dropped_groups}  members dropped by consensus {dropped_members}")
    print(f"written {out_path}")


if __name__ == "__main__":
    main()
