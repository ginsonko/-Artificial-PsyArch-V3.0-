#!/usr/bin/env python3
"""竖式数学课程脚本 (M3升级) — 教事实+示范后, 未教组合逐列算出.

用法: python scripts/teach_vertical_addition.py <db_path>
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn
from apv3test.runtime.phase20_7.runtime import teach_process_paradigm_demonstration

FACTS = [('2+4=?','6'),('3+5=?','8'),('1+6=?','7'),('3+2=?','5'),('4+5=?','9'),
         ('2+3=?','5'),('4+3=?','7'),('2+5=?','7'),('5+8=?','13'),('4+3+1=?','8'),
         ('2+6=?','8'),('7+5=?','12'),('3+4+1=?','8')]

def main():
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tmp_vertical.sqlite")
    try:
        db.unlink(missing_ok=True)
    except PermissionError:
        pass
    teach_sid = "vertical_teach"
    for q, a in FACTS:
        run_phase20_7_turn(user_text=q, teacher_feedback=TeacherFeedback(feedback_text=a, reward_mag=1.0),
                           session_id=teach_sid, db_path=db, max_ticks=48, runtime_stage="stage6")
    # 过程范式示范: 教 AP "竖式逐列加"的行动序列 (事实×过程 = 泛化)
    for demo_example in ["23+45=68", "31+26=57"]:
        teach_process_paradigm_demonstration(db, session_id=teach_sid, example=demo_example, repeats=3)
    # 观察轮 (让 AP 也跑一遍正常 turn 看到这些题目)
    for q, a in [("23+45=?", "68"), ("31+26=?", "57")]:
        run_phase20_7_turn(user_text=q, session_id=teach_sid, db_path=db, max_ticks=48, runtime_stage="stage6")
        run_phase20_7_turn(user_text=q, teacher_feedback=TeacherFeedback(feedback_text=a, reward_mag=1.0),
                           session_id=teach_sid, db_path=db, max_ticks=48, runtime_stage="stage6")
    cold_sid = "vertical_cold"
    print("# 竖式数学课程 (M3)\n")
    print("| 问题 | 回复 | 期望 |")
    print("|---|---|---|")
    for q, expected in [("42+35=?", "77"), ("24+53=?", "77"), ("45+38=?", "83"), ("87+96=?", "不知道")]:
        r = run_phase20_7_turn(user_text=q, session_id=cold_sid, db_path=db, max_ticks=48, runtime_stage="stage6")
        ok = "✅" if (expected == "不知道" and ("不太会" in r.reply_text or "不太知道" in r.reply_text or "还在想" in r.reply_text)) or r.reply_text == expected else "❌"
        print(f"| {q} | {r.reply_text!r} | {expected} | {ok} |")
    print("\n注: 每列结果是已教事实的exact召回, 非Python eval. 87+96的7+6没教→诚实说不知道.")
    try:
        db.unlink(missing_ok=True)
    except PermissionError:
        pass  # Windows file locking — benign

if __name__ == "__main__":
    main()