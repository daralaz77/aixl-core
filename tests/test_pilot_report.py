"""Pilot report: the arithmetic that decides stop / pivot / go must be right, and the report must never copy the partner's text."""
import csv
import json

from benchmarks import pilot_report as P


def test_wilson_interval_contains_the_proportion_and_shrinks_with_n():
    lo, hi = P.wilson(10, 100)
    assert lo < 0.10 < hi and hi - lo < P.wilson(1, 10)[1] - P.wilson(1, 10)[0]
    assert P.wilson(0, 0) == (0.0, 1.0)


def test_estimate_recovers_a_known_rate_and_its_interval_covers_it():
    # 1000 pairs, 200 flagged (60 % real changes), 800 not flagged (2 % real) -> true rate = 0.2*0.6 + 0.8*0.02 = 13.6 %
    point, lo, hi = P.estimate(200, 800, 60, 100, 2, 100)
    assert abs(point - 0.136) < 1e-9 and lo < 0.136 < hi


def test_zone_is_certain_only_when_the_interval_sits_inside_one_zone():
    assert P.zone(0.02, 0.01, 0.03) == ("PARAR", True)
    assert P.zone(0.02, 0.01, 0.06) == ("PARAR", False)
    assert P.zone(0.10, 0.05, 0.12) == ("PIVOTAR", True)
    assert P.zone(0.13, 0.10, 0.20) == ("PIVOTAR", False)
    assert P.zone(0.20, 0.16, 0.25) == ("SEGUIR", True)


def test_end_to_end_report_has_no_partner_text(tmp_path):
    pairs = [{"id": f"P{i}", "source": "Pay 100 dollars to Acme before Friday.", "relay": "Pay 100 dollars to Acme before Friday." if i % 5 else "Pay 1000 dollars to Acme before Monday.",
              "flow": "f1"} for i in range(60)]
    pf = tmp_path / "pairs.jsonl"
    pf.write_text("\n".join(json.dumps(p) for p in pairs), encoding="utf-8")
    out = tmp_path / "out"
    P.analyze(str(pf), str(out), sample=10)
    sheet = list(csv.reader(open(out / "labeling_sheet.csv", encoding="utf-8")))[1:]
    assert len(sheet) == 20                                            # 10 flagged + 10 unflagged, shuffled
    truth = {p["id"]: p["relay"] != p["source"] for p in pairs}
    with open(tmp_path / "l1.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([[r[0], "CAMBIO" if truth[r[0]] else "IGUAL"] for r in sheet])
    text = P.report(str(out), str(tmp_path / "l1.csv"), "Socio X", labels2_path=str(tmp_path / "l1.csv"))
    assert "Acme" not in text and "dollars" not in text                # counts only, never the partner's text
    assert "20.0 %" in text and "Acuerdo entre las dos personas: 20 de 20" in text
    assert (out / "informe.md").exists()
