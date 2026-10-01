"""`aixl_negotiate` as a genuine multi-turn A2A Task (E-A2A-NEGOTIATE, 2026-09-30).

Why this exists: AIXL's negotiation protocol (CLARIFY -> ANSWER) is inherently a stateful, possibly
multi-round exchange. Over MCP — which has no native concept of a paused, resumable task — getting any
multi-turn exchange at all required building a whole separate mechanism: a second MCP server process
(aixl/agents/sender_agent.py) plus aixl/autonomous_negotiation.py driving it by hand. A2A's Task model
(TaskState.TASK_STATE_INPUT_REQUIRED, a TaskStore that persists state across calls) is built for exactly
this kind of pause-and-resume interaction natively — this module uses it for the ONE case negotiation
genuinely needs a human in the loop: an irreversible-action disagreement (see data/config.json's
`irreversible_actions`), which `aixl/negotiation.py` has always REJECTed with the message "requires human
confirmation, not auto-resolved by trusting the sender" — a claim that, until now, had no actual mechanism
behind it. This closes that gap for real: the task pauses, asks a human (or another real agent) which
candidate is correct, and resumes with their answer instead of just giving up.

Reuses aixl.negotiation's own tested helpers (compare_canonical, worst_dimension, _dim_of_label,
_is_empty, _involves_irreversible_action) — imported, not reimplemented; aixl/negotiation.py itself is
untouched. Ordinary (non-irreversible) disagreements still auto-resolve in a single pass, exactly like
`negotiate()` — only an irreversible-action disagreement ever pauses the task."""
from google.protobuf.json_format import MessageToDict

from a2a.helpers.proto_helpers import new_data_message, new_task_from_user_message
from a2a.server.tasks import TaskUpdater
from a2a.types.a2a_pb2 import Role, TaskState

from aixl.core.ontology import load_config
from aixl.negotiation import (
    compare_canonical, worst_dimension, _dim_of_label, _is_empty, _involves_irreversible_action,
)

TUPLE_DIMS = {"actions", "entities", "data", "time", "location", "constraints", "conditions",
              "negation", "references", "quantities", "output", "modifiers"}


def _encode_canon(canon: dict) -> dict:
    return {k: (list(v) if isinstance(v, tuple) else v) for k, v in canon.items()}


def _decode_canon(canon: dict) -> dict:
    return {k: (tuple(v) if k in TUPLE_DIMS and isinstance(v, list) else v) for k, v in canon.items()}


def _advance(sender_canonical: dict, belief: dict, cfg: dict, round_: int, max_rounds: int):
    """Auto-resolve loop, identical logic to negotiate()'s round loop, except it STOPS and reports
    ('ask_human', ...) instead of REJECTing outright when it hits an irreversible-action disagreement.
    Returns ('accept', belief) | ('reject', reason, belief) | ('ask_human', dim, question, candidates, round_, belief).

    Check order (fetch -> empty-check -> irreversible-check) matters and must match
    aixl.negotiation._negotiate_core's order exactly, for the same reason documented there: an
    empty sender value and an irreversible receiver candidate are NOT mutually exclusive (d.target
    can be irreversible independent of whether the sender resolved anything at all). Getting this
    order backwards was caught by actually running the round-trip ("Quita el ticket #77." — an
    out-of-vocabulary sender verb — asked a human to pick between DELETE and NOT_SPECIFIED instead
    of correctly rejecting outright), not assumed correct from reading the code alone."""
    while round_ < max_rounds:
        result = compare_canonical(sender_canonical, belief, cfg)
        if result.equivalent:
            return ("accept", belief)
        d = worst_dimension(result)
        dim = _dim_of_label(d.field)
        round_ += 1
        sender_value = sender_canonical.get(dim, "")
        if dim == "actions" and _is_empty(sender_value):
            return ("reject", f"sender's own message does not resolve {d.field} either — "
                               f"cannot confirm which reading is correct", belief)
        if dim == "actions" and _involves_irreversible_action(d, cfg):
            question = (f"{d.field}: receiver read '{d.target}', sender's own message implies "
                        f"'{d.source}' — which is correct? This disagreement involves an "
                        f"irreversible action and needs a human decision.")
            return ("ask_human", dim, question, (d.target, d.source), round_, belief)
        belief = dict(belief)
        belief[dim] = sender_value
    result = compare_canonical(sender_canonical, belief, cfg)
    if result.equivalent:
        return ("accept", belief)
    return ("reject", f"no consensus after {max_rounds} rounds; "
                       f"{len(result.differences)} dimension(s) still differ", belief)


async def _apply_outcome(updater: TaskUpdater, outcome, sender_canonical: dict, max_rounds: int,
                          context_id: str, task_id: str) -> None:
    kind = outcome[0]
    if kind == "accept":
        _, belief = outcome
        msg = new_data_message({"converged": True, "canonical": _encode_canon(belief)},
                                role=Role.ROLE_AGENT, context_id=context_id, task_id=task_id)
        await updater.complete(message=msg)
    elif kind == "reject":
        _, reason, belief = outcome
        msg = new_data_message({"converged": False, "reason": reason},
                                role=Role.ROLE_AGENT, context_id=context_id, task_id=task_id)
        await updater.reject(message=msg)
    else:  # ask_human
        _, dim, question, candidates, round_, belief = outcome
        msg = new_data_message({"question": question, "field": dim, "candidates": list(candidates)},
                                role=Role.ROLE_AGENT, context_id=context_id, task_id=task_id)
        state = {
            "sender_canonical": _encode_canon(sender_canonical),
            "belief": _encode_canon(belief),
            "awaiting_dim": dim,
            "round": round_,
            "max_rounds": max_rounds,
        }
        await updater.update_status(TaskState.TASK_STATE_INPUT_REQUIRED, message=msg, metadata=state)


async def start_negotiation(context, event_queue, req: dict) -> None:
    import aixl
    sender_text = req.get("sender_text", "")
    receiver_text = req.get("receiver_text", "")
    max_rounds = int(req.get("max_rounds", 3))
    sender_canonical = aixl.to_semantic(sender_text).canonical()
    belief = aixl.to_semantic(receiver_text).canonical()
    cfg = load_config()

    task = new_task_from_user_message(context.message)
    await event_queue.enqueue_event(task)
    updater = TaskUpdater(event_queue, context.task_id, context.context_id)

    outcome = _advance(sender_canonical, belief, cfg, 0, max_rounds)
    await _apply_outcome(updater, outcome, sender_canonical, max_rounds, context.context_id, context.task_id)


async def resume_negotiation(context, event_queue, req: dict) -> None:
    task = context.current_task
    state = MessageToDict(task.metadata) if task.metadata else {}
    sender_canonical = _decode_canon(state["sender_canonical"])
    belief = _decode_canon(state["belief"])
    dim = state["awaiting_dim"]
    round_ = int(state["round"])
    max_rounds = int(state["max_rounds"])
    cfg = load_config()

    value = req.get("value", "")
    resolved = (tuple(value) if isinstance(value, list) else (value,)) if dim in TUPLE_DIMS else value
    # The human's answer is now the agreed ground truth for THIS dimension on BOTH sides, not just
    # the receiver's belief — pinning only belief[dim] left sender_canonical[dim] unchanged, so the
    # very next compare_canonical() call kept reporting the exact same disagreement all over again
    # (found by actually running the round-trip, not assumed: a real "Close/Delete ticket #77" human
    # resume kept coming back with the identical CLARIFY question instead of resolving).
    sender_canonical = dict(sender_canonical)
    sender_canonical[dim] = resolved
    belief = dict(belief)
    belief[dim] = resolved

    updater = TaskUpdater(event_queue, context.task_id, context.context_id)
    outcome = _advance(sender_canonical, belief, cfg, round_, max_rounds)
    await _apply_outcome(updater, outcome, sender_canonical, max_rounds, context.context_id, context.task_id)
