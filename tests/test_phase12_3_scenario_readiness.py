from __future__ import annotations

import subprocess
import sys

from runtime.demo_substrate.profile import default_demo_profile
from runtime.demo_substrate.scenario_readiness import evaluate_demo_readiness


def test_scenario_readiness_passes_when_three_or_more_scenarios_are_supported() -> None:
    trace = evaluate_demo_readiness(
        default_demo_profile(),
        ("chat", "reward", "memory", "audit", "vision", "audio", "goal", "deliberative", "trust"),
    )

    assert trace.supported_count >= 3
    assert trace.ready_for_public_trial is True


def test_scenario_readiness_reports_missing_tags_for_weak_profile() -> None:
    trace = evaluate_demo_readiness(default_demo_profile(), ("chat", "audit"))
    embodied = next(item for item in trace.scenario_results if item.scenario_id == "embodied_preview")

    assert trace.ready_for_public_trial is False
    assert "vision" in embodied.missing_tags
    assert "action" in embodied.missing_tags


def test_phase12_3_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "12.3"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 12.3 deliverables present" in completed.stdout
