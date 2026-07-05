from __future__ import annotations

import ast
import inspect
import textwrap
from dataclasses import dataclass
from pathlib import Path

import pytest

from apv3test.runtime import (
    ExternalExpressionToken,
    IncrementalTickInput,
    IncrementalTickRuntime,
    observe_feeling_expression_cooccurrence,
)
from apv3test.runtime import draft_introspection as draft_introspection_module
from apv3test.runtime import reply_pressure as reply_pressure_module
from apv3test.runtime.cooccurrence_store import CooccurrenceAssociationStore


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
class _ReplayOutcome:
    first_label: str
    association_state: dict[str, object]
    emitted_tokens: tuple[str, ...]
    committed_text: str


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


def _teach_multi_reply(state: dict, runtime: IncrementalTickRuntime, *, suffix: str) -> dict:
    for step in tuple(
        _teach(
            tick,
            case_name=f"phase7_3f_multi_reply_{suffix}",
            cue_tokens=(SAN, GU),
            reply_tokens=(MAO, LU),
            context_tokens=("ctx_idiom",),
        )
        for tick in range(1, 31)
    ) + tuple(
        _teach(
            tick,
            case_name=f"phase7_3f_multi_reply_{suffix}",
            cue_tokens=(SAN, GU),
            reply_tokens=(CAO, LU, ZHI, ZHONG),
            context_tokens=("ctx_idiom",),
        )
        for tick in range(31, 61)
    ):
        state = runtime.run_tick(state, step).state
    return state


def _teach_expression_paradigm(state: dict, runtime: IncrementalTickRuntime, *, suffix: str) -> dict:
    for step in (
        _teach(
            70,
            case_name=f"phase7_3f_expression_{suffix}",
            cue_tokens=(STYLE_CUE,),
            reply_tokens=(EXPR_UNCERTAIN, "candidate::a"),
            context_tokens=("ctx_expression",),
        ),
        _teach(
            71,
            case_name=f"phase7_3f_expression_{suffix}",
            cue_tokens=(STYLE_CUE,),
            reply_tokens=(EXPR_UNCERTAIN, "candidate::b"),
            context_tokens=("ctx_expression",),
        ),
    ):
        state = runtime.run_tick(state, step).state
    return state


def _expression_pid(state: dict, *, suffix: str) -> str:
    tag = f"phase7_3f_expression_{suffix}"
    for row in state["paradigms"]:
        if tag in row.get("probe_tags", []):
            return str(row["pid"])
    raise AssertionError("expression paradigm not found")


def _recall_with_query(tick: int) -> IncrementalTickInput:
    return IncrementalTickInput(
        tick=tick,
        cue_tokens=(SAN, GU),
        context_tokens=("ctx_idiom",),
        emit_reply=True,
        commit_after_draft=True,
        grasp=1.2,
        demand_slow=0.1,
        incoming_external_query=("?",),
    )


def _run_blackbox_replay(*, suffix: str) -> _ReplayOutcome:
    runtime = IncrementalTickRuntime()
    state = _teach_expression_paradigm(_teach_multi_reply(_base_state(), runtime, suffix=suffix), runtime, suffix=suffix)

    first = runtime.run_tick(state, _recall_with_query(100))
    assert first.dialogue_result is not None
    assert first.dialogue_result.emitted_tokens == (LU,)
    assert first.dialogue_result.committed_text == ""
    state = first.dialogue_result.state
    labels = tuple(
        str(item.get("sa_label", ""))
        for item in state.get("introspection_feelings", [])
        if isinstance(item, dict) and int(item.get("tick", -1)) == 100
    )
    assert labels

    expression_pid = _expression_pid(state, suffix=suffix)
    store = CooccurrenceAssociationStore.from_state(state.get("cooccurrence_associations"))
    observe_feeling_expression_cooccurrence(
        store,
        labels,
        (
            ExternalExpressionToken(EXPR_UNCERTAIN, "teacher_reply", attention_weight=1.0, paradigm_id=expression_pid),
            ExternalExpressionToken("noise::nearby", "perception_other", attention_weight=0.1),
        ),
        current_tick=101,
    )
    state["cooccurrence_associations"] = store.export_state()

    second = runtime.run_tick(state, _recall_with_query(130))
    assert second.dialogue_result is not None
    return _ReplayOutcome(
        first_label=labels[-1],
        association_state=state["cooccurrence_associations"],
        emitted_tokens=second.dialogue_result.emitted_tokens,
        committed_text=second.dialogue_result.committed_text,
    )


def test_phase7_3f_blackbox_replay_learns_expression_after_observed_failure() -> None:
    outcome = _run_blackbox_replay(suffix="blackbox")

    assert outcome.emitted_tokens == (EXPR_UNCERTAIN, LU)
    assert outcome.committed_text == EXPR_UNCERTAIN + LU
    paradigm_pairs = outcome.association_state["paradigm_pairs"]
    assert paradigm_pairs
    assert paradigm_pairs[0]["key_a"] == outcome.first_label


@pytest.mark.parametrize(
    ("left_prefix", "right_prefix"),
    (
        ("opaqueA::", "opaqueB::"),
        ("feeling_x_", "inner_state_y_"),
        ("draft-affect/", "proto-affect/"),
    ),
)
def test_phase7_3f_label_bijection_keeps_behavior_opaque(
    monkeypatch: pytest.MonkeyPatch,
    left_prefix: str,
    right_prefix: str,
) -> None:
    monkeypatch.setattr(
        draft_introspection_module,
        "make_feeling_label",
        lambda prototype_id: f"{left_prefix}{int(prototype_id)}",
    )
    suffix = f"bij_{left_prefix.replace(':', '_').replace('/', '_')}_{right_prefix.replace(':', '_').replace('/', '_')}"
    left = _run_blackbox_replay(suffix=suffix)

    monkeypatch.setattr(
        draft_introspection_module,
        "make_feeling_label",
        lambda prototype_id: f"{right_prefix}{int(prototype_id)}",
    )
    right = _run_blackbox_replay(suffix=suffix)

    assert left.first_label != right.first_label
    assert left.first_label.removeprefix(left_prefix) == right.first_label.removeprefix(right_prefix)
    assert left.emitted_tokens == right.emitted_tokens == (EXPR_UNCERTAIN, LU)
    assert left.committed_text == right.committed_text == EXPR_UNCERTAIN + LU
    assert _normalize_assoc_labels(left.association_state, left_prefix) == _normalize_assoc_labels(
        right.association_state,
        right_prefix,
    )


def test_phase7_3f_ast_redlines_for_label_opacity_and_pressure_trace() -> None:
    runtime_root = Path(__file__).resolve().parents[1] / "apv3test" / "runtime"
    checked_files = (
        runtime_root / "draft_introspection.py",
        runtime_root / "cooccurrence_store.py",
        runtime_root / "cooccurrence_learning.py",
        runtime_root / "incremental_tick_runtime.py",
        runtime_root / "reply_pressure.py",
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in checked_files)
    for forbidden in (
        "must_reply",
        "undecidable_feeling_tokens",
        "feeling::undecidable",
        "find_by_cue_token",
        "_most_common_reply",
        "pressure_type_weights",
        "proto_0",
        "proto_1",
    ):
        assert forbidden not in combined
    assert combined.count("feeling::draft::proto_") == 1

    pressure_tree = ast.parse(inspect.getsource(reply_pressure_module))
    forbidden_pressure_fields = {"provenance", "sources", "dominant_source"}
    for node in ast.walk(pressure_tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden_pressure_fields
    pressure_fields = set(reply_pressure_module.ReplyPressureSA.__dataclass_fields__)
    assert pressure_fields.isdisjoint(forbidden_pressure_fields)


def test_phase7_3f_extract_facts_and_rebind_do_not_read_expression_content_as_feeling() -> None:
    tree = ast.parse(inspect.getsource(draft_introspection_module.extract_facts))
    allowed_view_attrs = {"role", "is_filled", "occupancy", "fit_margin", "commit_readiness"}
    forbidden_attrs = {
        "filler",
        "value",
        "cue",
        "label",
        "sa_label",
        "anchor_meta",
        "meta",
        "attrs",
        "__dict__",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden_attrs
            if isinstance(node.value, ast.Name) and node.value.id == "view":
                assert node.attr in allowed_view_attrs
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "getattr"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"startswith", "endswith", "__contains__"}

    rebind_tree = ast.parse(textwrap.dedent(inspect.getsource(IncrementalTickRuntime._run_learned_expression_reply)))
    string_literals = {
        node.value
        for node in ast.walk(rebind_tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert EXPR_UNCERTAIN not in string_literals
    assert LU not in string_literals
    assert "feeling::draft::proto_" not in string_literals


def _normalize_assoc_labels(payload: dict[str, object], prefix: str) -> dict[str, object]:
    def normalize(value: object) -> object:
        if isinstance(value, str) and value.startswith(prefix):
            return "LABEL#" + value.removeprefix(prefix)
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        return value

    return normalize(payload)  # type: ignore[return-value]
