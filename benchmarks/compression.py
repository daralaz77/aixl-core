"""STRUCTURAL compression: text vs AIXL vs canonical JSON. Tokens use tiktoken cl100k_base (OpenAI tokenizer) when installed;
that is a PROXY for LLM tokens (not Claude's tokenizer) and is labelled as such. Without tiktoken only structural metrics are printed."""
import json, os
from aixl import to_aixl, to_semantic
from aixl.serialization import json_codec
from benchmarks.dataset import load

try:
    import tiktoken
    ENC = tiktoken.get_encoding("cl100k_base")
except Exception:                                        # noqa: BLE001
    ENC = None


def texts():
    out = []
    for c in load():
        out.append(c["input_a"])
        if c.get("input_b"): out.append(c["input_b"])
    return out


def run(ts=None):
    ts = ts or texts()
    tot = {"chars": [0, 0, 0], "bytes": [0, 0, 0], "words": [0, 0, 0], "tokens": [0, 0, 0]}
    for t in ts:
        g = to_semantic(t); a = to_aixl(t); j = json_codec.canonical_json(g)
        for i, x in enumerate((t, a, j)):
            tot["chars"][i] += len(x); tot["bytes"][i] += len(x.encode("utf-8")); tot["words"][i] += len(x.split())
            if ENC: tot["tokens"][i] += len(ENC.encode(x))
    red = lambda v, i: round(100 * (1 - v[i] / v[0]), 1)
    out = {"n_texts": len(ts), "note": "negative reduction = AIXL/JSON is LONGER than the natural text"}
    for k, v in tot.items():
        if k == "tokens" and not ENC:
            out["tokens"] = "not measured (no tokenizer installed)"; continue
        out[k] = {"text": v[0], "aixl": v[1], "canonical_json": v[2], "aixl_reduction_pct_vs_text": red(v, 1), "json_reduction_pct_vs_text": red(v, 2),
                  "aixl_reduction_pct_vs_json": round(100 * (1 - v[1] / v[2]), 1)}
    out["token_tokenizer"] = "tiktoken cl100k_base (OpenAI; proxy, not Claude's tokenizer)" if ENC else None
    return out


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, ensure_ascii=False))
