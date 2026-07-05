from __future__ import annotations

import subprocess
import sys

import pytest

from runtime.demo_substrate.profile import default_demo_profile, load_demo_profile


def test_default_demo_profile_keeps_four_scenarios_and_quiet_style() -> None:
    profile = default_demo_profile()

    assert profile.voice_style == "quiet_girl"
    assert {scenario.scenario_id for scenario in profile.scenarios} == {
        "text_dialogue",
        "desktop_companion",
        "agent_collaboration",
        "embodied_preview",
    }


def test_profile_loader_rejects_unknown_schema_version() -> None:
    with pytest.raises(ValueError):
        load_demo_profile({"schema_version": 999, "scenarios": ()})


def test_phase12_2_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "12.2"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 12.2 deliverables present" in completed.stdout
