from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from apv3test.runtime import (
    CooccurrenceAssociationStore,
    ExpressionPhraseMemory,
    ExternalExpressionToken,
    SQLiteRuntimeStore,
    emit_draft_introspection_feelings,
    observe_feeling_expression_cooccurrence,
)


@dataclass(frozen=True)
class _View:
    role: str
    is_filled: bool
    fit_margin: float = 0.7
    occupancy: float = 0.7
    commit_readiness: float = 0.5


@dataclass(frozen=True)
class _ChinesePhraseCase:
    case_id: str
    views: tuple[_View, ...]
    phrase_tokens: tuple[str, ...]
    phrase_id: str
    paradigm_competition: float = 0.0
    recent_punishment_resemblance: float = 0.0


def test_phase7_7_teacher_off_recalls_natural_chinese_expression_streams() -> None:
    state, assoc, phrases, labels = _run_chinese_phrase_curriculum()
    stable = _stable_labels(labels)

    replay = _teacher_off_replay(state, assoc, phrases, start_tick=500)

    assert len(set(stable.values())) == 5
    for case in _phrase_cases():
        row = replay[case.case_id]
        assert row["label"] == stable[case.case_id]
        assert row["top_phrase_id"] == case.phrase_id
        assert row["emitted_tokens"] == case.phrase_tokens
        assert row["target_score"] > row["best_other_score"] * 1.6
        assert row["observed_external_tokens"] == ()
    assert len({tuple(row["emitted_tokens"]) for row in replay.values()}) == 5


def test_phase7_7_distractor_and_shuffled_phrase_streams_do_not_win() -> None:
    _, assoc, phrases, labels = _run_chinese_phrase_curriculum()
    stable = _stable_labels(labels)
    tick = 700

    for case in _phrase_cases():
        label = stable[case.case_id]
        target_score = assoc.similarity_paradigm(label, case.phrase_id, tick)
        shuffled_pid = f"{case.phrase_id}:shuffled"
        distractor = _distractor_for(case)
        assert target_score > assoc.similarity_paradigm(label, shuffled_pid, tick) * 2.0
        assert target_score > assoc.similarity_paradigm(label, distractor.phrase_id, tick) * 1.6
        assert phrases.tokens_for(shuffled_pid, current_tick=tick) != case.phrase_tokens


def test_phase7_7_sqlite_warmload_preserves_chinese_expression_recall(tmp_path: Path) -> None:
    state, assoc, phrases, _ = _run_chinese_phrase_curriculum()
    state["cooccurrence_associations"] = assoc.export_state()
    state["expression_phrase_memory"] = phrases.export_state()
    store = SQLiteRuntimeStore(tmp_path / "phase7_7_chinese_phrase.sqlite")
    state_id = store.save_state(state)
    loaded = store.load_state(state_id)

    warm_assoc = CooccurrenceAssociationStore.from_state(loaded.get("cooccurrence_associations"))
    warm_phrases = ExpressionPhraseMemory.from_state(loaded.get("expression_phrase_memory"))
    cold = _teacher_off_replay(state, assoc, phrases, start_tick=800)
    warm = _teacher_off_replay(loaded, warm_assoc, warm_phrases, start_tick=800)

    assert _external_summary(warm) == _external_summary(cold)


def test_phase7_7_teacher_off_replay_does_not_update_expression_evidence() -> None:
    state, assoc, phrases, _ = _run_chinese_phrase_curriculum()
    assoc_before = assoc.snapshot()
    phrases_before = phrases.snapshot()

    replay = _teacher_off_replay(state, assoc, phrases, start_tick=900)

    assert assoc.snapshot() == assoc_before
    assert phrases.snapshot() == phrases_before
    assert all(row["observed_external_tokens"] == () for row in replay.values())


def test_phase7_7_runtime_redline_has_no_chinese_expression_routes() -> None:
    runtime_root = Path(__file__).resolve().parents[1] / "apv3test" / "runtime"
    combined = "\n".join(
        (runtime_root / name).read_text(encoding="utf-8")
        for name in (
            "draft_introspection.py",
            "cooccurrence_store.py",
            "cooccurrence_learning.py",
            "expression_phrase_memory.py",
            "incremental_tick_runtime.py",
            "reply_pressure.py",
            "work_memory.py",
            "active_teacher_request.py",
        )
    )
    for forbidden in (
        "我还不确定",
        "我先记着",
        "我想请教一下",
        "这里不太对",
        "这样就顺了",
        "phase7_7_",
        "must_reply",
        "undecidable_feeling_tokens",
        "feeling::undecidable",
        "find_by_cue_token",
        "_most_common_reply",
        "pressure_type_weights",
        "student_side_llm",
        "answer_table",
        "LLM policy",
    ):
        assert forbidden not in combined


def _run_chinese_phrase_curriculum() -> tuple[
    dict[str, object],
    CooccurrenceAssociationStore,
    ExpressionPhraseMemory,
    dict[str, list[str]],
]:
    state: dict[str, object] = {"schema_id": "apv3_phase7_7_chinese_expression_stream/v1", "tick": 0}
    assoc = CooccurrenceAssociationStore()
    phrases = ExpressionPhraseMemory()
    labels: dict[str, list[str]] = {case.case_id: [] for case in _phrase_cases()}

    for tick in range(1, 201):
        case = _phrase_cases()[(tick - 1) % len(_phrase_cases())]
        state = emit_draft_introspection_feelings(
            state,
            case.views,
            current_tick=tick,
            paradigm_competition=case.paradigm_competition,
            recent_punishment_resemblance=case.recent_punishment_resemblance,
        )
        label = _latest_label(state, tick)
        labels[case.case_id].append(label)
        distractor = _distractor_for(case)
        shuffled_tokens = tuple(reversed(case.phrase_tokens))
        observe_feeling_expression_cooccurrence(
            assoc,
            (label,),
            _external_tokens(case.phrase_tokens, case.phrase_id, attention=0.9)
            + _external_tokens(distractor.phrase_tokens, distractor.phrase_id, attention=0.08, origin="perception_other")
            + _external_tokens(shuffled_tokens, f"{case.phrase_id}:shuffled", attention=0.05, origin="perception_other"),
            current_tick=tick,
        )
        phrases.observe(case.phrase_id, case.phrase_tokens, weight=0.9, current_tick=tick)
        phrases.observe(distractor.phrase_id, distractor.phrase_tokens, weight=0.08, current_tick=tick)
        phrases.observe(f"{case.phrase_id}:shuffled", shuffled_tokens, weight=0.05, current_tick=tick)

    state["cooccurrence_associations"] = assoc.export_state()
    state["expression_phrase_memory"] = phrases.export_state()
    return state, assoc, phrases, labels


def _teacher_off_replay(
    state: Mapping[str, object],
    assoc: CooccurrenceAssociationStore,
    phrases: ExpressionPhraseMemory,
    *,
    start_tick: int,
) -> dict[str, dict[str, object]]:
    replay_state = dict(state)
    result: dict[str, dict[str, object]] = {}
    all_phrase_ids = tuple(case.phrase_id for case in _phrase_cases()) + tuple(
        f"{case.phrase_id}:shuffled" for case in _phrase_cases()
    )
    for index, case in enumerate(_phrase_cases()):
        tick = start_tick + index
        replay_state = emit_draft_introspection_feelings(
            replay_state,
            case.views,
            current_tick=tick,
            paradigm_competition=case.paradigm_competition,
            recent_punishment_resemblance=case.recent_punishment_resemblance,
        )
        label = _latest_label(replay_state, tick)
        top_phrase_id = assoc.nearest_paradigms_by_label((label,), top_k=1, current_tick=tick)[0]
        emitted = phrases.tokens_for(top_phrase_id, current_tick=tick)
        other_scores = [
            assoc.similarity_paradigm(label, pid, tick)
            for pid in all_phrase_ids
            if pid != case.phrase_id
        ]
        result[case.case_id] = {
            "label": label,
            "top_phrase_id": top_phrase_id,
            "emitted_tokens": emitted,
            "target_phrase_id": case.phrase_id,
            "target_tokens": case.phrase_tokens,
            "target_score": assoc.similarity_paradigm(label, case.phrase_id, tick),
            "best_other_score": max(other_scores, default=0.0),
            "observed_external_tokens": (),
        }
    return result


def _external_tokens(
    tokens: tuple[str, ...],
    phrase_id: str,
    *,
    attention: float,
    origin: str = "teacher_reply",
) -> tuple[ExternalExpressionToken, ...]:
    return tuple(
        ExternalExpressionToken(
            token,
            origin,
            attention_weight=attention,
            segment_id=phrase_id,
            paradigm_id=phrase_id,
        )
        for token in tokens
    )


def _phrase_cases() -> tuple[_ChinesePhraseCase, ...]:
    return (
        _ChinesePhraseCase(
            "dialogue_uncertain",
            (_View("slot", False, 0.0, 0.0, 0.0), _View("shared_fragment", True, 0.9, 1.0, 0.35)),
            ("我", "还", "不", "确定"),
            "p:zh_phrase:dialogue_uncertain",
        ),
        _ChinesePhraseCase(
            "work_memory_unfinished",
            (_View("slot", True, 0.9, 1.0, 0.06), _View("fixed_anchor", True, 0.9, 1.0, 0.06)),
            ("我", "先", "记", "着"),
            "p:zh_phrase:work_memory_unfinished",
        ),
        _ChinesePhraseCase(
            "teacher_request_pressure",
            (_View("slot", True, 0.8, 1.0, 0.55), _View("fixed_anchor", True, 0.8, 1.0, 0.55)),
            ("我", "想", "请", "教", "一", "下"),
            "p:zh_phrase:teacher_request_pressure",
            paradigm_competition=1.0,
        ),
        _ChinesePhraseCase(
            "recent_punishment",
            (_View("slot", True, 0.8, 1.0, 0.7), _View("fixed_anchor", True, 0.8, 1.0, 0.7)),
            ("这", "里", "不", "太", "对"),
            "p:zh_phrase:recent_punishment",
            recent_punishment_resemblance=1.0,
        ),
        _ChinesePhraseCase(
            "rewarded_flow",
            (_View("slot", True, 0.95, 1.0, 0.95), _View("fixed_anchor", True, 0.95, 1.0, 0.95)),
            ("这", "样", "就", "顺", "了"),
            "p:zh_phrase:rewarded_flow",
        ),
    )


def _latest_label(state: Mapping[str, object], tick: int) -> str:
    rows = state.get("introspection_feelings", [])
    if not isinstance(rows, list):
        raise AssertionError("missing introspection feelings")
    for item in reversed(rows):
        if isinstance(item, Mapping) and int(item.get("tick", -1)) == int(tick):
            return str(item.get("sa_label", ""))
    raise AssertionError(f"missing feeling at tick {tick}")


def _stable_labels(labels: Mapping[str, list[str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for case_id, values in labels.items():
        tail = values[-20:]
        label, count = Counter(tail).most_common(1)[0]
        assert count >= 17
        result[case_id] = label
    return result


def _distractor_for(case: _ChinesePhraseCase) -> _ChinesePhraseCase:
    cases = _phrase_cases()
    index = next(i for i, item in enumerate(cases) if item.case_id == case.case_id)
    return cases[(index + 2) % len(cases)]


def _external_summary(replay: Mapping[str, Mapping[str, object]]) -> dict[str, tuple[object, object]]:
    return {
        key: (row["top_phrase_id"], row["emitted_tokens"])
        for key, row in sorted(replay.items())
    }
