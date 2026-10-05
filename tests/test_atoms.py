"""AIXL 0.4 atom layer: registry integrity, schema, wire, firewall, alignment, diff, the master-prompt critical tests (§33-39),
and the invariant that a COMPLETE extraction on the dev gold is always exact (the extractor must declare what it cannot place)."""
import json, os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from aixl.atoms import registry as R, fidelity
from aixl.atoms.schema import Atom, AtomGraph
from aixl.atoms.wire import encode, decode, DecodeError
from aixl.atoms.firewall import Profile, receive, check, common_profile, align, diff
from aixl.atoms.extract import extract

D = os.path.join(ROOT, "data", "atoms")


def _gold():
    texts = {c["id"]: c for c in json.load(open(os.path.join(D, "cases_dev.json"), encoding="utf-8"))}
    out = {}
    for l in open(os.path.join(D, "gold_dev.jsonl"), encoding="utf-8"):
        r = json.loads(l); out[r["id"]] = (texts[r["id"]]["text"], AtomGraph.from_dict(dict(atoms=r["atoms"], relations=r["relations"], text=texts[r["id"]]["text"])))
    return out


GOLD = _gold()
TXT = {i: t for i, (t, _) in GOLD.items()}


def fp(text):
    return extract(text).fingerprint(include_unrepresented=False)


# ---------------------------------------------------------------- registry
def test_registry_ids_unique_and_well_formed():
    ids = [c["id"] for c in R.CONCEPTS]
    assert len(ids) == len(set(ids))
    for c in R.CONCEPTS:
        assert c["type"] in R.ATOM_TYPES and c["definition"]
        for n in c["near"]: assert R.concept(n) is not None, (c["id"], n)


def test_registry_lexemes_cover_three_languages_for_actions():
    for c in R.CONCEPTS:
        if c["type"] == "ACTION" and c["id"] != "ACT.ENSURE" and not c.get("learned"):
            assert all(c["lex"][l] for l in ("es", "en", "pt")), c["id"]


# ---------------------------------------------------------------- schema
def test_gold_graphs_validate():
    for i, (_, g) in GOLD.items(): assert g.validate() == [], i


def test_fingerprint_independent_of_ids_and_order():
    a = AtomGraph([Atom("1", "ACTION", "ACT.SUMMARIZE"), Atom("2", "ENTITY", "ENT.REPORT")], [("1", "TARGETS", "2")])
    b = AtomGraph([Atom("z", "ENTITY", "ENT.REPORT"), Atom("y", "ACTION", "ACT.SUMMARIZE")], [("y", "TARGETS", "z")])
    assert a.fingerprint() == b.fingerprint()


def test_fingerprint_sensitive_to_relation_direction_and_role():
    base = [Atom("1", "ACTION", "ACT.SEND"), Atom("2", "ENTITY", "ENT.REPORT"), Atom("3", "ENTITY", "ENT.CUSTOMER")]
    a = AtomGraph(list(base), [("1", "TARGETS", "2"), ("1", "RECIPIENT", "3")])
    b = AtomGraph(list(base), [("1", "TARGETS", "3"), ("1", "RECIPIENT", "2")])
    assert a.fingerprint() != b.fingerprint()


def test_validate_rejects_bad_time_ref_and_unregistered_concept():
    g = AtomGraph([Atom("1", "TIME", value=dict(rel="before", ref="whenever"))])
    assert any("bad TIME ref" in e for e in g.validate())
    g = AtomGraph([Atom("1", "ACTION", "ACT.NOPE")])
    assert any("unregistered" in e for e in g.validate())


# ---------------------------------------------------------------- wire + firewall
def test_wire_roundtrip_all_gold():
    for i, (_, g) in GOLD.items():
        h = decode(encode(g))
        assert h.fingerprint() == g.fingerprint() == h._declared_fp, i


def test_wire_value_with_spaces_roundtrips():
    g = AtomGraph([Atom("1", "NAME", value="Maria Lopez")])
    assert decode(encode(g)).atoms[0].value == "Maria Lopez"


def test_tamper_in_transit_is_integrity_failure():
    m = encode(extract("Resume el informe en máximo 150 palabras."))
    v = receive(m.replace('"n":150', '"n":151'), Profile("B"))
    assert not v.accepted and "SEMANTIC_INTEGRITY_FAILURE" in v.reasons


def test_unknown_type_or_relation_is_malformed_not_guessed():
    m = encode(extract("Resume el informe."))
    assert "MALFORMED_MESSAGE" in receive(m.replace(" ACTION ", " WIZARD "), Profile("B")).reasons
    assert "MALFORMED_MESSAGE" in receive(m.replace("TARGETS", "BEFRIENDS"), Profile("B")).reasons


def test_unsupported_concept_is_reported_never_substituted():
    m = encode(extract("Resume el informe."))
    v = receive(m, Profile("tiny", concepts=frozenset({"ACT.SEND"})))
    assert not v.accepted and "UNSUPPORTED_CONCEPT" in v.reasons and ("concept", "ACT.SUMMARIZE") in v.unsupported


def test_extension_policy():
    g = extract("Rotate the API keys.")
    assert any(a.concept.startswith("x:") for a in g.atoms if a.concept)
    assert not check(g, Profile("strict")).accepted
    assert check(g, Profile("open", accept_extensions=True)).accepted


def test_common_profile_is_intersection():
    a = Profile("A", concepts=frozenset({"ACT.SEND", "ACT.DELETE"})); b = Profile("B", concepts=frozenset({"ACT.SEND", "ACT.SAVE"}))
    assert common_profile(a, b).concepts == frozenset({"ACT.SEND"})
    assert Profile.from_hello(a.hello()).concepts == a.concepts


def test_alignment_never_upgrades_close_to_exact():
    assert align("ACT.SEND", "ACT.SEND") == "EXACT_MATCH"
    assert align("ACT.SEND", "ACT.PUBLISH") == "CLOSE_MATCH"
    assert align("ACT.SEND", "x:foo") == "UNKNOWN"
    assert align("ACT.SEND", "ENT.REPORT") == "INCOMPATIBLE"


def test_unrepresented_is_part_of_the_message_and_the_fingerprint():
    g = AtomGraph([Atom("1", "ACTION", "ACT.SEND")], unrepresented=["per post"])
    assert decode(encode(g)).unrepresented == ["per post"]
    assert g.fingerprint() != AtomGraph([Atom("1", "ACTION", "ACT.SEND")]).fingerprint()
    assert not g.complete


# ---------------------------------------------------------------- master prompt critical tests
def test_s33_three_languages_same_graph():
    es, en, pt = fp("Resume el informe en máximo 150 palabras."), fp("Summarize the report in no more than 150 words."), fp("Resuma o relatório em no máximo 150 palavras.")
    assert es == en == pt


def test_s34_quantity_change_is_exactly_one_difference():
    d = diff(extract("Resume el informe en máximo 150 palabras."), extract("Resume el informe en máximo 300 palabras."))
    assert len(d) == 1 and d[0]["field"] == "value" and d[0]["old"]["n"] == 150 and d[0]["new"]["n"] == 300


def test_s35_negation_changes_only_modality():
    d = diff(extract("Usa fuentes oficiales."), extract("No uses fuentes oficiales."))
    assert len(d) == 1 and d[0]["field"] == "modality" and (d[0]["old"], d[0]["new"]) == ("DO", "DONT")


def test_s36_scope_exception_differs_from_plain():
    a = fp("Resume todos los documentos excepto los confidenciales."); b = fp("Resume todos los documentos confidenciales.")
    assert a != b
    assert fp("Summarize all documents except the confidential ones.") == a


def test_s37_condition_vs_check():
    assert fp("Si el archivo está vacío, solicita otro.") != fp("Solicita otro archivo y comprueba si está vacío.")


def test_s38_three_temporal_forms_are_different():
    s = {fp("Envía el informe antes del viernes."), fp("Envía el informe el viernes."), fp("Envía el informe después del viernes.")}
    assert len(s) == 3


def test_s39_four_quantity_modes_are_different():
    s = {fp("Write exactly 10 sentences."), fp("Write at most 10 sentences."), fp("Escribe al menos 10 frases."), fp("Escreva aproximadamente 10 frases.")}
    assert len(s) == 4


# ---------------------------------------------------------------- extractor
def test_complete_implies_exact_on_dev_gold():
    """The extractor may be wrong only when it says so (graph.unrepresented non-empty)."""
    silent = []
    for i, (t, gold) in GOLD.items():
        got = extract(t)
        if got.complete and got.fingerprint(include_unrepresented=False) != gold.fingerprint(include_unrepresented=False): silent.append(i)
    assert silent == [], silent


def test_extractor_dev_regression_floor():
    sc = [fidelity.score(g, extract(t)) for t, g in GOLD.values()]
    agg = fidelity.aggregate(sc)
    assert agg["overall"]["f1"] >= 0.97 and agg["exact_graph"] >= 0.94     # dev set: regression guard, NOT a performance claim


def test_unknown_vocabulary_is_flagged_not_dropped():
    g = extract("Reconcilia las cuentas del trimestre.")
    assert not g.complete and any(u.startswith("term:") for u in g.unrepresented)
    assert not extract("blah blah").atoms or not extract("blah blah").complete


def test_registry_version_is_single_source_of_truth():
    g = extract("Resume el informe.")
    assert g.registry_version == R.REGISTRY_VERSION and decode(encode(g)).registry_version == R.REGISTRY_VERSION
    assert Profile("p").registry_version == R.REGISTRY_VERSION


def test_time_grammar_accepts_what_the_guide_defines():
    ok = [dict(rel="before", ref="10-17"), dict(rel="before", ref="event:expiry", offset="1mo"), dict(rel="at", ref="17:00"), dict(rel="after", ref="d10"),
          dict(rel="within", ref="24h"), dict(rel="during", ref="this_weekend"), dict(rel="at", ref="evening"), dict(rel="since", ref="2026-01-01")]
    for v in ok: assert AtomGraph([Atom("1", "TIME", value=v)]).validate() == [], v
    for v in (dict(rel="before", ref="whenever"), dict(rel="before", ref="event:x", offset="soon"), dict(rel="around", ref="fri")):
        assert AtomGraph([Atom("1", "TIME", value=v)]).validate(), v


def test_unknown_atom_keys_are_reported_not_dropped():
    g = AtomGraph.from_dict(dict(atoms=[dict(id="a", type="TIME", value=dict(rel="before", ref="fri"), offset="2d")], relations=[]))
    assert any("unknown atom keys" in e for e in g.validate())


def test_generated_registry_doc_is_fresh():
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import gen_atoms_docs
    assert open(os.path.join(ROOT, "docs", "ATOMS_REGISTRY.md"), encoding="utf-8").read() == gen_atoms_docs.render(), "run: python scripts/gen_atoms_docs.py"


# ---------------------------------------------------------------- LLM wrapper (mock callables: the core calls no model)
from aixl.atoms import llm_extract as LX

_GOOD = {"id": "t", "atoms": [dict(id="a1", type="ACTION", concept="ACT.SUMMARIZE", modality="DO"), dict(id="a2", type="ENTITY", concept="ENT.REPORT")],
         "relations": [["a1", "TARGETS", "a2"]]}


def _call(d):
    return lambda prompt: json.dumps(d)


def test_prompt_is_self_contained_and_versioned():
    p = LX.build_prompt([dict(id="x1", text="Resume el informe.")])
    assert "ACT.SUMMARIZE" in p and "RELATIONS (source -> target)" in p and "Guide v0.4" in p and "Resume el informe." in p and len(LX.prompt_id()) == 12


def test_parse_tolerates_fences_and_reports_invalid_and_missing():
    bad = dict(_GOOD, id="b", relations=[["a2", "TARGETS", "a1"]])         # entity cannot TARGET an action: endpoint violation
    raw = "```json\n" + json.dumps(dict(_GOOD, id="a")) + "\n" + json.dumps(bad) + "\n```"
    p = LX.parse_response(raw, ["a", "b", "c"])
    assert set(p.graphs) == {"a"} and "b" in p.errors and p.errors["c"] == ["MISSING"]


def test_lemma_canonicalization():
    d = dict(_GOOD, atoms=_GOOD["atoms"] + [dict(id="a3", type="ENTITY", concept="x:Press Release")])
    assert any(a.concept == "x:press_release" for a in LX.parse_response(json.dumps(d), ["t"]).graphs["t"].atoms)


def test_wrapper_accepts_only_when_calls_agree_and_abstains_otherwise():
    ok = LX.extract_llm("Resume el informe.", [_call(_GOOD), _call(_GOOD)])
    assert ok.status == "ACCEPT" and ok.agreement == "exact"
    other = dict(_GOOD, atoms=[dict(id="a1", type="ACTION", concept="ACT.SUMMARIZE", modality="DONT"), _GOOD["atoms"][1]])
    r = LX.extract_llm("Resume el informe.", [_call(_GOOD), _call(other)])
    assert r.status == "ABSTAIN" and r.reasons == ["CALLS_DISAGREE"] and len(r.candidates) == 2


def test_wrapper_never_accepts_with_one_call_or_an_invalid_call():
    assert LX.extract_llm("x", [_call(_GOOD)]).status == "ABSTAIN"
    assert LX.extract_llm("x", [_call(_GOOD), lambda p: "not json"]).status == "ABSTAIN"


def test_core_policy_tolerates_auxiliary_link_differences_only():
    with_prop = dict(_GOOD, atoms=_GOOD["atoms"] + [dict(id="a3", type="PROPERTY", concept="PRP.OFFICIAL")], relations=_GOOD["relations"] + [["a2", "HAS_PROPERTY", "a3"]])
    assert LX.extract_llm("x", [_call(_GOOD), _call(with_prop)], policy="exact").status == "ABSTAIN"
    r = LX.extract_llm("x", [_call(_GOOD), _call(with_prop)], policy="core")
    assert r.status == "ACCEPT" and r.agreement == "core"
    neg = dict(_GOOD, atoms=[dict(id="a1", type="ACTION", concept="ACT.SUMMARIZE", modality="DONT"), _GOOD["atoms"][1]])
    assert LX.extract_llm("x", [_call(_GOOD), _call(neg)], policy="core").status == "ABSTAIN"


# ---------------------------------------------------------------- normal form + learned registry (ADR-021)
from aixl.atoms.normalize import Normalizer, lemma, singular


def test_learned_concepts_are_well_formed_and_do_not_shadow_curated_ones():
    assert R.LEARNED, "learned_concepts.json should not be empty"
    curated = {c["id"] for c in R.CONCEPTS if not c.get("learned")}
    for c in R.LEARNED:
        assert c["id"] not in curated and c["evidence"]["texts"] >= 3 and c["lex"]["en"] and c["definition"].startswith("learned from data")


def test_rule_extractor_ignores_learned_concepts():
    g = extract("Reply to the supplier.")          # 'reply'/'supplier' are learned concepts: the rule extractor must still treat them as unknown
    assert not g.complete


def test_normalizer_maps_learned_lemmas_and_leaves_meaning_alone():
    n = Normalizer()
    g = AtomGraph([Atom("1", "ACTION", "x:reply"), Atom("2", "ENTITY", "x:suppliers")], [("1", "TARGETS", "2")])
    h = n(g)
    assert {a.concept for a in h.atoms} == {"ACT.REPLY", "ENT.SUPPLIER"} and h.validate() == []
    neg = AtomGraph([Atom("1", "ACTION", "x:reply", modality="DONT"), Atom("2", "ENTITY", "x:supplier")], [("1", "TARGETS", "2")])
    assert n(neg).fingerprint() != h.fingerprint()                      # negation survives normalization


def test_lemma_and_singular():
    assert lemma("x:Press_Releases") == "x:press_release" and singular("entries") == "entry" and singular("status") == "status" and singular("class") == "class"


def test_compound_collapse_merges_split_and_compound_forms():
    compound = AtomGraph([Atom("1", "ACTION", "ACT.REVIEW"), Atom("2", "ENTITY", "x:corporate_card")], [("1", "TARGETS", "2")])
    split = AtomGraph([Atom("1", "ACTION", "ACT.REVIEW"), Atom("2", "ENTITY", "x:card"), Atom("3", "PROPERTY", "x:corporate")], [("1", "TARGETS", "2"), ("2", "HAS_PROPERTY", "3")])
    n = Normalizer()
    assert n(split).fingerprint() == n(compound).fingerprint()
    # a modifier that has relations of its own is NOT absorbed (it is not a leaf)
    busy = AtomGraph([Atom("1", "ACTION", "ACT.REVIEW"), Atom("2", "ENTITY", "x:card"), Atom("3", "PROPERTY", "x:corporate"), Atom("4", "QUANTITY", value=dict(mode="exact", n=2, unit="item"))],
                     [("1", "TARGETS", "2"), ("2", "HAS_PROPERTY", "3"), ("2", "CONSTRAINED_BY", "4")])
    assert any(a.concept == "x:corporate_card" for a in n(busy).atoms)   # leaf property absorbed, quantity link kept
    assert any(a.type == "QUANTITY" for a in n(busy).atoms)


def test_alias_table_only_merges_same_atom_type_and_has_evidence():
    from aixl.atoms.normalize import load_tables
    t = load_tables()
    for k, v in t["aliases"].items():
        typ = k.split(":", 1)[0]
        c = R.concept(v)
        assert c is None or c["type"] == typ, (k, v)               # registry canonical must be of the same atom type
        assert t["alias_evidence"][k]
