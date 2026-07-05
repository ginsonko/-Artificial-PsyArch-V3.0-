#!/usr/bin/env python3
"""W5 挂机稳定性观察 — 60连续idle turn无crash+不无限重复."""
import sys, time, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn

def main():
    td = Path(tempfile.mkdtemp()); db = td / "soak.sqlite"; sid = "soak"
    # 重现W1-B张力场景
    run_phase20_7_turn(user_text="明天吃什么好呢", session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    run_phase20_7_turn(user_text="明天吃什么好呢", teacher_feedback=TeacherFeedback(feedback_text="我还在想这个问题", reward_mag=1.0),
                       session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    for _ in range(3):
        run_phase20_7_turn(user_text="周末去哪玩好呢", session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")
    # 60连续idle
    times = []; replies = []; unique_replies = set()
    for i in range(60):
        t0 = time.perf_counter()
        r = run_phase20_7_turn(user_text="", session_id=sid, db_path=db, max_ticks=8, runtime_stage="stage6")
        dt = time.perf_counter() - t0
        times.append(dt)
        reply = r.reply_text
        replies.append(reply)
        if reply: unique_replies.add(reply)
    non_empty = sum(1 for r in replies if r)
    print(f"# 挂机稳定性观察 (W5)\n")
    print(f"| 指标 | 值 |")
    print(f"|---|---|")
    print(f"| 总idle turn | 60 |")
    print(f"| 无crash | ✅ |")
    print(f"| 非空回复次数 | {non_empty} |")
    print(f"| 不同回复内容数 | {len(unique_replies)} |")
    print(f"| 单turn耗时 min/avg/max | {min(times):.2f}/{sum(times)/len(times):.2f}/{max(times):.2f}s |")
    if non_empty >= 60:
        print(f"\n⚠️ 60次全说话 — BLOCKED (repetition_fatigue未生效)")
    else:
        print(f"\n✅ 非全说话 ({non_empty}/60) — repetition_fatigue让后续idle回归沉默")

if __name__ == "__main__":
    main()