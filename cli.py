#!/usr/bin/env python3
"""AIXL 0.3 CLI.   python cli.py translate "Analiza las ventas de Q1 2026"
   compare A B | diff A B | drift A B | ambiguity TEXT | contradiction A B | aixl AIXL | lab A B | demo | serve [port] | bench
   negotiate SENDER_TEXT RECEIVER_TEXT [--rounds N] | negotiate-aixl SENDER_AIXL RECEIVER_AIXL [--rounds N]"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aixl  # noqa: E402

DEMOS = [
    ("DEMO 1 — equivalencia", "Analiza las ventas del primer trimestre de 2026.", "Examina las ventas de Q1 2026.", "EQUIVALENT"),
    ("DEMO 2 — diferencia temporal", "Analiza las ventas de Q1 2026.", "Analiza las ventas de Q2 2026.", "NOT EQUIVALENT / TIME DRIFT"),
    ("DEMO 3 — negación", "Elimina el reporte.", "No elimines el reporte.", "NOT EQUIVALENT / CRITICAL DIFFERENCE"),
    ("DEMO 4 — cantidad", "Analiza 100 registros.", "Analiza 1000 registros.", "NOT EQUIVALENT / QUANTITY DIFFERENCE"),
    ("DEMO 5 — restricción", "Confianza >= 0.90", "Confianza >= 0.70", "NOT EQUIVALENT / CONSTRAINT DIFFERENCE"),
]


def dump(x):
    print(json.dumps(x, ensure_ascii=False, indent=2))


def _negotiation_dict(out):
    return {"converged": out.converged, "rounds": out.rounds,
            "transcript": [t.encode() for t in out.transcript],
            "remaining_differences": [d.to_dict() for d in out.remaining_differences]}


def _print_negotiation(out):
    for t in out.transcript:
        print(" ", t.encode())
    print()
    print(("CONVERGED" if out.converged else "REJECTED") + f" in {out.rounds} round(s)")
    for d in out.remaining_differences:
        print(f"  unresolved: {d.field}: {d.source} -> {d.target}  [{d.severity}]")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="aixl", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, n in (("translate", 1), ("ambiguity", 1), ("aixl", 1), ("compare", 2), ("diff", 2), ("drift", 2), ("contradiction", 2), ("lab", 2)):
        p = sub.add_parser(name)
        p.add_argument("a"); n == 2 and p.add_argument("b"); p.add_argument("--json", action="store_true")
    sub.add_parser("demo"); sub.add_parser("bench")
    for name in ("negotiate", "negotiate-aixl"):
        p = sub.add_parser(name)
        p.add_argument("a"); p.add_argument("b"); p.add_argument("--rounds", type=int, default=3)
        p.add_argument("--json", action="store_true")
    sv = sub.add_parser("serve"); sv.add_argument("port", nargs="?", type=int, default=8765)
    a = ap.parse_args(argv)
    if a.cmd == "translate":
        t = aixl.translate(a.a)
        return dump(t) if a.json else (print("AIXL:", t["aixl"]), dump({"semantic": t["semantic"], "ambiguity": t["ambiguity"]["ambiguous"]}))
    if a.cmd == "aixl":
        g = aixl.from_aixl(a.a); dump({k: (list(v) if isinstance(v, tuple) else v) for k, v in g.canonical().items()}); return
    if a.cmd == "compare":
        r = aixl.compare(a.a, a.b)
        if a.json: return dump(r.to_dict())
        print(f"equivalent: {str(r.equivalent).lower()}   similarity: {r.similarity:.2f}   drift: {r.drift_level}")
        for d in r.differences: print(f"  {d.field}: {d.source} -> {d.target}  [{d.severity}]")
        return
    if a.cmd == "diff": return print(aixl.semantic_diff(a.a, a.b))
    if a.cmd == "drift":
        r = aixl.detect_drift(a.a, a.b); return dump(r.to_dict()) if a.json else (print(r.level, "CRITICAL_SEMANTIC_DRIFT" if r.critical else ""), [print(f"  {d.field}: {d.source} -> {d.target} [{d.severity}]") for d in r.differences])
    if a.cmd == "ambiguity": return dump(aixl.detect_ambiguity(a.a).to_dict())
    if a.cmd == "contradiction": return dump(aixl.detect_contradiction(a.a, a.b).to_dict())
    if a.cmd == "negotiate":
        out = aixl.negotiate(a.a, a.b, max_rounds=a.rounds)
        return dump(_negotiation_dict(out)) if a.json else _print_negotiation(out)
    if a.cmd == "negotiate-aixl":
        out = aixl.negotiate_aixl(a.a, a.b, max_rounds=a.rounds)
        return dump(_negotiation_dict(out)) if a.json else _print_negotiation(out)
    if a.cmd == "lab":
        from lab.render import lab_view; return print(lab_view(a.a, a.b))
    if a.cmd == "demo":
        for title, x, y, expect in DEMOS:
            r = aixl.compare(x, y)
            print(f"\n{title}\n  A: {x}\n  B: {y}\n  expected: {expect}\n  got:      {'EQUIVALENT' if r.equivalent else 'NOT EQUIVALENT'} / {r.drift_level} / fields={[d.field for d in r.differences]}")
        t = "Analiza los datos recientes."; amb = aixl.detect_ambiguity(t)
        print(f"\nDEMO 6 — ambigüedad\n  {t}\n  expected: AMBIGUOUS\n  got:      {'AMBIGUOUS' if amb.ambiguous else 'NOT AMBIGUOUS'} ({amb.reason}, fields={amb.fields})")
        return
    if a.cmd == "serve":
        from lab.server import H; from http.server import HTTPServer
        print(f"AIXL Semantic Lab on http://localhost:{a.port}", flush=True); HTTPServer(("127.0.0.1", a.port), H).serve_forever()
    if a.cmd == "bench":
        from benchmarks import equivalence; s, *_ = equivalence.run(); return dump(s)


if __name__ == "__main__":
    main()
