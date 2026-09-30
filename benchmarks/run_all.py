"""Run every benchmark and write BENCHMARK/results_dev_latest.json. Usage: python -m benchmarks.run_all"""
import json, os
from benchmarks import equivalence, compression
from benchmarks import blind_eval

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    dev, *_ = equivalence.run()
    b1, *_ = blind_eval.run(1)
    out = {"dev200_DEMO": dev, "blind1_CONTAMINATED_after_fixes": b1["equivalence"], "compression": compression.run()}
    p = os.path.join(ROOT, "BENCHMARK", "results_dev_latest.json")
    if os.path.exists(p): os.chmod(p, 0o644)
    json.dump(out, open(p, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
