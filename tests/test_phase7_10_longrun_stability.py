from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import random

from apv3test.runtime import (
    CooccurrenceAssociationStore,
    ExpressionPhraseMemory,
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
PUNISH_VIEWS = (
    _View("slot", True, 0.8, 1.0, 0.7),
    _View("fixed_anchor", True, 0.8, 1.0, 0.7),
)


def test_phase7_10_longrun_stability_health_metrics() -> None:
    state = _run_long_dialogue(n_ticks=5000)
    trace = _trace(state)
    memory = ExpressionPhraseMemory.from_state(state.get("expression_phrase_memory"))
    assoc = CooccurrenceAssociationStore.from_state(state.get("cooccurrence_associations"))
    supports = [record.support for record in memory.records]
    outputs = [tuple(row.get("committed_tokens", ())) for row in trace]
    top5_share = _top_n_share(supports, 5)
    prototype_count = len(state.get("introspection_prototype_store", {}).get("prototypes", []))

    assert len(trace) == 5000
    assert len(memory.records) == 120
    assert top5_share < 0.8
    assert _gini(supports) < 0.72
    assert 3 <= prototype_count <= 12
    assert len(assoc.pairs) <= 80
    assert len(assoc.paradigm_pairs) <= 80
    assert all(_style_ok(tokens) for tokens in outputs)
    assert sum(1 for tokens in outputs if "我" in "".join(tokens)) == 0


def test_phase7_10_longrun_repeated_sqlite_warmload_parity(tmp_path: Path) -> None:
    sequence = _dialogue_sequence(1800)
    continuous = _run_long_dialogue(sequence=sequence)
    split = _run_long_dialogue(sequence=sequence, split_points=(450, 900, 1350), tmp_path=tmp_path)

    assert _external_summary(split) == _external_summary(continuous)


def test_phase7_10_longrun_test_uses_tmp_sqlite_only(tmp_path: Path) -> None:
    db_path = tmp_path / "phase7_10_guard.sqlite"
    state = _run_long_dialogue(n_ticks=120, split_points=(60,), tmp_path=tmp_path, db_name=db_path.name)

    assert db_path.exists()
    assert "minimalist_dialogue_trace" in state
    assert not (Path.cwd() / "phase7_10_guard.sqlite").exists()


def test_phase7_10_runtime_redline_has_no_longrun_routes() -> None:
    runtime_root = Path(__file__).resolve().parents[1] / "apv3test" / "runtime"
    combined = "\n".join(path.read_text(encoding="utf-8") for path in runtime_root.glob("*.py"))
    for forbidden in (
        "phase7_10_",
        "longrun",
        "incoming_external_query ==",
        "answer_table",
        "student_side_llm",
        "_most_common_reply",
        "must_reply",
    ):
        assert forbidden not in combined


def _run_long_dialogue(
    *,
    n_ticks: int | None = None,
    sequence: tuple[int, ...] | None = None,
    split_points: tuple[int, ...] = (),
    tmp_path: Path | None = None,
    db_name: str = "phase7_10.sqlite",
) -> dict[str, object]:
    runtime = MinimalistDialogueFlowRuntime()
    state: dict[str, object] = {"schema_id": "apv3_phase7_10_longrun/v1"}
    seq = sequence if sequence is not None else _dialogue_sequence(int(n_ticks or 5000))
    for tick, kind in enumerate(seq, start=1):
        result = runtime.run_turn(state, _turn_for(kind, tick))
        state = result.state
        if tick in set(split_points):
            assert tmp_path is not None
            store = SQLiteRuntimeStore(tmp_path / db_name)
            state = store.load_state(store.save_state(state))
    return state


def _dialogue_sequence(n_ticks: int) -> tuple[int, ...]:
    rng = random.Random(7910)
    base = [0, 1, 2, 3] * 12
    while len(base) < n_ticks:
        base.append(rng.randrange(0, 4))
    return tuple(base[:n_ticks])


def _turn_for(kind: int, tick: int) -> MinimalistDialogueTurnInput:
    views, phrases = (
        (UNCERTAIN_VIEWS, (("不知道",), ("还不会",), ("不确定",))),
        (FLOW_VIEWS, (("嗯",), ("好",), ("真好"))),
        (REQUEST_VIEWS, (("教教",), ("再说",), ("试试"))),
        (PUNISH_VIEWS, (("不对",), ("不太懂",), ("慢一点"))),
    )[kind]
    phrase = phrases[tick % len(phrases)] if tick % 5 != 0 else ()
    return MinimalistDialogueTurnInput(
        tick=tick,
        incoming_external_query=(f"turn::{tick}",),
        context_tokens=(f"context::{kind}",),
        views=views,
        observed_expression_tokens=phrase,
        observed_attention_weight=0.62,
        reward_delta=0.05 if tick % 17 == 0 else 0.0,
        punish_delta=0.04 if tick % 29 == 0 else 0.0,
    )


def _trace(state: dict[str, object]) -> list[dict[str, object]]:
    rows = state.get("minimalist_dialogue_trace", [])
    assert isinstance(rows, list)
    return [row for row in rows if isinstance(row, dict)]


def _external_summary(state: dict[str, object]) -> tuple[tuple[str, str], ...]:
    rows = _trace(state)[-120:]
    return tuple((str(row.get("committed_phrase_id", "")), str(row.get("committed_text", ""))) for row in rows)


def _style_ok(tokens: tuple[object, ...]) -> bool:
    try:
        assert_style_compliant(tuple(str(token) for token in tokens))
    except AssertionError:
        return False
    return True


def _top_n_share(values: list[float], n: int) -> float:
    total = sum(max(0.0, value) for value in values)
    if total <= 0.0:
        return 0.0
    return sum(sorted((max(0.0, value) for value in values), reverse=True)[:n]) / total


def _gini(values: list[float]) -> float:
    rows = sorted(max(0.0, value) for value in values)
    if not rows or sum(rows) <= 0.0:
        return 0.0
    weighted = sum((index + 1) * value for index, value in enumerate(rows))
    return (2.0 * weighted) / (len(rows) * sum(rows)) - (len(rows) + 1.0) / len(rows)
