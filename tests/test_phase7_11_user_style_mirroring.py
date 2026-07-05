from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from apv3test.runtime import (
    CooccurrenceAssociationStore,
    ExpressionPhraseMemory,
    MinimalistDialogueFlowRuntime,
    MinimalistDialogueTurnInput,
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


USER_A_PHRASES = (("嗯",), ("哦",), ("试试",))
USER_B_PHRASES = (("好",), ("可以",), ("再说一次",))


def test_phase7_11_user_a_style_topk_converges_to_user_a_phrases() -> None:
    state = _train_user_style(USER_A_PHRASES, n_ticks=500)
    top = _top_phrase_tokens(state, top_k=3)

    assert _jaccard(top, USER_A_PHRASES) >= 0.6
    assert all(_style_ok(tokens) for tokens in top)


def test_phase7_11_user_b_style_topk_converges_to_user_b_phrases() -> None:
    state = _train_user_style(USER_B_PHRASES, n_ticks=500)
    top = _top_phrase_tokens(state, top_k=3)

    assert _jaccard(top, USER_B_PHRASES) >= 0.6
    assert all(_style_ok(tokens) for tokens in top)


def test_phase7_11_same_feeling_outputs_differ_between_users() -> None:
    state_a = _train_user_style(USER_A_PHRASES, n_ticks=500)
    state_b = _train_user_style(USER_B_PHRASES, n_ticks=500)
    top_a = _top_phrase_tokens(state_a, top_k=3)
    top_b = _top_phrase_tokens(state_b, top_k=3)

    assert _jaccard(top_a, top_b) <= 0.25
    assert _teacher_off_output(state_a) in top_a
    assert _teacher_off_output(state_b) in top_b
    assert _teacher_off_output(state_a) != _teacher_off_output(state_b)


def test_phase7_11_unknown_user_phrase_does_not_enter_phrase_memory() -> None:
    state = _train_user_style((("我", "完整", "解释", "一下"),), n_ticks=30)
    memory = ExpressionPhraseMemory.from_state(state.get("expression_phrase_memory"))
    trace = _trace(state)

    assert len(memory.records) == 120
    assert all(row.get("learned_phrase_id", "") == "" for row in trace)
    assert memory.phrase_id_for_tokens(("我", "完整", "解释", "一下")) == ""


def test_phase7_11_commit_texts_are_seed_corpus_only() -> None:
    state = _train_user_style(USER_A_PHRASES + USER_B_PHRASES, n_ticks=300)
    memory = ExpressionPhraseMemory.from_state(state.get("expression_phrase_memory"))
    seed_tokens = {record.tokens for record in memory.records}
    committed = [tuple(row.get("committed_tokens", ())) for row in _trace(state) if row.get("committed_tokens")]

    assert committed
    assert all(tokens in seed_tokens for tokens in committed)
    assert all(_style_ok(tokens) for tokens in committed)


def test_phase7_11_runtime_redline_has_no_user_style_routes() -> None:
    runtime_root = Path(__file__).resolve().parents[1] / "apv3test" / "runtime"
    combined = "\n".join(path.read_text(encoding="utf-8") for path in runtime_root.glob("*.py"))
    for forbidden in (
        "USER_A",
        "USER_B",
        "user_style ==",
        "answer_table",
        "student_side_llm",
        "_most_common_reply",
        "must_reply",
        "incoming_external_query ==",
    ):
        assert forbidden not in combined


def _train_user_style(phrases: tuple[tuple[str, ...], ...], *, n_ticks: int) -> dict[str, object]:
    runtime = MinimalistDialogueFlowRuntime()
    state: dict[str, object] = {"schema_id": "apv3_phase7_11_user_style/v1"}
    for tick in range(1, n_ticks + 1):
        phrase = phrases[(tick - 1) % len(phrases)]
        result = runtime.run_turn(
            state,
            MinimalistDialogueTurnInput(
                tick=tick,
                views=UNCERTAIN_VIEWS,
                incoming_external_query=(f"user_turn::{tick}",),
                observed_expression_tokens=phrase,
                observed_attention_weight=0.72,
                reward_delta=0.03 if tick % 19 == 0 else 0.0,
            ),
        )
        state = result.state
    return state


def _top_phrase_tokens(state: dict[str, object], *, top_k: int) -> tuple[tuple[str, ...], ...]:
    label = _dominant_label(state)
    assoc = CooccurrenceAssociationStore.from_state(state.get("cooccurrence_associations"))
    memory = ExpressionPhraseMemory.from_state(state.get("expression_phrase_memory"))
    pids = assoc.nearest_paradigms_by_label((label,), top_k=top_k * 3, current_tick=999)
    return tuple(record.tokens for record in memory.recall(pids, top_k=top_k, current_tick=999))


def _teacher_off_output(state: dict[str, object]) -> tuple[str, ...]:
    runtime = MinimalistDialogueFlowRuntime()
    result = runtime.run_turn(
        state,
        MinimalistDialogueTurnInput(tick=999, views=UNCERTAIN_VIEWS),
    )
    return result.committed_tokens


def _dominant_label(state: dict[str, object]) -> str:
    labels = [
        str(row.get("feeling_label", ""))
        for row in _trace(state)
        if isinstance(row, dict) and row.get("feeling_label")
    ]
    return Counter(labels).most_common(1)[0][0]


def _trace(state: dict[str, object]) -> list[dict[str, object]]:
    rows = state.get("minimalist_dialogue_trace", [])
    assert isinstance(rows, list)
    return [row for row in rows if isinstance(row, dict)]


def _jaccard(left: tuple[tuple[str, ...], ...], right: tuple[tuple[str, ...], ...]) -> float:
    a = set(left)
    b = set(right)
    if not a and not b:
        return 1.0
    return len(a & b) / max(1, len(a | b))


def _style_ok(tokens: tuple[str, ...]) -> bool:
    try:
        assert_style_compliant(tokens)
    except AssertionError:
        return False
    return True
