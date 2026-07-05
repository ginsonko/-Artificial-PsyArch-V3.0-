from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from apv3test.runtime import (
    MinimalistDialogueFlowRuntime,
    MinimalistDialogueTurnInput,
    SQLiteRuntimeStore,
    assert_style_compliant,
)


@dataclass(frozen=True)
class _View:
    role: str
    is_filled: bool
    fit_margin: float = 0.7
    occupancy: float = 0.7
    commit_readiness: float = 0.5


UNCERTAIN_VIEWS = (
    _View("slot", False, 0.0, 0.0, 0.0),
    _View("shared_fragment", True, 0.9, 1.0, 0.35),
)
FLOW_VIEWS = (
    _View("slot", True, 0.95, 1.0, 0.95),
    _View("fixed_anchor", True, 0.95, 1.0, 0.95),
)
REQUEST_VIEWS = (
    _View("slot", True, 0.8, 1.0, 0.55),
    _View("fixed_anchor", True, 0.8, 1.0, 0.55),
)


def test_phase7_9_multiturn_observation_then_teacher_off_reply() -> None:
    runtime = MinimalistDialogueFlowRuntime()
    state: dict[str, object] = {"schema_id": "apv3_phase7_9_multiturn/v1"}
    outputs = []
    for tick in range(1, 5):
        result = runtime.run_turn(
            state,
            MinimalistDialogueTurnInput(
                tick=tick,
                incoming_external_query=("名字", "?"),
                views=UNCERTAIN_VIEWS,
                observed_expression_tokens=("不知道",) if tick <= 2 else (),
            ),
        )
        state = result.state
        outputs.append(result.committed_tokens)

    assert outputs[-1] == ("不知道",)
    assert all(len(tokens) <= 3 for tokens in outputs)
    assert all(_style_ok(tokens) for tokens in outputs)
    assert _trace(state)[-1]["learned_phrase_id"] == ""


def test_phase7_9_punishment_changes_next_same_feeling_recall() -> None:
    runtime = MinimalistDialogueFlowRuntime()
    state: dict[str, object] = {"schema_id": "apv3_phase7_9_feedback/v1"}

    first = runtime.run_turn(
        state,
        MinimalistDialogueTurnInput(
            tick=1,
            views=UNCERTAIN_VIEWS,
            observed_expression_tokens=("不知道",),
            observed_attention_weight=0.95,
        ),
    )
    second = runtime.run_turn(
        first.state,
        MinimalistDialogueTurnInput(
            tick=2,
            views=UNCERTAIN_VIEWS,
            punish_delta=1.4,
            observed_expression_tokens=("还不会",),
            observed_attention_weight=0.95,
        ),
    )
    third = runtime.run_turn(
        second.state,
        MinimalistDialogueTurnInput(tick=3, views=UNCERTAIN_VIEWS),
    )

    assert first.committed_tokens == ("不知道",)
    assert second.feedback_target_phrase_id == first.committed_phrase_id
    assert third.committed_tokens == ("还不会",)
    assert third.committed_phrase_id == "p:resp:cantyet"


def test_phase7_9_topic_switch_does_not_contaminate_current_feeling() -> None:
    runtime = MinimalistDialogueFlowRuntime()
    state: dict[str, object] = {"schema_id": "apv3_phase7_9_topic_switch/v1"}
    for tick in range(1, 5):
        result = runtime.run_turn(
            state,
            MinimalistDialogueTurnInput(
                tick=tick,
                views=UNCERTAIN_VIEWS,
                observed_expression_tokens=("不知道",),
            ),
        )
        state = result.state

    flow = runtime.run_turn(
        state,
        MinimalistDialogueTurnInput(
            tick=5,
            incoming_external_query=("天气",),
            context_tokens=("ctx::flow",),
            views=FLOW_VIEWS,
            observed_expression_tokens=("嗯",),
        ),
    )
    flow_teacher_off = runtime.run_turn(
        flow.state,
        MinimalistDialogueTurnInput(
            tick=6,
            incoming_external_query=("天气",),
            context_tokens=("ctx::flow",),
            views=FLOW_VIEWS,
        ),
    )

    assert flow_teacher_off.committed_tokens == ("嗯",)
    assert flow_teacher_off.feeling_label != result.feeling_label
    assert flow_teacher_off.committed_tokens != ("不知道",)


def test_phase7_9_sqlite_warmload_parity_mid_multiturn(tmp_path: Path) -> None:
    continuous = _run_sequence()
    split = _run_sequence(split_at=3, tmp_path=tmp_path)

    assert _external_summary(continuous) == _external_summary(split)


def test_phase7_9_freeform_multiturn_style_redlines_hold() -> None:
    runtime = MinimalistDialogueFlowRuntime()
    state: dict[str, object] = {"schema_id": "apv3_phase7_9_style/v1"}
    outputs = []
    sequence = (
        (UNCERTAIN_VIEWS, ("不知道",)),
        (FLOW_VIEWS, ("嗯",)),
        (REQUEST_VIEWS, ("教教",)),
    )
    for tick in range(1, 121):
        views, phrase = sequence[(tick - 1) % len(sequence)]
        result = runtime.run_turn(
            state,
            MinimalistDialogueTurnInput(
                tick=tick,
                views=views,
                observed_expression_tokens=phrase if tick <= 9 else (),
            ),
        )
        state = result.state
        outputs.append(result.committed_tokens)

    assert len(outputs) == 120
    assert all(len(tokens) <= 3 for tokens in outputs)
    assert all(_style_ok(tokens) for tokens in outputs)
    assert sum(1 for tokens in outputs if "我" in "".join(tokens)) == 0


def test_phase7_9_runtime_redline_has_no_multiturn_script_routes() -> None:
    runtime_root = Path(__file__).resolve().parents[1] / "apv3test" / "runtime"
    combined = "\n".join(path.read_text(encoding="utf-8") for path in runtime_root.glob("*.py"))
    for forbidden in (
        "phase7_9_",
        "incoming_external_query ==",
        "case_name ==",
        "answer_table",
        "student_side_llm",
        "_most_common_reply",
        "must_reply",
        "if record.phrase_kind",
        "phrase_kind ==",
    ):
        assert forbidden not in combined


def _run_sequence(*, split_at: int | None = None, tmp_path: Path | None = None) -> dict[str, object]:
    runtime = MinimalistDialogueFlowRuntime()
    state: dict[str, object] = {"schema_id": "apv3_phase7_9_sqlite/v1"}
    turns = (
        MinimalistDialogueTurnInput(tick=1, views=UNCERTAIN_VIEWS, observed_expression_tokens=("不知道",)),
        MinimalistDialogueTurnInput(tick=2, views=FLOW_VIEWS, observed_expression_tokens=("嗯",)),
        MinimalistDialogueTurnInput(tick=3, views=REQUEST_VIEWS, observed_expression_tokens=("教教",)),
        MinimalistDialogueTurnInput(tick=4, views=UNCERTAIN_VIEWS),
        MinimalistDialogueTurnInput(tick=5, views=FLOW_VIEWS),
        MinimalistDialogueTurnInput(tick=6, views=REQUEST_VIEWS),
    )
    for index, turn in enumerate(turns, start=1):
        result = runtime.run_turn(state, turn)
        state = result.state
        if split_at is not None and index == split_at:
            assert tmp_path is not None
            store = SQLiteRuntimeStore(tmp_path / "phase7_9.sqlite")
            state = store.load_state(store.save_state(state))
    return state


def _trace(state: dict[str, object]) -> list[dict[str, object]]:
    rows = state.get("minimalist_dialogue_trace", [])
    assert isinstance(rows, list)
    return [row for row in rows if isinstance(row, dict)]


def _external_summary(state: dict[str, object]) -> tuple[tuple[str, str], ...]:
    return tuple(
        (str(row.get("committed_phrase_id", "")), str(row.get("committed_text", "")))
        for row in _trace(state)
    )


def _style_ok(tokens: tuple[str, ...]) -> bool:
    try:
        assert_style_compliant(tokens)
    except AssertionError:
        return False
    return True
