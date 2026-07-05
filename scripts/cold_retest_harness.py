#!/usr/bin/env python3
"""冷重测 harness — 从源 DB 读已学经验，用全新 session 冷重测召回通过率.

用法: python scripts/cold_retest_harness.py <source_db> [--session-prefix cold]
不修改 source_db. 输出 markdown 通过率表到 stdout.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

# 确保能 import apv3test (脚本从 scripts/ 跑时需加上级目录)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(description="Cold retest harness")
    parser.add_argument("source_db", type=str, help="Path to source phase20_7 DB")
    parser.add_argument("--session-prefix", type=str, default="cold", help="Session prefix for cold test")
    args = parser.parse_args()

    source = Path(args.source_db)
    if not source.exists():
        print(f"ERROR: source DB not found: {source}", file=sys.stderr)
        sys.exit(1)

    # 1) 从 source_db 读 experience_alignment (排除 counter_evidence 和 expression_role 非空)
    pairs: list[tuple[str, str]] = []
    with sqlite3.connect(str(source)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT payload_json FROM phase20_7_experience_events WHERE event_kind='experience_alignment'"
        ).fetchall()
        for row in rows:
            payload = json.loads(row["payload_json"])
            if str(payload.get("alignment_role") or "") == "counter_evidence":
                continue
            if payload.get("expression_role"):
                continue
            output_text = "".join(str(ch) for ch in payload.get("output_chars", ()))
            if not output_text:
                continue
            # input_text 从 input_event_id 的 payload.text 取
            input_event_id = payload.get("input_event_id")
            if not input_event_id:
                continue
            irow = conn.execute(
                "SELECT payload_json FROM phase20_7_experience_events WHERE event_id=?",
                (str(input_event_id),),
            ).fetchone()
            if irow is None:
                continue
            ipayload = json.loads(irow[0]) if irow[0] else {}
            input_text = str(ipayload.get("text", "") or "")
            if not input_text:
                continue
            pairs.append((input_text, output_text))

    if not pairs:
        print("No valid (input, output) pairs found for cold retest.")
        return

    # 2) 复制 source_db 到临时文件 (保留长期库=经验流)
    tmpdir = Path(tempfile.mkdtemp())
    cold_db = tmpdir / "cold_copy.sqlite"
    shutil.copy2(source, cold_db)

    # 3) 用全新 session 冷重测
    cold_session = f"{args.session_prefix}_{int(time.time())}"
    from apv3test.runtime.phase20_7 import run_phase20_7_turn

    results: list[tuple[str, str, str, bool]] = []
    for input_text, expected_output in pairs:
        result = run_phase20_7_turn(
            user_text=input_text,
            session_id=cold_session,
            db_path=cold_db,
            post_commit_idle_ticks=0,
            runtime_stage="stage6",
        )
        actual = result.reply_text
        passed = actual == expected_output
        results.append((input_text, expected_output, actual, passed))

    # 4) 输出 markdown 通过率表
    total = len(results)
    passed_count = sum(1 for _, _, _, p in results if p)
    print(f"# Cold Retest Report\n")
    print(f"- Source DB: `{source}`")
    print(f"- Cold session: `{cold_session}`")
    print(f"- Total pairs: {total}")
    print(f"- Passed: {passed_count}")
    print(f"- Failed: {total - passed_count}")
    print(f"- Pass rate: {passed_count / total * 100:.1f}%\n")
    print("| Input | Expected | Actual | Pass |")
    print("|---|---|---|---|")
    for inp, exp, act, p in results:
        status = "✅" if p else "❌"
        print(f"| {inp[:30]} | {exp[:30]} | {act[:30]} | {status} |")

    # 5) 清理临时文件 (Windows 可能锁文件, 容错)
    try:
        cold_db.unlink(missing_ok=True)
        tmpdir.rmdir()
    except (PermissionError, OSError):
        pass  # 临时文件, 系统重启后自动清理


if __name__ == "__main__":
    main()