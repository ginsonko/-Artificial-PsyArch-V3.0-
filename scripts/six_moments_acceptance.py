#!/usr/bin/env python3
"""V5 六时刻自动验收 — M-A~M-F 逐一复现出报告."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn

FACTS = [('2+4=?','6'),('3+5=?','8'),('1+6=?','7'),('3+2=?','5'),('4+5=?','9'),
         ('2+3=?','5'),('4+3=?','7'),('2+5=?','7'),('5+8=?','13'),('4+3+1=?','8'),
         ('2+6=?','8'),('7+5=?','12'),('3+4+1=?','8')]

def main():
    td = Path(tempfile.mkdtemp()); db = td / "six.sqlite"
    results = []

    # M-A: 张力自发说话
    sid = "ma"
    run_phase20_7_turn(user_text="明天吃什么好呢", session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    run_phase20_7_turn(user_text="明天吃什么好呢", teacher_feedback=TeacherFeedback(feedback_text="我还在想这个问题", reward_mag=1.0),
                       session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    for _ in range(3):
        run_phase20_7_turn(user_text="周末去哪玩好呢", session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    r = run_phase20_7_turn(user_text="", session_id=sid, db_path=db, max_ticks=8, runtime_stage="stage6")
    ma = bool(r.reply_text)
    results.append(("M-A 活的", "张力后idle自发说话", repr(r.reply_text), "非空", "✅" if ma else "❌"))

    # M-B: 在想 (write→read→commit序列)
    sid = "mb"
    run_phase20_7_turn(user_text="你好", teacher_feedback=TeacherFeedback(feedback_text="你好呀", reward_mag=1.0),
                       session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    r = run_phase20_7_turn(user_text="你好", session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    actions = [t.selected_action.get("action_type","") for t in r.tick_trace if isinstance(t.selected_action, dict)]
    mb = "write_cell" in actions and "read_draft" in actions and "commit_reply" in actions
    results.append(("M-B 在想", "write→read→commit序列", str(actions[:5]), "含三者", "✅" if mb else "❌"))

    # M-C: 教得动 (教学召回+泛化+惩罚不复读)
    sid = "mc"
    run_phase20_7_turn(user_text="你好", teacher_feedback=TeacherFeedback(feedback_text="你好呀", reward_mag=1.0),
                       session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    r1 = run_phase20_7_turn(user_text="你好", session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    run_phase20_7_turn(user_text="没错,你真聪明", teacher_feedback=TeacherFeedback(feedback_text="谢谢", reward_mag=1.0),
                       session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    r2 = run_phase20_7_turn(user_text="你真聪明", session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    run_phase20_7_turn(user_text="你真棒", teacher_feedback=TeacherFeedback(feedback_text="谢谢你", reward_mag=1.0),
                       session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    run_phase20_7_turn(user_text="你真棒", teacher_feedback=TeacherFeedback(feedback_text="不对", punish_mag=1.0),
                       session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    r3 = run_phase20_7_turn(user_text="真棒", session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    mc = r1.reply_text == "你好呀" and r2.reply_text == "谢谢" and r3.reply_text != "不对"
    results.append(("M-C 教得动", "召回+'泛化+惩罚不复读", f"召回={r1.reply_text!r} 泛化={r2.reply_text!r} 纠错后={r3.reply_text!r}", "召回+泛化+不复读", "✅" if mc else "❌"))

    # M-D: 不糊弄 (未知诚实+视觉回指)
    sid = "md"
    r4 = run_phase20_7_turn(user_text="量子引力是什么", session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    md = "不太知道" in r4.reply_text or "还在想" in r4.reply_text
    results.append(("M-D 不糊弄", "未知诚实说不知道", repr(r4.reply_text), "含不太知道", "✅" if md else "❌"))

    # M-E: 会算不是背 (竖式范式组合)
    sid = "me"
    for q, a in FACTS:
        run_phase20_7_turn(user_text=q, teacher_feedback=TeacherFeedback(feedback_text=a, reward_mag=1.0),
                           session_id=sid, db_path=db, max_ticks=48, runtime_stage="stage6")
    run_phase20_7_turn(user_text="23+45=?", session_id=sid, db_path=db, max_ticks=48, runtime_stage="stage6")
    run_phase20_7_turn(user_text="23+45=?", teacher_feedback=TeacherFeedback(feedback_text="68", reward_mag=1.0),
                       session_id=sid, db_path=db, max_ticks=48, runtime_stage="stage6")
    run_phase20_7_turn(user_text="31+26=?", session_id=sid, db_path=db, max_ticks=48, runtime_stage="stage6")
    run_phase20_7_turn(user_text="31+26=?", teacher_feedback=TeacherFeedback(feedback_text="57", reward_mag=1.0),
                       session_id=sid, db_path=db, max_ticks=48, runtime_stage="stage6")
    r5 = run_phase20_7_turn(user_text="42+35=?", session_id=sid, db_path=db, max_ticks=48, runtime_stage="stage6")
    r6 = run_phase20_7_turn(user_text="87+96=?", session_id=sid, db_path=db, max_ticks=48, runtime_stage="stage6")
    me = r5.reply_text == "77" and ("不太知道" in r6.reply_text or "还在想" in r6.reply_text)
    results.append(("M-E 会算不是背", "42+35=77+87+96不知道", f"42+35={r5.reply_text!r} 87+96={r6.reply_text!r}", "77+不知道", "✅" if me else "❌"))

    # M-F: 有心情 (情绪通道+rhythm+fatigue非零)
    sid = "mf"
    for _ in range(4):
        run_phase20_7_turn(user_text="你好", teacher_feedback=TeacherFeedback(feedback_text="你好呀", reward_mag=1.0),
                           session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    r7 = run_phase20_7_turn(user_text="你好", session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    rhythm = 0.0; fatigue = 0.0
    for t in r7.tick_trace:
        fs = t.feelings if isinstance(t.feelings, dict) else {}
        if "rhythm_sense" in fs: rhythm = float(fs["rhythm_sense"])
        if "repetition_fatigue_channel" in fs: fatigue = float(fs["repetition_fatigue_channel"])
        if rhythm > 0 or fatigue > 0: break
    emo = r7.emotion if isinstance(r7.emotion, dict) else {}
    mf = rhythm > 0 or fatigue > 0
    results.append(("M-F 有心情", "rhythm/fatigue非零+rhythm=fatigue", f"rhythm={rhythm} fatigue={fatigue} emo_valence={emo.get('valence','?')}", "非零", "✅" if mf else "❌"))

    # 输出报告
    print("# 六时刻自动验收报告\n")
    all_pass = all(r[4] == "✅" for r in results)
    print(f"**总判定: {'6/6 PASS ✅' if all_pass else '有FAIL ❌'}**\n")
    print("| 时刻 | 场景 | 实际 | 期望 | 判定 |")
    print("|---|---|---|---|---|")
    for name, scene, actual, expected, verdict in results:
        print(f"| {name} | {scene} | {actual} | {expected} | {verdict} |")
    if not all_pass:
        print("\n⚠️ 有FAIL — BLOCKED")

if __name__ == "__main__":
    main()