from __future__ import annotations

from pathlib import Path


def test_phase20_10i_workbench_static_displays_memory_rhythm_and_outcome_bars() -> None:
    workbench = Path("apv3test/web/static/phase20_7_workbench.js").read_text(encoding="utf-8")

    assert "10f 记忆节律" in workbench
    assert "10h 后果把握" in workbench
    assert "对象:记忆巩固·历史时间线" in workbench
    assert "对象:遗忘压力·历史时间线" in workbench
    assert "对象:复习节律·历史时间线" in workbench
    assert "对象:再巩固·历史时间线" in workbench
