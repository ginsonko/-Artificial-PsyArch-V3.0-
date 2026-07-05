from __future__ import annotations

from pathlib import Path

from apv3test.runtime import (
    LearnedActionOutcome,
    LearnedBnCandidate,
    LearnedParadigm,
    LearnedPerceptPrototype,
    LearnedToken,
    LearnedTransition,
    LearningEpisode,
    LearningEpisodeWriter,
    ParityProbeCase,
    SQLiteRuntimeStore,
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


def _morning_episode() -> LearningEpisode:
    return LearningEpisode(
        episode_id="teach:morning_greeting:v1",
        tokens=(
            LearnedToken("早安", (0.72, 0.18, 0.03), 3.0),
            LearnedToken("早安，我在。", (0.70, 0.20, 0.04), 2.5),
        ),
        transitions=(LearnedTransition("早安", "早安，我在。", 3.0),),
        paradigms=(
            LearnedParadigm(
                "p:morning_greeting_successor",
                support_delta=3.0,
                conf=0.74,
                slot_types=("cue", "reply"),
                probe_tags=("morning_greeting",),
            ),
        ),
        bn_candidates=(
            LearnedBnCandidate(
                "memory:morning_greeting_pair",
                "dialogue",
                {
                    "morning_greeting": {
                        "label": 0.86,
                        "display": 0.45,
                        "bigram": 0.34,
                        "focus": 0.62,
                        "state_match": 0.7,
                        "energy": 0.54,
                        "sequence": 0.66,
                        "posting": 0.18,
                        "vector": 0.76,
                        "learned_similarity": 0.7,
                        "learned_vector": 100.0,
                    }
                },
            ),
        ),
        action_outcomes=(LearnedActionOutcome("type_char", drive_bias_delta=0.21, reward_delta=2.0),),
        percept_prototypes=(
            LearnedPerceptPrototype(
                "audio:morning_tone",
                support_delta=1.0,
                features={"tone": "soft", "time_feeling": "morning"},
                probe_tags=("morning_greeting",),
            ),
        ),
    )


def _morning_case() -> ParityProbeCase:
    return ParityProbeCase(
        "morning_greeting",
        "早安",
        "type_char",
        ("早安", "早安，我在。"),
        "memory:morning_greeting_pair",
        "早安，我在。",
        "p:morning_greeting_successor",
    )


def test_learning_episode_writes_recallable_ap_native_evidence() -> None:
    state = LearningEpisodeWriter().apply(_blank_state(), _morning_episode())

    result = run_parity_probe(state, [_morning_case()])[0]

    assert result.bn_top[0]["candidate_id"] == "memory:morning_greeting_pair"
    assert result.bn_top[0]["trace_only"]["learned_vector"] == 100.0
    assert result.cn_successors[0]["target"] == "早安，我在。"
    assert result.learned_tokens[0]["support"] == 3.0
    assert result.paradigms[0]["pid"] == "p:morning_greeting_successor"
    assert result.action_outcome["reward_support"] == 2.0
    assert result.percept_prototypes[0]["prototype_id"] == "audio:morning_tone"


def test_learning_write_survives_sqlite_restore_and_recall(tmp_path: Path) -> None:
    writer = LearningEpisodeWriter()
    learned_state = writer.apply(_blank_state(), _morning_episode())
    cases = [_morning_case()]
    memory_results = run_parity_probe(learned_state, cases)
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")

    state_id = store.save_state(learned_state)
    restored_state = store.load_state(state_id)
    restored_results = run_parity_probe(restored_state, cases)

    assert restored_state == learned_state
    assert_probe_parity(memory_results, restored_results)


def test_learning_episode_merges_support_without_duplicate_edges() -> None:
    writer = LearningEpisodeWriter()

    once = writer.apply(_blank_state(), _morning_episode())
    twice = writer.apply(once, _morning_episode())

    transitions = [
        item
        for item in twice["transitions"]
        if item["source"] == "早安" and item["target"] == "早安，我在。"
    ]
    assert len(transitions) == 1
    assert transitions[0]["support"] == 6.0
    assert twice["online_embedding"]["tokens"]["早安"]["support"] == 6.0
    assert twice["action_outcomes"]["type_char"]["reward_support"] == 4.0


def test_learning_write_reaches_sqlite_projection_tables(tmp_path: Path) -> None:
    learned_state = LearningEpisodeWriter().apply(_blank_state(), _morning_episode())
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")

    state_id = store.save_state(learned_state)
    projection = store.load_ontology_projection(state_id)
    token_map = {row["token"]: row for row in projection["online_embedding_tokens"]}
    transition_pairs = {(row["source"], row["target"]) for row in projection["explicit_transitions"]}
    paradigm_ids = {row["pid"] for row in projection["paradigm_sa"]}

    assert token_map["早安"]["support"] == 3.0
    assert ("早安", "早安，我在。") in transition_pairs
    assert "p:morning_greeting_successor" in paradigm_ids
    assert projection["action_outcomes"]["type_char"]["reward_support"] == 2.0
    assert projection["percept_prototypes"][0]["prototype_id"] == "audio:morning_tone"
