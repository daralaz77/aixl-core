"""FASE 8 — live negotiation protocol between two agents (2026-09-29, E-NEGOTIATE).

Every prior experiment (E-XV, E-DATE, E-INTEROP) treated a disagreement between two independently-
encoded AIXL messages as something to minimize by teaching both sides the SAME shared vocabulary
up front. That closes most gaps but not all (E-INTEROP: 53 % -> 79 % cross-vendor consistency over
3 rounds, then diminishing returns). This module is the other half: when two agents STILL disagree
after encoding, instead of silently picking one reading or crashing, the RECEIVER asks a targeted
CLARIFY question about the single worst-severity dimension, the SENDER (who holds the original
instruction and is therefore authoritative) ANSWERs with its own value for that one dimension, the
receiver adopts it and re-compares — repeating up to a bounded number of rounds, then ACCEPTing
(converged) or REJECTing (honestly reporting what could not be resolved, never guessing further).

Design choices, each deliberate:
- A negotiation turn is its OWN small wire format (`NEGOTIATE X=... MSG=... ...`), NOT new AIXL atoms.
  Mixing protocol/transport concerns (turn-taking, message ids) into the frozen semantic ATOMS dict
  would blur the layers and risk the core codec; a negotiation turn instead CARRIES a normal AIXL
  line as its payload where relevant (REQUEST/ANSWER turns), decoded by the untouched aixl_codec.
- Negotiation resolves ONE dimension per round, the worst-severity one first (CRITICAL before MAJOR
  before MODERATE before MINOR) — this is the dimension most likely to change the equivalence verdict,
  so it converges in the fewest rounds and never wastes a round on something that wouldn't matter.
- The sender is trusted for the disputed dimension's value (it holds the original instruction); this
  models "ask the party who actually knows", not a coin flip or a vote between two guesses.
- Bounded rounds (default 3, matching how many rounds E-INTEROP itself needed to converge from 53 %
  to 79 % before diminishing returns set in): a REJECT after the cap is an honest, reportable outcome,
  never an infinite loop or a silent guess.
"""
from dataclasses import dataclass, field
import re

from aixl.core.comparator import compare_canonical, Difference
from aixl.core.ontology import DIMENSIONS, load_config, rank

TURN_TYPES = {"REQUEST", "CLARIFY", "ANSWER", "ACCEPT", "REJECT"}
_DIM_LABEL = {"negation": "NEGATION", "actions": "ACTION", "quantities": "QUANTITY"}
_LABEL_DIM = {v: k for k, v in _DIM_LABEL.items()}
DERIVED = {"intent", "goal"}   # same as comparator.DERIVED: never negotiated directly, they follow actions/negation


class NegotiationError(Exception):
    def __init__(self, code, msg=""):
        super().__init__(f"ERROR:{code} {msg}".strip())
        self.code = code


def _dim_of_label(label: str) -> str:
    return _LABEL_DIM.get(label, label.lower())


def _fmt(v) -> str:
    if isinstance(v, tuple):
        return ",".join(v) if v else "NOT_SPECIFIED"
    return v if v else "NOT_SPECIFIED"


def _is_empty(v) -> bool:
    return v is None or v == "" or (isinstance(v, tuple) and len(v) == 0)


def _quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _unquote(s: str) -> str:
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return s


@dataclass
class NegotiationTurn:
    turn_type: str                 # REQUEST | CLARIFY | ANSWER | ACCEPT | REJECT
    msg_id: str
    ref_id: str = ""
    dim: str = ""                  # canonical() key under dispute, e.g. "actions" (empty when not applicable)
    candidates: tuple = ()         # (receiver_value, sender_value) as display strings, for CLARIFY
    question: str = ""             # free-text question, for CLARIFY
    value: str = ""                # the resolved value, for ANSWER
    payload: str = ""              # a normal AIXL line, for REQUEST turns
    reason: str = ""               # for REJECT

    def encode(self) -> str:
        if self.turn_type not in TURN_TYPES:
            raise NegotiationError("INVALID_TURN", f"unknown turn type {self.turn_type!r}")
        toks = [f"X={self.turn_type}", f"MSG={self.msg_id}"]
        if self.ref_id:
            toks.append(f"REF={self.ref_id}")
        if self.dim:
            toks.append(f"DIM={self.dim}")
        if self.candidates:
            # ';' separates the candidates themselves; ',' stays free inside one candidate for a tuple-valued
            # dimension (e.g. D:REPORT,DATA as ONE candidate reading) — found necessary after an independent
            # model, given only the spec, naturally wrote a comma-joined multi-value candidate and collided
            # with a plain comma-separated CANDIDATES list (E-NEGOTIATE live demo, 2026-09-29).
            toks.append("CANDIDATES=" + ";".join(self.candidates))
        if self.question:
            toks.append("Q=" + _quote(self.question))
        if self.value:
            toks.append("VALUE=" + (_quote(self.value) if "," in self.value or " " in self.value else self.value))
        if self.reason:
            toks.append("REASON=" + _quote(self.reason))
        if self.payload:
            toks.append("PAYLOAD=" + _quote(self.payload))
        return "NEGOTIATE " + " ".join(toks)


_TOKEN_RX = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|[^\s]+)')


def decode(line: str) -> NegotiationTurn:
    """Raises NegotiationError on malformed input — same never-crash-on-bad-input philosophy as aixl_codec."""
    line = line.strip()
    if not line.startswith("NEGOTIATE"):
        raise NegotiationError("INVALID_TURN", "line does not start with NEGOTIATE")
    rest = line[len("NEGOTIATE"):].strip()
    fields = {}
    for m in _TOKEN_RX.finditer(rest):
        fields[m.group(1)] = _unquote(m.group(2))
    if "X" not in fields or "MSG" not in fields:
        raise NegotiationError("INVALID_TURN", "missing X= or MSG=")
    turn_type = fields["X"]
    if turn_type not in TURN_TYPES:
        raise NegotiationError("INVALID_TURN", f"unknown turn type {turn_type!r}")
    candidates = tuple(fields["CANDIDATES"].split(";")) if "CANDIDATES" in fields else ()
    return NegotiationTurn(
        turn_type=turn_type, msg_id=fields["MSG"], ref_id=fields.get("REF", ""),
        dim=fields.get("DIM", ""), candidates=candidates, question=fields.get("Q", ""),
        value=fields.get("VALUE", ""), payload=fields.get("PAYLOAD", ""), reason=fields.get("REASON", ""),
    )


def worst_dimension(result) -> Difference | None:
    """The single Difference to negotiate first: highest severity, then first in DIMENSIONS order (stable)."""
    if not result.differences:
        return None
    order = {d: i for i, d in enumerate(DIMENSIONS)}
    return max(result.differences, key=lambda d: (rank(d.severity), -order.get(_dim_of_label(d.field), 999)))


@dataclass
class NegotiationOutcome:
    converged: bool
    rounds: int
    transcript: list = field(default_factory=list)          # list[NegotiationTurn], in order
    final_receiver_canonical: dict = field(default_factory=dict)
    remaining_differences: list = field(default_factory=list)   # list[Difference], empty if converged


def negotiate(sender_canonical: dict, receiver_canonical: dict, config: dict | None = None,
              max_rounds: int = 3, msg_prefix: str = "M") -> NegotiationOutcome:
    """Run a bounded clarification exchange. The sender's own canonical() dict is treated as authoritative
    for whichever ONE dimension the receiver disputes each round (see module docstring for why). Returns
    an honest ACCEPT (converged) or REJECT (remaining_differences non-empty) — never a silent guess past
    max_rounds, and never more rounds than the cap even if disagreements remain."""
    cfg = config or load_config()
    belief = dict(receiver_canonical)
    transcript: list[NegotiationTurn] = []
    n = 0
    mid = 0

    def next_id():
        nonlocal mid
        mid += 1
        return f"{msg_prefix}{mid}"

    req_id = next_id()
    transcript.append(NegotiationTurn("REQUEST", req_id))
    last_id = req_id
    while n < max_rounds:
        result = compare_canonical(sender_canonical, belief, cfg)
        if result.equivalent:
            acc_id = next_id()
            transcript.append(NegotiationTurn("ACCEPT", acc_id, ref_id=last_id))
            return NegotiationOutcome(True, n, transcript, belief, [])
        d = worst_dimension(result)
        dim = _dim_of_label(d.field)
        n += 1
        clarify_id = next_id()
        # d comes from compare_canonical(sender_canonical, belief): d.source is the SENDER's value (A side),
        # d.target is the RECEIVER's/belief's value (B side) — found backwards here (question text and
        # candidate order swapped which was which) by reading real CLI output, not by the unit tests, which
        # only ever checked the final resolved ANSWER value, never the CLARIFY's own displayed wording.
        transcript.append(NegotiationTurn(
            "CLARIFY", clarify_id, ref_id=last_id, dim=dim, candidates=(d.target, d.source),
            question=f"{d.field}: receiver read '{d.target}', sender's own message implies '{d.source}' — which is correct?"))
        sender_value = sender_canonical.get(dim, "")
        # E-MCP third-party test (2026-09-30, Claude Desktop): "the sender is authoritative" only holds
        # when the sender's own re-derived value actually says something. Scoped to `actions` ONLY: an
        # empty `actions` is always a translator failure (every real instruction has a main verb; found
        # via "Quita el ticket #77." — an out-of-vocabulary verb — silently overwriting the receiver's
        # correct DELETE reading with nothing while still reporting ACCEPT). Every OTHER dimension can be
        # legitimately, correctly empty (no prohibition stated, no time given, ...) — rejecting there too
        # broke a real case (sender genuinely states no negation vs. receiver's FORBID:DELETE, where the
        # sender's empty value IS the correct answer), caught by the existing test suite.
        if dim == "actions" and _is_empty(sender_value):
            rej_id = next_id()
            transcript.append(NegotiationTurn(
                "REJECT", rej_id, ref_id=clarify_id,
                reason=f"sender's own message does not resolve {d.field} either — cannot confirm which reading is correct"))
            return NegotiationOutcome(False, n, transcript, belief, result.differences)
        answer_id = next_id()
        transcript.append(NegotiationTurn("ANSWER", answer_id, ref_id=clarify_id, dim=dim, value=_fmt(sender_value)))
        belief[dim] = sender_value           # adopt the sender's value for exactly this one dimension
        last_id = answer_id
    # E-NEGOTIATE self-check (found by running this on real E-INTEROP disagreements, not by unit tests alone —
    # every unit test happened to leave one spare round, masking this): the round that PATCHES the last
    # disputed dimension must still be re-checked for equivalence before falling through to REJECT, or a
    # negotiation that resolves everything right at the round cap is wrongly reported as failed.
    result = compare_canonical(sender_canonical, belief, cfg)
    if result.equivalent:
        acc_id = next_id()
        transcript.append(NegotiationTurn("ACCEPT", acc_id, ref_id=last_id))
        return NegotiationOutcome(True, n, transcript, belief, [])
    rej_id = next_id()
    transcript.append(NegotiationTurn(
        "REJECT", rej_id, ref_id=last_id,
        reason=f"no consensus after {max_rounds} rounds; {len(result.differences)} dimension(s) still differ"))
    return NegotiationOutcome(False, n, transcript, belief, result.differences)
