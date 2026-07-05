from __future__ import annotations

from pathlib import Path

import pytest

from apv3test.runtime import (
    DraftActionRunner,
    DraftTextAction,
    LearningEpisodeWriter,
    SQLiteRuntimeStore,
)


def _blank_state() -> dict:
    return {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {"tokens": {}},
        "transitions": [],
        "paradigms": [],
        "bn_candidates": [],
        "action_outcomes": {},
        "percept_prototypes": [],
    }


def test_draft_type_reread_modify_commit_clears_buffer() -> None:
    runner = DraftActionRunner()
    state = _blank_state()

    state = runner.apply(state, DraftTextAction(tick=1, kind="type_text", text="我在"))
    state = runner.apply(state, DraftTextAction(tick=2, kind="reread"))
    state = runner.apply(state, DraftTextAction(tick=3, kind="replace_tail", old_text="在", new_text="在。"))
    state = runner.apply(state, DraftTextAction(tick=4, kind="commit"))

    runtime = state["draft_runtime"]
    assert runtime["readbacks"][-1]["text"] == "我在"
    assert runtime["commits"][-1]["text"] == "我在。"
    assert runtime["buffer"] == ""
    assert runtime["cursor"] == 0


def test_same_actuator_can_only_take_one_action_per_tick() -> None:
    runner = DraftActionRunner()
    state = runner.apply(_blank_state(), DraftTextAction(tick=1, kind="type_text", text="早"))

    with pytest.raises(ValueError, match="same actuator"):
        runner.apply(state, DraftTextAction(tick=1, kind="type_text", text="安"))


def test_uncommitted_draft_does_not_create_positive_learning_episode() -> None:
    runner = DraftActionRunner()
    state = runner.apply(_blank_state(), DraftTextAction(tick=1, kind="type_text", text="半成品"))

    episode = runner.learning_episode_from_latest_commit(state, episode_id="draft:uncommitted")

    assert episode is None
    assert state["action_outcomes"] == {}


def test_committed_draft_creates_action_outcome_only_after_commit() -> None:
    runner = DraftActionRunner()
    state = _blank_state()
    state = runner.apply(state, DraftTextAction(tick=1, kind="type_text", text="早安，我在。"))
    before_commit = runner.learning_episode_from_latest_commit(state, episode_id="draft:before_commit")
    state = runner.apply(state, DraftTextAction(tick=2, kind="commit"))
    after_commit = runner.learning_episode_from_latest_commit(state, episode_id="draft:after_commit")

    assert before_commit is None
    assert after_commit is not None
    learned_state = LearningEpisodeWriter().apply(state, after_commit)
    assert learned_state["action_outcomes"]["text_commit"]["reward_support"] == 1.0
    assert learned_state["online_embedding"]["tokens"] == {}
    assert learned_state["transitions"] == []


def test_draft_runtime_survives_sqlite_restore_and_commit_state(tmp_path: Path) -> None:
    runner = DraftActionRunner()
    state = _blank_state()
    state = runner.apply(state, DraftTextAction(tick=1, kind="type_text", text="我"))
    state = runner.apply(state, DraftTextAction(tick=2, kind="type_text", text="在"))
    state = runner.apply(state, DraftTextAction(tick=3, kind="delete_chars", count=1))
    state = runner.apply(state, DraftTextAction(tick=4, kind="type_text", text="在。"))
    state = runner.apply(state, DraftTextAction(tick=5, kind="commit"))
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")

    state_id = store.save_state(state)
    restored = store.load_state(state_id)

    assert restored == state
    assert restored["draft_runtime"]["commits"][-1]["text"] == "我在。"
    assert restored["draft_runtime"]["buffer"] == ""


def test_committed_action_outcome_reaches_sqlite_projection(tmp_path: Path) -> None:
    runner = DraftActionRunner()
    state = _blank_state()
    state = runner.apply(state, DraftTextAction(tick=1, kind="type_text", text="我在。"))
    state = runner.apply(state, DraftTextAction(tick=2, kind="commit"))
    episode = runner.learning_episode_from_latest_commit(state, episode_id="draft:commit_reward")
    assert episode is not None
    learned_state = LearningEpisodeWriter().apply(state, episode)
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")

    state_id = store.save_state(learned_state)
    projection = store.load_ontology_projection(state_id)

    assert projection["action_outcomes"]["text_commit"]["reward_support"] == 1.0
    assert projection["online_embedding_tokens"] == []
    assert projection["explicit_transitions"] == []


def test_uncommitted_draft_restore_still_has_no_positive_projection(tmp_path: Path) -> None:
    runner = DraftActionRunner()
    state = runner.apply(_blank_state(), DraftTextAction(tick=1, kind="type_text", text="未完成草稿"))
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")

    state_id = store.save_state(state)
    restored = store.load_state(state_id)
    projection = store.load_ontology_projection(state_id)

    assert restored["draft_runtime"]["buffer"] == "未完成草稿"
    assert restored["draft_runtime"]["commits"] == []
    assert projection["action_outcomes"] == {}
    assert projection["online_embedding_tokens"] == []
    assert projection["explicit_transitions"] == []
