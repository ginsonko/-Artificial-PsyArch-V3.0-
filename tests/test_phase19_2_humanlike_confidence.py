from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.percept_vector.phase19_runtime import CueEvidence, decide_humanlike_confidence


def test_phase19_2_few_strong_cues_can_make_a_humanlike_soft_or_firm_call() -> None:
    decision = decide_humanlike_confidence(
        (
            CueEvidence("round_shape", 0.91, 0.86, 0.95),
            CueEvidence("red_yellow_skin", 0.82, 0.78, 0.90),
            CueEvidence("stem_hint", 0.34, 0.55, 0.70),
        ),
        top_score=0.78,
        nearest_negative_score=0.49,
        source_reliability=0.92,
        object_novelty=0.20,
        context_novelty=0.15,
    )

    assert decision.raw_confidence > 0.36
    assert decision.decision_tier in {"soft", "firm"}
    assert decision.decomposition["Pi"] < 1.0
    assert decision.decomposition["Gamma"] > 0.0


def test_phase19_2_equal_top_scores_do_not_get_false_margin_confidence() -> None:
    decision = decide_humanlike_confidence(
        (
            CueEvidence("shared_color", 0.82, 0.70, 0.90),
            CueEvidence("shared_curve", 0.80, 0.65, 0.90),
        ),
        top_score=0.61,
        nearest_negative_score=0.61,
        source_reliability=0.95,
        object_novelty=0.10,
        context_novelty=0.10,
    )

    assert decision.decomposition["mu"] < 0.50
    assert decision.decision_tier != "firm"


def test_phase19_2_context_novelty_downgrades_to_reinspect_not_no_call() -> None:
    decision = decide_humanlike_confidence(
        (
            CueEvidence("clear_voice", 0.96, 0.88, 0.95),
            CueEvidence("known_rhythm", 0.90, 0.80, 0.90),
        ),
        top_score=0.90,
        nearest_negative_score=0.20,
        source_reliability=0.98,
        object_novelty=0.05,
        context_novelty=0.90,
    )

    assert decision.raw_confidence > 0.60
    assert decision.decision_tier == "soft"


def test_phase19_2_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "19.2"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
