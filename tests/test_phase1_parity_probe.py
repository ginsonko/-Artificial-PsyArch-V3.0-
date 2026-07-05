from __future__ import annotations

from pathlib import Path

from apv3test.runtime import ParityProbeCase, SQLiteRuntimeStore, assert_probe_parity, run_parity_probe


def _phase1_state() -> dict:
    return {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {
            "tokens": {
                "你好": {"vector": [0.91, 0.03, 0.02], "support": 6.0},
                "我在": {"vector": [0.88, 0.05, 0.03], "support": 5.5},
                "三顾": {"vector": [0.11, 0.82, 0.04], "support": 4.5},
                "茅庐": {"vector": [0.10, 0.84, 0.03], "support": 4.3},
                "黄色": {"vector": [0.2, 0.1, 0.9], "support": 3.0},
                "苹果": {"vector": [0.25, 0.12, 0.86], "support": 3.0},
            }
        },
        "bn_candidates": [
            {
                "candidate_id": "memory:greeting_pair",
                "domain": "dialogue",
                "probe_features": {
                    "greeting": {
                        "label": 0.92,
                        "display": 0.5,
                        "bigram": 0.4,
                        "focus": 0.7,
                        "state_match": 0.8,
                        "energy": 0.6,
                        "sequence": 0.75,
                        "posting": 0.2,
                        "vector": 0.9,
                        "learned_similarity": 0.8,
                        "learned_vector": 99.0,
                    }
                },
            },
            {
                "candidate_id": "memory:idiom_pair",
                "domain": "language",
                "probe_features": {
                    "idiom_successor": {
                        "label": 0.91,
                        "display": 0.45,
                        "bigram": 0.7,
                        "focus": 0.6,
                        "state_match": 0.7,
                        "energy": 0.55,
                        "sequence": 0.8,
                        "posting": 0.25,
                        "vector": 0.86,
                        "learned_similarity": 0.78,
                    }
                },
            },
            {
                "candidate_id": "memory:math_additive_template",
                "domain": "math",
                "probe_features": {
                    "simple_math": {
                        "label": 0.88,
                        "display": 0.35,
                        "bigram": 0.55,
                        "focus": 0.8,
                        "state_match": 0.83,
                        "energy": 0.62,
                        "sequence": 0.77,
                        "posting": 0.3,
                        "vector": 0.74,
                        "numeric": 0.6,
                        "relation": 0.65,
                        "learned_similarity": 0.7,
                    }
                },
            },
            {
                "candidate_id": "memory:yellow_apple_generalization",
                "domain": "multimodal",
                "probe_features": {
                    "yellow_apple": {
                        "label": 0.82,
                        "display": 0.6,
                        "bigram": 0.4,
                        "focus": 0.85,
                        "state_match": 0.74,
                        "energy": 0.72,
                        "sequence": 0.3,
                        "posting": 0.25,
                        "vector": 0.8,
                        "learned_similarity": 0.75,
                    }
                },
            },
            {
                "candidate_id": "memory:interruption_recovery",
                "domain": "attention",
                "probe_features": {
                    "interruption_recovery": {
                        "label": 0.76,
                        "display": 0.3,
                        "bigram": 0.2,
                        "focus": 0.9,
                        "state_match": 0.86,
                        "energy": 0.8,
                        "sequence": 0.68,
                        "posting": 0.15,
                        "vector": 0.55,
                        "learned_similarity": 0.72,
                    }
                },
            },
        ],
        "transitions": [
            {"source": "你好", "target": "我在", "support": 6.0},
            {"source": "三顾", "target": "茅庐", "support": 5.0},
            {"source": "simple_math_template", "target": "write_step_then_compute", "support": 4.0},
            {"source": "yellow+apple", "target": "compose_color_object", "support": 3.5},
            {"source": "task_interrupted", "target": "hold_pressure_then_resume", "support": 3.8},
        ],
        "paradigms": [
            {"pid": "p:greeting_successor", "support": 6.0, "conf": 0.86, "slot_types": ["cue", "reply"], "probe_tags": ["greeting"]},
            {"pid": "p:idiom_successor", "support": 5.0, "conf": 0.82, "slot_types": ["prefix", "suffix"], "probe_tags": ["idiom_successor"]},
            {"pid": "p:math_step_template", "support": 4.0, "conf": 0.79, "slot_types": ["operand", "operator", "result"], "probe_tags": ["simple_math"]},
            {"pid": "p:color_object", "support": 3.7, "conf": 0.78, "slot_types": ["color", "object"], "probe_tags": ["yellow_apple"]},
            {"pid": "p:interrupt_resume", "support": 3.4, "conf": 0.76, "slot_types": ["task", "break", "resume"], "probe_tags": ["interruption_recovery"]},
        ],
        "action_outcomes": {
            "type_char": {"drive_bias": 0.34, "reward_support": 7.0, "punish_support": 0.2},
            "focus_task_pressure": {"drive_bias": 0.42, "reward_support": 3.0, "punish_support": 0.1},
            "compose_slots": {"drive_bias": 0.38, "reward_support": 4.0, "punish_support": 0.1},
        },
        "percept_prototypes": [
            {"prototype_id": "visual:yellow_apple", "support": 2.5, "features": {"color": "yellow", "object": "apple"}, "probe_tags": ["yellow_apple"]},
        ],
    }


def _cases() -> list[ParityProbeCase]:
    return [
        ParityProbeCase("greeting", "你好", "type_char", ("你好", "我在"), "memory:greeting_pair", "我在", "p:greeting_successor"),
        ParityProbeCase("idiom_successor", "三顾", "type_char", ("三顾", "茅庐"), "memory:idiom_pair", "茅庐", "p:idiom_successor"),
        ParityProbeCase("simple_math", "simple_math_template", "type_char", (), "memory:math_additive_template", "write_step_then_compute", "p:math_step_template"),
        ParityProbeCase("yellow_apple", "yellow+apple", "compose_slots", ("黄色", "苹果"), "memory:yellow_apple_generalization", "compose_color_object", "p:color_object"),
        ParityProbeCase("interruption_recovery", "task_interrupted", "focus_task_pressure", (), "memory:interruption_recovery", "hold_pressure_then_resume", "p:interrupt_resume"),
    ]


def test_phase1_probe_matches_expected_anchors_in_memory_state() -> None:
    results = run_parity_probe(_phase1_state(), _cases())

    for case, result in zip(_cases(), results):
        assert result.bn_top[0]["candidate_id"] == case.expected_top_bn
        assert result.cn_successors[0]["target"] == case.expected_successor
        assert result.paradigms[0]["pid"] == case.expected_paradigm
        assert result.action_outcome["drive_bias"] > 0.0


def test_phase1_memory_state_matches_sqlite_rehydrated_state(tmp_path: Path) -> None:
    state = _phase1_state()
    cases = _cases()
    memory_results = run_parity_probe(state, cases)
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")

    state_id = store.save_state(state)
    restored = store.load_state(state_id)
    restored_results = run_parity_probe(restored, cases)

    assert restored == state
    assert_probe_parity(memory_results, restored_results)


def test_phase1_projection_counts_cover_all_probe_domains(tmp_path: Path) -> None:
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")

    state_id = store.save_state(_phase1_state())
    counts = store.ontology_counts(state_id)

    assert counts["online_embedding_tokens"] == 6
    assert counts["explicit_transitions"] == 5
    assert counts["paradigm_sa"] == 5
    assert counts["action_outcomes"] == 3
    assert counts["percept_prototypes"] == 1


def test_phase1_sqlite_projection_preserves_probe_payloads(tmp_path: Path) -> None:
    store = SQLiteRuntimeStore(tmp_path / "runtime.sqlite")

    state_id = store.save_state(_phase1_state())
    projection = store.load_ontology_projection(state_id)

    token_map = {row["token"]: row for row in projection["online_embedding_tokens"]}
    transition_targets = {(row["source"], row["target"]) for row in projection["explicit_transitions"]}
    paradigm_ids = {row["pid"] for row in projection["paradigm_sa"]}

    assert token_map["你好"]["support"] == 6.0
    assert ("三顾", "茅庐") in transition_targets
    assert "p:color_object" in paradigm_ids
    assert projection["action_outcomes"]["focus_task_pressure"]["drive_bias"] == 0.42
    assert projection["percept_prototypes"][0]["features"] == {"color": "yellow", "object": "apple"}
