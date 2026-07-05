from __future__ import annotations

from pathlib import Path


def test_phase20_10l_workbench_lifecycle_and_replay_share_memory_rhythm_timeline_language() -> None:
    workbench = Path("apv3test/web/static/phase20_7_workbench.js").read_text(encoding="utf-8")

    assert "10l 同一时间线" in workbench
    assert "对象:记忆巩固·历史时间线" in workbench
    assert "对象:遗忘压力·历史时间线" in workbench
    assert "对象:复习节律·历史时间线" in workbench
    assert "对象:再巩固·历史时间线" in workbench
