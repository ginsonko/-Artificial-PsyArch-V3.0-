#!/usr/bin/env python3
"""性能基线 — 每turn耗时 min/avg/max."""
import sys, time, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn

def main():
    td = Path(tempfile.mkdtemp()); db = td / "perf.sqlite"; sid = "perf"
    teach_pairs = [("你好","你好呀"),("3+7=?","10"),("没错,你好聪明","谢谢"),("这是什么","是苹果"),("你真棒","谢谢你")]
    for inp, out in teach_pairs:
        run_phase20_7_turn(user_text=inp, teacher_feedback=TeacherFeedback(feedback_text=out, reward_mag=1.0), session_id=sid, db_path=db, post_commit_idle_ticks=0, runtime_stage="stage6")
    queries = ["你好","3+7=?","你好聪明","这是什么","你真棒","量子引力","13+7=?","嗯","你好啊","真棒"]
    times = []
    for q in queries:
        t0 = time.perf_counter()
        run_phase20_7_turn(user_text=q, session_id=sid, db_path=db, post_commit_idle_ticks=0, runtime_stage="stage6")
        times.append(time.perf_counter() - t0)
    print(f"# Perf Baseline (M2)\n")
    print(f"| metric | value |")
    print(f"|---|---|")
    print(f"| min | {min(times):.3f}s |")
    print(f"| avg | {sum(times)/len(times):.3f}s |")
    print(f"| max | {max(times):.3f}s |")
    print(f"| count | {len(times)} |")
    if sum(times)/len(times) > 4.0:
        print(f"\n⚠️ avg > 4s — BLOCKED for Fable5")

if __name__ == "__main__":
    main()