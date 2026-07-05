from __future__ import annotations

from pathlib import Path


def test_phase20_10j_workbench_tick_explanations_reference_memory_rhythm() -> None:
    workbench = Path("apv3test/web/static/phase20_7_workbench.js").read_text(encoding="utf-8")

    assert "草稿把握来源" in workbench
    assert "记忆巩固" in workbench
    assert "记忆防守" in workbench
    assert "私有自测把" in workbench
    assert "记忆节律" in workbench
