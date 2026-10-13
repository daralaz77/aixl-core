"""Behavioural equivalence of the ANALYSIS path between two code trees (a refactor/perf change must not change a single output).
   git worktree add /tmp/old HEAD
   (cd /tmp && PYTHONPATH=/tmp/old  python <repo>/benchmarks/code_equivalence_probe.py /tmp/old.json)
   (cd /tmp && PYTHONPATH=<repo>    python <repo>/benchmarks/code_equivalence_probe.py /tmp/new.json /tmp/old.json)   # compares and exits 1 on any difference
aixl, benchmarks and lab all come from PYTHONPATH (i.e. from the tree under test); the probe prints which tree it imported, and compare() refuses to
compare a tree with itself (a probe that used the new code twice once 'proved' equivalence for nothing)."""
import hashlib
import json
import os
import random
import sys


def _texts():
    import benchmarks.characterization as C
    from benchmarks._corpus import real_user_messages
    from lab.arena import arena as A
    out = list(C.corpus())
    out += [m for m in sorted(real_user_messages()) if len(m) <= 4000][:2500]
    rng = random.Random(11)
    for _name, _kind, fn in A.NL_ATTACKERS:
        for b in A.SEEDS:
            m = fn(b, random.Random(rng.randrange(1 << 30)))
            if m and m != b:
                out.append(m)
    out += ["Analiza las ventas antes de Q1 2026 y despues de marzo de 2025. " * k for k in (1, 2, 5, 30)]
    out += ["Q1 2026 " * k for k in (1, 3, 50)] + ["1,2,3," * k for k in (1, 5, 200)] + ["5 clientes, 12 registros y 3.5 ventas. " * k for k in (1, 4)]
    out += ["Analiza las ventas de Q1 2026. " * k for k in (1, 7, 60, 250)]
    return out


def probe():
    os.environ["AIXL_MAX_INPUT_CHARS"] = "100000000"
    import aixl.translators.natural_to_semantic as N
    import benchmarks.characterization as C
    from aixl.core.fingerprint import fingerprint_graph
    from aixl.serialization.aixl_codec import encode
    texts, h = _texts(), {}
    with C.frozen_today():
        for i, t in enumerate(texts):
            try:
                g = N.to_graph(t)
                blob = fingerprint_graph(g) + "|" + encode(g) + "|" + json.dumps(g.canonical(), sort_keys=True, default=str)
                h[i] = hashlib.sha256(blob.encode()).hexdigest()[:16]
            except Exception as e:
                h[i] = "EXC " + type(e).__name__
    return {"n": len(texts), "code": N.__file__, "h": h}


def compare(new, old):
    if new["code"] == old["code"]:
        raise SystemExit("both runs imported the same tree: " + new["code"])
    nh, oh = {str(k): v for k, v in new["h"].items()}, {str(k): v for k, v in old["h"].items()}     # JSON round-trips int keys to str
    diff = [k for k in nh if nh[k] != oh.get(k)]
    return len(nh) - len(diff), len(nh), diff


if __name__ == "__main__":
    res = probe()
    json.dump(res, open(sys.argv[1], "w"))
    print("imported:", res["code"], "| texts:", res["n"])
    if len(sys.argv) > 2:
        same, total, diff = compare(res, json.load(open(sys.argv[2])))
        print(f"identical: {same}/{total}", "" if not diff else f"DIFFERENT: {diff[:8]}")
        sys.exit(1 if diff else 0)
