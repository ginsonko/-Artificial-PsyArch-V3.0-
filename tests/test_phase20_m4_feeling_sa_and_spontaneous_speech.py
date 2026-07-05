"""M4 感受SA回灌 + 自发外显行为测试."""
from __future__ import annotations
from pathlib import Path
from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn


def test_high_surprise_writes_feeling_sa_to_pool(tmp_path: Path) -> None:
    db = tmp_path / "m4a.sqlite"; sid = "m4a"
    r = run_phase20_7_turn(user_text="骤然异变量子坍缩!", session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    sas = set()
    for e in r.tick_trace:
        for i in (e.state_pool_top or []):
            if str(i.get("sa_id", "")).startswith("feeling::"):
                sas.add(str(i.get("sa_id")))
    assert len(sas) > 0, "state_pool_top应含feeling::SA"


def test_feeling_sa_written_recorded_in_feelings(tmp_path: Path) -> None:
    db = tmp_path / "m4b.sqlite"; sid = "m4b"
    r = run_phase20_7_turn(user_text="这是什么量子现象", session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    found = False
    for tick in r.tick_trace:
        fs = tick.feelings if isinstance(tick.feelings, dict) else {}
        if "feeling_sa_written" in fs:
            found = True
            break
    assert found, "tick feelings应含feeling_sa_written"


def test_accumulated_unclosed_tension_triggers_spontaneous_speech(tmp_path: Path) -> None:
    db = tmp_path / "m4c.sqlite"; sid = "m4c"
    run_phase20_7_turn(user_text="明天吃什么好呢", session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    run_phase20_7_turn(user_text="明天吃什么好呢", teacher_feedback=TeacherFeedback(feedback_text="我还在想这个问题", reward_mag=1.0),
                       session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    for _ in range(3):
        run_phase20_7_turn(user_text="周末去哪玩好呢", session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    r = run_phase20_7_turn(user_text="", session_id=sid, db_path=db, max_ticks=8, runtime_stage="stage6")
    assert r.reply_text, "张力累积后idle应自发说话"


def test_no_tension_idle_stays_silent(tmp_path: Path) -> None:
    db = tmp_path / "m4d.sqlite"; sid = "m4d"
    run_phase20_7_turn(user_text="你好", teacher_feedback=TeacherFeedback(feedback_text="你好呀", reward_mag=1.0),
                       session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    run_phase20_7_turn(user_text="你好", session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    for _ in range(4):
        r = run_phase20_7_turn(user_text="", session_id=sid, db_path=db, max_ticks=8, runtime_stage="stage6")
        assert not r.reply_text, "无张力时idle应保持沉默"