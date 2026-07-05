from __future__ import annotations

from pathlib import Path


PHASE_MATRIX = {
    "8_2": (
        "FinalReport_Phase8_2_ContinuousTickSensorRuntime_20260617.md",
        "test_phase8_2_continuous_tick_sensor_runtime.py",
    ),
    "8_3": (
        "FinalReport_Phase8_3_SourceBoundaryLedger_20260617.md",
        "test_phase8_3_source_boundary_ledger.py",
    ),
    "8_4": (
        "FinalReport_Phase8_4_SDPLComposedVocab_20260617.md",
        "test_phase8_4_sdpl_composed_vocab.py",
    ),
    "8_5": (
        "FinalReport_Phase8_5_CognitiveFeelings_20260617.md",
        "test_phase8_5_cognitive_feelings.py",
    ),
    "8_6": (
        "FinalReport_Phase8_6_VisualSensorQuantizedBuckets_20260617.md",
        "test_phase8_6_visual_sensor.py",
    ),
    "8_7": (
        "FinalReport_Phase8_7_VisualFocusActions_20260617.md",
        "test_phase8_7_visual_focus.py",
    ),
    "8_8": (
        "FinalReport_Phase8_8_YellowAppleGeneralization_20260617.md",
        "test_phase8_8_yellow_apple_generalization.py",
    ),
    "8_9": (
        "FinalReport_Phase8_9_NaturalCorrectionSDPL_20260617.md",
        "test_phase8_9_natural_correction_sdpl.py",
    ),
    "8_10": (
        "FinalReport_Phase8_10_EndogenousSafetyMiniGate_20260617.md",
        "test_phase8_10_endogenous_safety_mini_gate.py",
    ),
    "8_11": (
        "FinalReport_Phase8_11_WebWorkbenchAudit_20260617.md",
        "test_phase8_11_web_workbench_audit.py",
    ),
    "8_12": (
        "FinalReport_Phase8_12_FastMappingReverseImagination_20260617.md",
        "test_phase8_12_fast_mapping.py",
    ),
    "8_13": (
        "FinalReport_Phase8_13_AudioSensorFilterbank_20260617.md",
        "test_phase8_13_audio_sensor.py",
    ),
    "8_14": (
        "FinalReport_Phase8_14_SDPLAnthropomorphicGates_20260617.md",
        "test_phase8_14_sdpl_anthropomorphic_gates.py",
    ),
    "8_15": (
        "FinalReport_Phase8_15_LongTermDualLayer_20260617.md",
        "test_phase8_15_long_term_dual_layer.py",
    ),
    "8_16": (
        "FinalReport_Phase8_16_CrossSessionDeferredIntention_20260617.md",
        "test_phase8_16_cross_session_deferred_intention.py",
    ),
    "8_17": (
        "FinalReport_Phase8_17_AutobiographicalRecall_20260617.md",
        "test_phase8_17_autobiographical_recall.py",
    ),
}


def test_phase8_audit_trail_has_report_and_test_for_each_declared_phase() -> None:
    root = Path(__file__).resolve().parents[1]

    for report_name, test_name in PHASE_MATRIX.values():
        assert (root / "docs" / report_name).exists(), report_name
        assert (root / "tests" / test_name).exists(), test_name


def test_phase8_audit_index_documents_redline_is_not_enough() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "docs" / "FinalReport_Phase8_AuditTrailIndex_20260617.md").read_text(
        encoding="utf-8"
    )

    assert "--phase X.Y" in text
    assert "不能替代 phase 级行为测试" in text
    assert "test_phase8_8_yellow_apple_generalization.py" in text
    assert "test_phase8_16_cross_session_deferred_intention.py" in text
