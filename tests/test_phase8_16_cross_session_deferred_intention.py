from __future__ import annotations

from pathlib import Path

from runtime.cognitive.long_term.deferred_intention import DeferredIntentionMemory


def test_cross_session_deferred_intention_recalls_action_from_cue(tmp_path: Path) -> None:
    db_path = tmp_path / "deferred.sqlite"
    session_1 = DeferredIntentionMemory()
    session_1.learn_intention(
        action_id="ACTION_REROUTE_001",
        cue_sa_ids=("vision::shape::construction", "vision::x_bucket::left"),
        support=0.9,
        created_tick=4,
    )
    session_1.save_sqlite(db_path)

    session_2 = DeferredIntentionMemory.load_sqlite(db_path)
    recalled = session_2.recall_for_cues(("vision::shape::construction",))

    assert recalled
    assert recalled[0].action_id == "ACTION_REROUTE_001"


def test_deferred_intention_no_match_does_not_emit_action(tmp_path: Path) -> None:
    db_path = tmp_path / "deferred.sqlite"
    memory = DeferredIntentionMemory()
    memory.learn_intention(
        action_id="ACTION_REROUTE_001",
        cue_sa_ids=("vision::shape::construction",),
    )
    memory.save_sqlite(db_path)

    loaded = DeferredIntentionMemory.load_sqlite(db_path)

    assert loaded.recall_for_cues(("vision::shape::flower",)) == ()
