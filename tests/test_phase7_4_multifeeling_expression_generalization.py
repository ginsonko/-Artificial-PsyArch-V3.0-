from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pytest

from apv3test.runtime import ExternalExpressionToken, observe_feeling_expression_cooccurrence
from apv3test.runtime import draft_introspection as draft_introspection_module
from apv3test.runtime.cooccurrence_store import CooccurrenceAssociationStore
from apv3test.runtime.draft_introspection import emit_draft_introspection_feelings


@dataclass(frozen=True)
class _View:
    role: str
    is_filled: bool
    fit_margin: float = 0.7
    occupancy: float = 0.7
    commit_readiness: float = 0.5


@dataclass(frozen=True)
class _StructuralEpisode:
    episode_id: str
    views: tuple[_View, ...]
    expression_token: str
    expression_pid: str
    paradigm_competition: float = 0.0
    recent_punishment_resemblance: float = 0.0


EPISODES: tuple[_StructuralEpisode, ...] = (
    _StructuralEpisode(
        "structure_0",
        (
            _View("slot", False, fit_margin=0.0, occupancy=0.0, commit_readiness=0.0),
            _View("shared_fragment", True, fit_margin=0.9, occupancy=1.0, commit_readiness=0.35),
        ),
        "expr::band_0",
        "p:expr:band_0",
    ),
    _StructuralEpisode(
        "structure_1",
        (
            _View("slot", True, fit_margin=0.9, occupancy=1.0, commit_readiness=0.05),
            _View("fixed_anchor", True, fit_margin=0.9, occupancy=1.0, commit_readiness=0.05),
        ),
        "expr::band_1",
        "p:expr:band_1",
    ),
    _StructuralEpisode(
        "structure_2",
        (
            _View("slot", True, fit_margin=0.8, occupancy=1.0, commit_readiness=0.7),
            _View("fixed_anchor", True, fit_margin=0.8, occupancy=1.0, commit_readiness=0.7),
        ),
        "expr::band_2",
        "p:expr:band_2",
        paradigm_competition=1.0,
    ),
    _StructuralEpisode(
        "structure_3",
        (
            _View("slot", True, fit_margin=0.8, occupancy=1.0, commit_readiness=0.7),
            _View("fixed_anchor", True, fit_margin=0.8, occupancy=1.0, commit_readiness=0.7),
        ),
        "expr::band_3",
        "p:expr:band_3",
        recent_punishment_resemblance=1.0,
    ),
    _StructuralEpisode(
        "structure_4",
        (
            _View("slot", False, fit_margin=0.2, occupancy=0.1, commit_readiness=0.2),
            _View("slot", False, fit_margin=0.2, occupancy=0.1, commit_readiness=0.2),
        ),
        "expr::band_4",
        "p:expr:band_4",
    ),
)


def test_phase7_4_multifeeling_curriculum_learns_distinct_expression_associations() -> None:
    state, store, labels_by_episode = _run_multifeeling_curriculum()

    stable_labels = _stable_labels(labels_by_episode)
    assert len(set(stable_labels.values())) >= 5
    active_prototypes = _active_prototypes(state)
    assert len(active_prototypes) >= 5
    assert all(float(item["activation_ema"]) > 1.0 for item in active_prototypes)

    confusion = _teacher_off_confusion_matrix(state, store, start_tick=400)
    for episode in EPISODES:
        row = confusion[episode.episode_id]
        assert row["label"] == stable_labels[episode.episode_id]
        assert row["top_token"] == episode.expression_token
        assert row["top_paradigm"] == episode.expression_pid
        assert row["target_score"] > row["best_other_score"] * 1.5

    assert len({row["top_token"] for row in confusion.values()}) == len(EPISODES)


def test_phase7_4_multifeeling_teacher_off_replay_has_no_external_expression_input() -> None:
    state, store, _ = _run_multifeeling_curriculum()
    before = store.snapshot()

    confusion = _teacher_off_confusion_matrix(state, store, start_tick=700)

    assert store.snapshot() == before
    assert all(row["observed_external_tokens"] == () for row in confusion.values())
    assert all(row["top_token"].startswith("expr::band_") for row in confusion.values())


@pytest.mark.parametrize(("left_prefix", "right_prefix"), (("mfA::", "mfB::"), ("inner-a/", "inner-b/")))
def test_phase7_4_multifeeling_label_bijection_keeps_recall_opaque(
    monkeypatch: pytest.MonkeyPatch,
    left_prefix: str,
    right_prefix: str,
) -> None:
    monkeypatch.setattr(
        draft_introspection_module,
        "make_feeling_label",
        lambda prototype_id: f"{left_prefix}{int(prototype_id)}",
    )
    left_state, left_store, _ = _run_multifeeling_curriculum()
    left_confusion = _teacher_off_confusion_matrix(left_state, left_store, start_tick=900)

    monkeypatch.setattr(
        draft_introspection_module,
        "make_feeling_label",
        lambda prototype_id: f"{right_prefix}{int(prototype_id)}",
    )
    right_state, right_store, _ = _run_multifeeling_curriculum()
    right_confusion = _teacher_off_confusion_matrix(right_state, right_store, start_tick=900)

    assert _external_recall(left_confusion) == _external_recall(right_confusion)
    assert _normalized_labels(left_confusion, left_prefix) == _normalized_labels(right_confusion, right_prefix)


def test_phase7_4_runtime_redline_has_no_multifeeling_semantic_routes() -> None:
    runtime_root = Path(__file__).resolve().parents[1] / "apv3test" / "runtime"
    combined = "\n".join(
        (runtime_root / name).read_text(encoding="utf-8")
        for name in (
            "draft_introspection.py",
            "cooccurrence_store.py",
            "cooccurrence_learning.py",
            "incremental_tick_runtime.py",
            "reply_pressure.py",
        )
    )
    for forbidden in (
        "expr::band_",
        "structure_",
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


def _run_multifeeling_curriculum() -> tuple[dict[str, object], CooccurrenceAssociationStore, dict[str, list[str]]]:
    state: dict[str, object] = {"tick": 0}
    store = CooccurrenceAssociationStore()
    labels_by_episode: dict[str, list[str]] = {episode.episode_id: [] for episode in EPISODES}
    for offset in range(250):
        episode = EPISODES[offset % len(EPISODES)]
        tick = offset + 1
        state = emit_draft_introspection_feelings(
            state,
            episode.views,
            current_tick=tick,
            paradigm_competition=episode.paradigm_competition,
            recent_punishment_resemblance=episode.recent_punishment_resemblance,
        )
        label = _latest_label(state, tick)
        labels_by_episode[episode.episode_id].append(label)
        distractor = EPISODES[(offset + 2) % len(EPISODES)]
        observe_feeling_expression_cooccurrence(
            store,
            (label,),
            (
                ExternalExpressionToken(
                    episode.expression_token,
                    "teacher_reply",
                    attention_weight=0.85,
                    paradigm_id=episode.expression_pid,
                ),
                ExternalExpressionToken(
                    distractor.expression_token,
                    "perception_other",
                    attention_weight=0.12,
                    paradigm_id=distractor.expression_pid,
                ),
                ExternalExpressionToken(
                    f"noise::{offset % 7}",
                    "perception_other",
                    attention_weight=0.04,
                    paradigm_id=f"p:noise:{offset % 7}",
                ),
            ),
            current_tick=tick,
        )
    state["cooccurrence_associations"] = store.export_state()
    return state, store, labels_by_episode


def _teacher_off_confusion_matrix(
    state: Mapping[str, object],
    store: CooccurrenceAssociationStore,
    *,
    start_tick: int,
) -> dict[str, dict[str, object]]:
    replay_state = dict(state)
    result: dict[str, dict[str, object]] = {}
    expression_tokens = tuple(episode.expression_token for episode in EPISODES)
    for index, episode in enumerate(EPISODES):
        tick = start_tick + index
        replay_state = emit_draft_introspection_feelings(
            replay_state,
            episode.views,
            current_tick=tick,
            paradigm_competition=episode.paradigm_competition,
            recent_punishment_resemblance=episode.recent_punishment_resemblance,
        )
        label = _latest_label(replay_state, tick)
        top_token = store.nearest_by_label((label,), top_k=1, current_tick=tick)[0]
        top_paradigm = store.nearest_paradigms_by_label((label,), top_k=1, current_tick=tick)[0]
        target_score = store.similarity(label, episode.expression_token, tick)
        other_scores = [
            store.similarity(label, token, tick)
            for token in expression_tokens
            if token != episode.expression_token
        ]
        result[episode.episode_id] = {
            "label": label,
            "top_token": top_token,
            "top_paradigm": top_paradigm,
            "target_score": target_score,
            "best_other_score": max(other_scores, default=0.0),
            "observed_external_tokens": (),
        }
    return result


def _stable_labels(labels_by_episode: Mapping[str, list[str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for episode_id, labels in labels_by_episode.items():
        tail = labels[-20:]
        label, count = Counter(tail).most_common(1)[0]
        assert count >= 18
        result[episode_id] = label
    return result


def _active_prototypes(state: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    payload = state.get("introspection_prototype_store", {})
    rows = payload.get("prototypes", []) if isinstance(payload, Mapping) else []
    if not isinstance(rows, list):
        return ()
    return tuple(item for item in rows if isinstance(item, Mapping))


def _latest_label(state: Mapping[str, object], tick: int) -> str:
    rows = state.get("introspection_feelings", [])
    if not isinstance(rows, list):
        raise AssertionError("missing introspection feelings")
    for item in reversed(rows):
        if isinstance(item, Mapping) and int(item.get("tick", -1)) == int(tick):
            return str(item.get("sa_label", ""))
    raise AssertionError(f"missing feeling at tick {tick}")


def _external_recall(confusion: Mapping[str, Mapping[str, object]]) -> dict[str, tuple[object, object]]:
    return {
        episode_id: (row["top_token"], row["top_paradigm"])
        for episode_id, row in sorted(confusion.items())
    }


def _normalized_labels(confusion: Mapping[str, Mapping[str, object]], prefix: str) -> dict[str, str]:
    return {
        episode_id: str(row["label"]).removeprefix(prefix)
        for episode_id, row in sorted(confusion.items())
    }
