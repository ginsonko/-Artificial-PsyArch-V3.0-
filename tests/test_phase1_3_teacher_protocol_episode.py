from __future__ import annotations

from pathlib import Path

from apv3test.runtime import (
    DraftTextAction,
    LearnedBnCandidate,
    LearnedParadigm,
    LearnedToken,
    LearnedTransition,
    LearningEpisode,
    ParityProbeCase,
    SQLiteRuntimeStore,
    TeacherProtocolEpisode,
    TeacherProtocolRunner,
    assert_probe_parity,
    run_parity_probe,
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


def _episode() -> TeacherProtocolEpisode:
    learning = LearningEpisode(
        episode_id="teach:spring_reply:v1",
        tokens=(
            LearnedToken("春天", (0.31, 0.64, 0.18), 2.0),
            LearnedToken("春天来了。", (0.33, 0.66, 0.2), 1.8),
        ),
        transitions=(LearnedTransition("春天", "春天来了。", 2.0),),
        paradigms=(
            LearnedParadigm(
                "p:spring_reply",
                support_delta=2.0,
                conf=0.72,
                slot_types=("cue", "reply"),
                probe_tags=("spring_reply",),
            ),
        ),
        bn_candidates=(
            LearnedBnCandidate(
                "memory:spring_reply_pair",
                "dialogue",
                {
                    "spring_reply": {
                        "label": 0.84,
                        "display": 0.42,
                        "bigram": 0.3,
                        "focus": 0.66,
                        "state_match": 0.68,
                        "energy": 0.5,
                        "sequence": 0.62,
                        "posting": 0.14,
                        "vector": 0.73,
                        "learned_similarity": 0.69,
                        "learned_vector": 77.0,
                    }
                },
            ),
        ),
    )
    return TeacherProtocolEpisode(
        episode_id="teacher_protocol:spring_reply:v1",
        learning_episode=learning,
        draft_actions=(
            DraftTextAction(tick=1, kind="type_text", text="春天来"),
            DraftTextAction(tick=2, kind="type_text", text="了"),
            DraftTextAction(tick=3, kind="reread"),
            DraftTextAction(tick=4, kind="replace_tail", old_text="了", new_text="了。"),
            DraftTextAction(tick=5, kind="commit"),
        ),
        probe_cases=(
            ParityProbeCase(
                "spring_reply",
                "春天",
                "text_commit",
                ("春天", "春天来了。"),
                "memory:spring_reply_pair",
                "春天来了。",
                "p:spring_reply",
            ),
        ),
        commit_episode_id="commit:spring_reply:v1",
    )


def test_teacher_protocol_runs_learning_draft_commit_and_recall() -> None:
    result = TeacherProtocolRunner().run(_blank_state(), _episode())
    runtime = result.state["draft_runtime"]
    probe = result.probe_results[0]

    assert runtime["readbacks"][-1]["text"] == "春天来了"
    assert runtime["commits"][-1]["text"] == "春天来了。"
    assert runtime["buffer"] == ""
    assert probe.bn_top[0]["candidate_id"] == "memory:spring_reply_pair"
    assert probe.bn_top[0]["trace_only"]["learned_vector"] == 77.0
    assert probe.cn_successors[0]["target"] == "春天来了。"
    assert probe.paradigms[0]["pid"] == "p:spring_reply"
    assert probe.action_outcome["reward_support"] == 1.0


def test_teacher_protocol_survives_sqlite_restore_and_recall(tmp_path: Path) -> None:
    protocol = _episode()
    result = TeacherProtocolRunner().run(_blank_state(), protocol)
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")

    state_id = store.save_state(result.state)
    restored = store.load_state(state_id)
    restored_probe = run_parity_probe(restored, protocol.probe_cases)

    assert restored == result.state
    assert_probe_parity(result.probe_results, restored_probe)


def test_teacher_protocol_projection_contains_only_committed_learning_boundary(tmp_path: Path) -> None:
    result = TeacherProtocolRunner().run(_blank_state(), _episode())
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")

    state_id = store.save_state(result.state)
    projection = store.load_ontology_projection(state_id)
    token_map = {row["token"]: row for row in projection["online_embedding_tokens"]}
    transition_pairs = {(row["source"], row["target"]) for row in projection["explicit_transitions"]}

    assert "春天来了" not in token_map
    assert "春天来了。" in token_map
    assert ("春天", "春天来了。") in transition_pairs
    assert projection["action_outcomes"]["text_commit"]["reward_support"] == 1.0
    assert result.state["draft_runtime"]["buffer"] == ""


def test_teacher_protocol_without_commit_does_not_write_commit_outcome() -> None:
    protocol = _episode()
    no_commit = TeacherProtocolEpisode(
        episode_id="teacher_protocol:spring_reply:uncommitted",
        learning_episode=protocol.learning_episode,
        draft_actions=protocol.draft_actions[:-1],
        probe_cases=protocol.probe_cases,
        commit_episode_id="commit:spring_reply:missing",
    )

    result = TeacherProtocolRunner().run(_blank_state(), no_commit)

    assert result.state["draft_runtime"]["buffer"] == "春天来了。"
    assert result.state["draft_runtime"]["commits"] == []
    assert "text_commit" not in result.state["action_outcomes"]
