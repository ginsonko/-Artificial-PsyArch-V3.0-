"""M2 统一召回竞争行为测试."""
from __future__ import annotations
from pathlib import Path
from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


def _turn(db, sid, text="", feedback=None):
    return run_phase20_7_turn(user_text=text, teacher_feedback=feedback, session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")


def test_exact_high_support_takes_fast_path(tmp_path: Path) -> None:
    db = tmp_path / "m2a.sqlite"; sid = "m2a"
    _turn(db, sid, "你好", feedback=TeacherFeedback(feedback_text="你好呀", reward_mag=1.0))
    r = _turn(db, sid, "你好")
    assert r.reply_text == "你好呀"
    assert any(b.get("kind") == "exact_b0" for t in r.tick_trace for b in t.b_candidates if isinstance(b, dict))


def test_subsequence_generalization_still_wins_when_rewarded(tmp_path: Path) -> None:
    db = tmp_path / "m2b.sqlite"; sid = "m2b"
    _turn(db, sid, "没错,你好聪明", feedback=TeacherFeedback(feedback_text="谢谢", reward_mag=1.0))
    r = _turn(db, sid, "你好聪明")
    assert r.reply_text == "谢谢"


def test_punished_exact_does_not_become_answer(tmp_path: Path) -> None:
    """教过的exact被punish后,该input的回复不应是punish文本(红线P0-1+M2竞争)."""
    db = tmp_path / "m2c.sqlite"; sid = "m2c"
    _turn(db, sid, "你好棒", feedback=TeacherFeedback(feedback_text="好的", reward_mag=1.0))
    _turn(db, sid, "你好棒", feedback=TeacherFeedback(feedback_text="不行", punish_mag=1.0))
    r = _turn(db, sid, "你好棒")
    assert r.reply_text != "不行"