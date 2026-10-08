"""Guard ratchet: zero false-pass on every frozen set, and the regression for each bug blind testing found.
Sets: data/guard/sets/*.json (dev = tuning data, blind1-4 = fresh sets written by the same author, spent). Labels are author-assigned."""
import glob
import json
import os

import pytest

from aixl.guard import guard

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETS = sorted(glob.glob(os.path.join(ROOT, "data", "guard", "sets", "*.json")))


def rows():
    for path in SETS:
        d = json.load(open(path, encoding="utf-8"))
        for profile, items in d.items():
            for i, it in enumerate(items):
                yield pytest.param(profile, it, id=f"{os.path.basename(path)[:-5]}-{profile}-{i}-{it['kind']}")


@pytest.mark.parametrize("profile,it", list(rows()))
def test_no_false_pass_and_recorded_decision(profile, it):
    r = guard(it["source"], it["candidate"], profile, use_aixl=False)
    assert r.decision == it["decision"]                      # the frozen decision (deterministic rules)
    if it["label"] == "D":
        assert r.decision == "REVIEW", f"distortion passed: {it['source']} -> {it['candidate']}"


def test_sin_is_a_negation_even_before_a_letter():            # bug found by blind3: the (?![a-z]) tail killed 'sin firmar'
    r = guard("Solicito copia del contrato firmado.", "Pido copia del contrato sin firmar.", "reclamaya", use_aixl=False)
    assert r.decision == "REVIEW"


def test_hidden_characters_force_review():
    r = guard("email must be an email", "El campo \"correo\" debe ser un correo v​alido.", "cinematch", use_aixl=False)
    assert r.decision == "REVIEW" and any(x.startswith("HIDDEN_CHARS") for x in r.reasons)


def test_identical_text_passes():
    assert guard("Forbidden", "Forbidden", "cinematch", use_aixl=False).passed


def test_guard_actions_cross_pairs_and_real_episode_case():
    """Same data/expectations as robot-school/services/api/scripts/test_instruction_guard.js (JS port parity)."""
    from aixl.guard import guard_actions
    cross = json.load(open(os.path.join(ROOT, "data", "guard", "robot_actions_cross.json"), encoding="utf-8"))
    ins, act = cross["instructions"], cross["actions"]
    assert all(guard_actions(ins[k], act[k]).passed for k in ins)
    specific = [1, 2, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    leaks = sorted(f"{i}/{j}" for i in specific for j in act if str(i) != j and guard_actions(ins[str(i)], act[j]).passed)
    assert leaks == ["12/6", "4/9", "6/12", "9/6"]
    # the documented real mismatch (DEC-005): "señala" recorded as "display"
    r = guard_actions("Señala con la mano el objeto que se te indique, dejando manos y objeto visibles.",
                      [{"verb": "display", "description": "Camera frames pineapple to show entire object"}])
    assert r.decision == "REVIEW" and r.reasons == ["NOT_REALIZED POINT"]
