"""Fable5 P0-P1 行为探针固化为 pytest — 断言行为非字段形状."""
from __future__ import annotations
from pathlib import Path
from apv3test.runtime.phase20_7 import MediaInput, TeacherFeedback, run_phase20_7_turn


def _turn(db, sid, text="", media=(), feedback=None):
    return run_phase20_7_turn(user_text=text, media_inputs=media, teacher_feedback=feedback,
                              session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")


def test_teach_recall_exact(tmp_path: Path) -> None:
    db = tmp_path / "t1.sqlite"; sid = "t1"
    _turn(db, sid, "你好", feedback=TeacherFeedback(feedback_text="你好呀", reward_mag=1.0))
    r = _turn(db, sid, "你好")
    assert r.reply_text == "你好呀"


def test_subsequence_generalization_preserved(tmp_path: Path) -> None:
    db = tmp_path / "t2.sqlite"; sid = "t2"
    _turn(db, sid, "没错,你好聪明", feedback=TeacherFeedback(feedback_text="谢谢", reward_mag=1.0))
    r = _turn(db, sid, "你好聪明")
    assert r.reply_text == "谢谢"


def test_punish_text_never_becomes_answer(tmp_path: Path) -> None:
    db = tmp_path / "t3.sqlite"; sid = "t3"
    _turn(db, sid, "你真棒", feedback=TeacherFeedback(feedback_text="谢谢你", reward_mag=1.0))
    _turn(db, sid, "真棒")
    _turn(db, sid, "你真棒", feedback=TeacherFeedback(feedback_text="不对", punish_mag=1.0))
    r = _turn(db, sid, "真棒")
    assert r.reply_text != "不对"


def test_math_recall(tmp_path: Path) -> None:
    db = tmp_path / "t4.sqlite"; sid = "t4"
    _turn(db, sid, "3+7=?", feedback=TeacherFeedback(feedback_text="10", reward_mag=1.0))
    r = _turn(db, sid, "3+7=?")
    assert r.reply_text == "10"


def test_math_subsequence_trap_13_plus_7(tmp_path: Path) -> None:
    db = tmp_path / "t5.sqlite"; sid = "t5"
    _turn(db, sid, "3+7=?", feedback=TeacherFeedback(feedback_text="10", reward_mag=1.0))
    _turn(db, sid, "2+5=?", feedback=TeacherFeedback(feedback_text="7", reward_mag=1.0))
    r = _turn(db, sid, "13+7=?")
    assert r.reply_text != "10"


def test_unknown_input_honest(tmp_path: Path) -> None:
    db = tmp_path / "t6.sqlite"; sid = "t6"
    r = _turn(db, sid, "量子引力是什么")
    assert "不太会" in r.reply_text


def test_visual_backref_resolves_to_latest_image(tmp_path: Path) -> None:
    import os
    apple = "data/phase20_workbench_media/真实苹果2_2bf246de034bf5c4.jpg"
    banana = "data/phase20_workbench_media/真实香蕉4_c2888e348a25d03b.webp"
    if not os.path.exists(apple) or not os.path.exists(banana):
        return  # 资产缺失时跳过
    db = tmp_path / "t7.sqlite"; sid = "t7"
    # P1-4: 视觉回指=学得的指代. 需先教"刚刚图片是啥"这个问法与视觉答案共现绑定.
    _turn(db, sid, "这是什么", (MediaInput(media_type="image", path=apple),),
          feedback=TeacherFeedback(feedback_text="是苹果", reward_mag=1.0))
    _turn(db, sid, "这是什么", (MediaInput(media_type="image", path=apple),))
    # 教"刚刚图片是啥"→"是苹果"(共现绑定视觉指代)
    _turn(db, sid, "刚刚图片是啥", (MediaInput(media_type="image", path=apple),),
          feedback=TeacherFeedback(feedback_text="是苹果", reward_mag=1.0))
    _turn(db, sid, "刚刚图片是啥", (MediaInput(media_type="image", path=apple),))
    # 看香蕉
    _turn(db, sid, "这是什么", (MediaInput(media_type="image", path=banana),),
          feedback=TeacherFeedback(feedback_text="是香蕉", reward_mag=1.0))
    _turn(db, sid, "刚刚图片是啥", (MediaInput(media_type="image", path=banana),),
          feedback=TeacherFeedback(feedback_text="是香蕉", reward_mag=1.0))
    # 再问 — 应回最新看的香蕉
    r = _turn(db, sid, "刚刚图片是啥")
    assert r.reply_text == "是香蕉"


def test_pure_text_does_not_borrow_visual(tmp_path: Path) -> None:
    import os
    apple = "data/phase20_workbench_media/真实苹果2_2bf246de034bf5c4.jpg"
    if not os.path.exists(apple):
        return
    db = tmp_path / "t8.sqlite"; sid = "t8"
    _turn(db, sid, "这是什么", (MediaInput(media_type="image", path=apple),),
          feedback=TeacherFeedback(feedback_text="是苹果", reward_mag=1.0))
    r = _turn(db, sid, "你是谁?")
    assert "苹果" not in r.reply_text


def test_channel_signals_not_all_zero(tmp_path: Path) -> None:
    db = tmp_path / "t9.sqlite"; sid = "t9"
    for _ in range(4):
        _turn(db, sid, "你好", feedback=TeacherFeedback(feedback_text="你好呀", reward_mag=1.0))
    r = _turn(db, sid, "你好")
    found_rhythm = False
    for tick in r.tick_trace:
        fs = tick.feelings if isinstance(tick.feelings, dict) else {}
        if "rhythm_sense" in fs and float(fs["rhythm_sense"]) > 0:
            found_rhythm = True
            break
    assert found_rhythm, "rhythm_sense should be > 0 after channel signals wired"


def test_emotion_cross_turn_accumulates(tmp_path: Path) -> None:
    db = tmp_path / "t10.sqlite"; sid = "t10"
    _turn(db, sid, "这是什么")
    _turn(db, sid, "这是什么", feedback=TeacherFeedback(feedback_text="是苹果", reward_mag=1.0))
    r = _turn(db, sid, "这是什么")
    emo = r.emotion if isinstance(r.emotion, dict) else {}
    assert emo.get("cross_turn_accumulated") is True
    assert float(emo.get("valence", 0.0)) > 0.05