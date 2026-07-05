from __future__ import annotations

from pathlib import Path


def test_phase20_10m_workbench_lifecycle_drilldown_reads_existing_trace_only() -> None:
    workbench = Path("apv3test/web/static/phase20_7_workbench.js").read_text(encoding="utf-8")

    assert "10m 更深下钻" in workbench
    assert "recent_review_ticks" in workbench
    assert "recent_self_test_ticks" in workbench
    assert "lifecycle_action_deltas" in workbench
    assert "reward_pressure" in workbench
    assert "punish_pressure" in workbench
    assert "lifecycle-drilldown" in workbench
    assert "request_teacher" in workbench
    assert "stop_generating" in workbench

