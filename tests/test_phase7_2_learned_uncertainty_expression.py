from __future__ import annotations

from dataclasses import dataclass

from apv3test.runtime import IncrementalTickInput, IncrementalTickRuntime
from apv3test.runtime.cooccurrence_store import CooccurrenceAssociationStore
from apv3test.runtime.draft_introspection import emit_draft_introspection_feelings


SAN = "\u4e09"
GU = "\u987e"
MAO = "\u8305"
LU = "\u5e90"
CAO = "\u8349"
ZHI = "\u4e4b"
ZHONG = "\u4e2d"

EXPR_UNCERTAIN = "expr::uncertain"
STYLE_CUE = "style::uncertain_expression"


@dataclass(frozen=True)
class _View:
    role: str
    is_filled: bool
    fit_margin: float = 0.5
    occupancy: float = 0.5
    commit_readiness: float = 0.5


def _base_state() -> dict:
    return {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {
            "tokens": {
                "ctx_idiom": {"vector": [0.0, 1.0], "support": 4.0, "promoted": True},
                "ctx_expression": {"vector": [1.0, 0.0], "support": 4.0, "promoted": True},
            }
        },
        "transitions": [],
        "paradigms": [],
        "action_outcomes": {},
        "percept_prototypes": [],
    }


def _teach(
    tick: int,
    *,
    case_name: str,
    cue_tokens: tuple[str, ...],
    reply_tokens: tuple[str, ...],
    context_tokens: tuple[str, ...],
) -> IncrementalTickInput:
    return IncrementalTickInput(
        tick=tick,
        case_name=case_name,
        cue_tokens=cue_tokens,
        reply_tokens=reply_tokens,
        context_tokens=context_tokens,
        source_kind="natural",
        teacher_stage="",
        commit_observation=True,
        reward_delta=1.0,
    )


def _teach_multi_reply(state: dict, runtime: IncrementalTickRuntime) -> dict:
    for step in tuple(
        _teach(
            tick,
            case_name="phase7_2_multi_reply_migrated",
            cue_tokens=(SAN, GU),
            reply_tokens=(MAO, LU),
            context_tokens=("ctx_idiom",),
        )
        for tick in range(1, 31)
    ) + tuple(
        _teach(
            tick,
            case_name="phase7_2_multi_reply_migrated",
            cue_tokens=(SAN, GU),
            reply_tokens=(CAO, LU, ZHI, ZHONG),
            context_tokens=("ctx_idiom",),
        )
        for tick in range(31, 61)
    ):
        state = runtime.run_tick(state, step).state
    return state


def _teach_expression(state: dict, runtime: IncrementalTickRuntime) -> dict:
    for step in (
        _teach(
            70,
            case_name="phase7_2_expression_migrated",
            cue_tokens=(STYLE_CUE,),
            reply_tokens=(EXPR_UNCERTAIN, "candidate::a"),
            context_tokens=("ctx_expression",),
        ),
        _teach(
            71,
            case_name="phase7_2_expression_migrated",
            cue_tokens=(STYLE_CUE,),
            reply_tokens=(EXPR_UNCERTAIN, "candidate::b"),
            context_tokens=("ctx_expression",),
        ),
    ):
        state = runtime.run_tick(state, step).state
    return state


def _seed_association(state: dict) -> dict:
    state = emit_draft_introspection_feelings(
        state,
        (
            _View("slot", False, fit_margin=0.0, occupancy=0.0, commit_readiness=0.0),
            _View("shared_fragment", True, fit_margin=0.8, occupancy=1.0, commit_readiness=0.35),
        ),
        current_tick=80,
    )
    label = state["introspection_feelings"][-1]["sa_label"]
    expression_pid = _expression_pid(state)
    store = CooccurrenceAssociationStore()
    store.observe_paradigm(label, expression_pid, weight=1.0, current_tick=81)
    state["cooccurrence_associations"] = store.export_state()
    return state


def _expression_pid(state: dict) -> str:
    for row in state["paradigms"]:
        if "phase7_2_expression_migrated" in row.get("probe_tags", []):
            return str(row["pid"])
    raise AssertionError("expression paradigm not found")


def _recall(*, query: bool = True) -> IncrementalTickInput:
    return IncrementalTickInput(
        tick=100,
        cue_tokens=(SAN, GU),
        context_tokens=("ctx_idiom",),
        emit_reply=True,
        commit_after_draft=True,
        grasp=1.2,
        demand_slow=0.1,
        incoming_external_query=("?",) if query else (),
    )


def test_phase7_2_migrated_external_query_uses_learned_uncertainty_expression() -> None:
    runtime = IncrementalTickRuntime()
    state = _seed_association(_teach_expression(_teach_multi_reply(_base_state(), runtime), runtime))

    result = runtime.run_tick(state, _recall(query=True))

    assert result.recall_result is not None
    assert result.recall_result.focus is not None
    assert result.recall_result.focus.cn is not None
    assert result.recall_result.focus.cn.successor_tokens == (LU,)
    assert result.dialogue_result is not None
    assert result.dialogue_result.emitted_tokens == (EXPR_UNCERTAIN, LU)
    assert result.dialogue_result.committed_text == EXPR_UNCERTAIN + LU


def test_phase7_2_migrated_without_learned_association_stays_uncommitted() -> None:
    runtime = IncrementalTickRuntime()
    state = _teach_expression(_teach_multi_reply(_base_state(), runtime), runtime)

    result = runtime.run_tick(state, _recall(query=True))

    assert result.dialogue_result is not None
    assert result.dialogue_result.emitted_tokens == (LU,)
    assert result.dialogue_result.committed_text == ""
    assert result.dialogue_result.draft_candidates[0].anchor_meta["undecidable_fragment"] is True


def test_phase7_2_migrated_without_reply_pressure_stays_uncommitted() -> None:
    runtime = IncrementalTickRuntime()
    state = _seed_association(_teach_expression(_teach_multi_reply(_base_state(), runtime), runtime))

    result = runtime.run_tick(state, _recall(query=False))

    assert result.dialogue_result is not None
    assert result.dialogue_result.emitted_tokens == (LU,)
    assert result.dialogue_result.committed_text == ""

