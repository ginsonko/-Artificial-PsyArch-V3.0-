from __future__ import annotations

import sqlite3

from apv3test.config.introspection_config import APV3CooccurrenceConfig
from apv3test.runtime import (
    CooccurrenceAssociationStore,
    ExternalExpressionToken,
    observe_feeling_expression_cooccurrence,
)


FEELING_A = "feeling::draft::proto_1"
FEELING_B = "feeling::draft::proto_2"
TARGET = "expr::target"
DISTRACTOR = "expr::distractor"
UNTRAINED = "expr::untrained"
PARADIGM_A = "p:expr:target"


def test_phase7_3c_cooccurrence_learning_relative_increment_and_nearest() -> None:
    cfg = APV3CooccurrenceConfig(test_learning_delta_min=0.05)
    store = CooccurrenceAssociationStore(cfg)
    before = store.similarity(FEELING_A, TARGET, 0)

    for tick in range(1, 11):
        observe_feeling_expression_cooccurrence(
            store,
            (FEELING_A,),
            (ExternalExpressionToken(TARGET, "teacher_reply", attention_weight=0.8),),
            current_tick=tick,
            config=cfg,
        )

    after = store.similarity(FEELING_A, TARGET, 11)
    assert after - before > cfg.test_learning_delta_min
    assert store.nearest_by_label((FEELING_A,), top_k=3, current_tick=11)[0] == TARGET
    assert store.similarity(FEELING_A, UNTRAINED, 11) == 0.0


def test_phase7_3c_self_emission_does_not_inflate_association() -> None:
    cfg = APV3CooccurrenceConfig(gamma_self_emission=0.0)
    store = CooccurrenceAssociationStore(cfg)
    observe_feeling_expression_cooccurrence(
        store,
        (FEELING_A,),
        (ExternalExpressionToken(TARGET, "teacher_reply"),),
        current_tick=1,
        config=cfg,
    )
    before = store.similarity(FEELING_A, TARGET, 2)
    for tick in range(3, 20):
        observe_feeling_expression_cooccurrence(
            store,
            (FEELING_A,),
            (ExternalExpressionToken(TARGET, "self_emission"),),
            current_tick=tick,
            config=cfg,
        )

    assert store.similarity(FEELING_A, TARGET, 20) <= before


def test_phase7_3c_target_beats_distractor_by_temporal_regular_cooccurrence() -> None:
    cfg = APV3CooccurrenceConfig(test_target_distractor_ratio_min=1.5)
    store = CooccurrenceAssociationStore(cfg)
    for tick in range(1, 61):
        observe_feeling_expression_cooccurrence(
            store,
            (FEELING_A,),
            (ExternalExpressionToken(TARGET, "perception_other", attention_weight=0.5),),
            current_tick=tick,
            config=cfg,
        )
        distractor_feeling = FEELING_A if tick % 4 == 0 else FEELING_B
        observe_feeling_expression_cooccurrence(
            store,
            (distractor_feeling,),
            (ExternalExpressionToken(DISTRACTOR, "perception_other", attention_weight=0.5),),
            current_tick=tick,
            config=cfg,
        )

    target_score = store.similarity(FEELING_A, TARGET, 61)
    distractor_score = store.similarity(FEELING_A, DISTRACTOR, 61)
    assert target_score > distractor_score * cfg.test_target_distractor_ratio_min
    assert store.nearest_by_label((FEELING_A,), top_k=1, current_tick=61) == (TARGET,)


def test_phase7_3c_paradigm_aggregation_does_not_need_find_by_cue_token() -> None:
    store = CooccurrenceAssociationStore()
    for tick in range(1, 6):
        observe_feeling_expression_cooccurrence(
            store,
            (FEELING_A,),
            (ExternalExpressionToken(TARGET, "teacher_reply", paradigm_id=PARADIGM_A),),
            current_tick=tick,
        )

    assert store.nearest_paradigms_by_label((FEELING_A,), top_k=3, current_tick=6) == (PARADIGM_A,)
    assert store.similarity_paradigm(FEELING_A, PARADIGM_A, 6) > 0.0


def test_phase7_3c_sqlite_warmload_parity_for_tokens_and_paradigms() -> None:
    cfg = APV3CooccurrenceConfig(half_life_decay=0.99, eviction_floor=1e-9)
    store = CooccurrenceAssociationStore(cfg)
    store.observe(FEELING_A, "expr::a", weight=0.7, current_tick=10, paradigm_id="p:a")
    store.observe(FEELING_A, "expr::b", weight=0.3, current_tick=20, paradigm_id="p:b")
    store.observe(FEELING_B, "expr::a", weight=0.5, current_tick=15, paradigm_id="p:a")
    query_tick = 100
    sims_before = {
        (FEELING_A, "expr::a"): store.similarity(FEELING_A, "expr::a", query_tick),
        (FEELING_A, "expr::b"): store.similarity(FEELING_A, "expr::b", query_tick),
        (FEELING_B, "expr::a"): store.similarity(FEELING_B, "expr::a", query_tick),
    }
    paradigms_before = store.nearest_paradigms_by_label((FEELING_A,), top_k=5, current_tick=query_tick)
    fanout_before = store.nearest_by_label((FEELING_A,), top_k=5, current_tick=query_tick)

    conn = sqlite3.connect(":memory:")
    store.export_to_sqlite(conn)
    reloaded = CooccurrenceAssociationStore(cfg)
    reloaded.import_from_sqlite(conn, current_tick=query_tick)

    for (left, right), expected in sims_before.items():
        assert abs(reloaded.similarity(left, right, query_tick) - expected) < 1e-9
    assert reloaded.nearest_by_label((FEELING_A,), top_k=5, current_tick=query_tick) == fanout_before
    assert reloaded.nearest_paradigms_by_label((FEELING_A,), top_k=5, current_tick=query_tick) == paradigms_before


def test_phase7_3c_import_is_idempotent_and_does_not_reanchor_tick() -> None:
    cfg = APV3CooccurrenceConfig(half_life_decay=0.5, eviction_floor=1e-9)
    store = CooccurrenceAssociationStore(cfg)
    store.observe(FEELING_A, TARGET, weight=1.0, current_tick=1)
    conn = sqlite3.connect(":memory:")
    store.export_to_sqlite(conn)
    at_5 = CooccurrenceAssociationStore(cfg)
    at_5.import_from_sqlite(conn, current_tick=5)
    again_at_5 = CooccurrenceAssociationStore(cfg)
    again_at_5.import_from_sqlite(conn, current_tick=5)

    assert at_5.snapshot() == again_at_5.snapshot()
    assert at_5.pairs[0].last_update_tick == 1
    assert abs(at_5.similarity(FEELING_A, TARGET, 5) - 0.0625) < 1e-9


def test_phase7_3c_import_drops_subfloor_rows_and_compact_eviction() -> None:
    cfg = APV3CooccurrenceConfig(half_life_decay=0.1, eviction_floor=0.02)
    store = CooccurrenceAssociationStore(cfg)
    store.observe(FEELING_A, TARGET, weight=1.0, current_tick=1, paradigm_id=PARADIGM_A)
    conn = sqlite3.connect(":memory:")
    store.export_to_sqlite(conn)

    reloaded = CooccurrenceAssociationStore(cfg)
    reloaded.import_from_sqlite(conn, current_tick=4)
    assert reloaded.pairs == ()
    assert reloaded.paradigm_pairs == ()

    store.compact(current_tick=4)
    assert store.pairs == ()
    assert store.paradigm_pairs == ()


def test_phase7_3c_retire_label_removes_token_and_paradigm_associations() -> None:
    store = CooccurrenceAssociationStore()
    store.observe(FEELING_A, TARGET, weight=1.0, current_tick=1, paradigm_id=PARADIGM_A)
    store.observe(FEELING_B, TARGET, weight=1.0, current_tick=1, paradigm_id=PARADIGM_A)

    store.retire_label(FEELING_A, current_tick=2)

    assert store.similarity(FEELING_A, TARGET, 2) == 0.0
    assert store.similarity_paradigm(FEELING_A, PARADIGM_A, 2) == 0.0
    assert store.similarity(FEELING_B, TARGET, 2) > 0.0
    assert store.nearest_paradigms_by_label((FEELING_B,), top_k=3, current_tick=2) == (PARADIGM_A,)

