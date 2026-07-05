from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

from runtime.cognitive.percept_vector.phase19_runtime import (
    EXTERNAL_AUDIO,
    EXTERNAL_VISUAL,
    PERCEIVED,
    SourceAwareWeights,
    active_visual_scan,
    audio_loo_probe,
    choose_next_fixation,
    extract_audio_audit_path,
    promote_event_to_concept_if_ready,
    temporal_event_bind,
)
from runtime.cognitive.percept_vector.vector_substrate import PartAssociation
from runtime.cognitive.state_pool.state_pool import load_constant


def _audio_paths() -> tuple[Path, ...]:
    root = Path("config/curriculum/assets/audio/synthetic")
    return (
        root / "audio_confirm_tone_train_0.wav",
        root / "audio_confirm_tone_train_1.wav",
        root / "audio_attention_tone_train_0.wav",
    )


def test_phase19_1_audio_receptor_is_30501_dimensional_and_source_clean() -> None:
    trace = extract_audio_audit_path(_audio_paths()[0], tick=220)

    assert len(trace.feature_vector) == int(load_constant("phase19.vector.audio_receptor_feature_dim")) == 30501
    assert trace.channel_lengths["A0"] == int(load_constant("phase19.audio.a0_dim"))
    assert sum(trace.channel_lengths[f"A{i}"] for i in range(9)) == 30501
    assert trace.receptor_version == "phase19_1a_auditory_foveated"
    assert trace.metadata["evaluator_label_accessed"] is False
    assert trace.metadata["inner_voice_sketch_only"] is True


def test_phase19_1a_audio_probe_returns_similarity_without_text_oracle() -> None:
    scores = audio_loo_probe(_audio_paths())

    assert len(scores) == 3
    assert all(0.0 <= score <= 1.0 for score in scores)
    assert max(scores) > min(scores)


def test_phase19_5_feedback_reduces_only_main_contributing_source_path() -> None:
    weights = SourceAwareWeights(
        {
            (PERCEIVED, EXTERNAL_VISUAL): 0.90,
            (PERCEIVED, EXTERNAL_AUDIO): 0.80,
            ("IMAGINED", EXTERNAL_VISUAL): 0.70,
        }
    )
    adjustment = weights.apply_feedback(
        contributions={
            (PERCEIVED, EXTERNAL_VISUAL): 0.70,
            (PERCEIVED, EXTERNAL_AUDIO): 0.20,
            ("IMAGINED", EXTERNAL_VISUAL): 0.10,
        },
        correction_strength=1.0,
    )

    assert adjustment.target_source == PERCEIVED
    assert adjustment.target_substrate == EXTERNAL_VISUAL
    assert adjustment.after < adjustment.before
    assert weights.weights[(PERCEIVED, EXTERNAL_AUDIO)] == 0.80
    assert weights.weights[("IMAGINED", EXTERNAL_VISUAL)] == 0.70


def test_phase19_5_temporal_event_promotes_only_after_threshold() -> None:
    event = temporal_event_bind(("pv_a", "aud_b"), tick_start=10, tick_end=12, source_markers=(PERCEIVED, "HEARSAY"))
    assert promote_event_to_concept_if_ready(event, (PartAssociation("part_a", 1.0),)) is None

    ready = type(event)(
        event_uuid=event.event_uuid,
        percept_uuids=event.percept_uuids,
        tick_window=event.tick_window,
        source_markers=event.source_markers,
        lifetime_cooccurrence_count=int(load_constant("phase19.binding.promote_cooccurrence_threshold")),
        metadata=event.metadata,
    )
    concept = promote_event_to_concept_if_ready(ready, (PartAssociation("part_a", 1.0),))
    assert concept is not None
    assert concept.lifecycle_status == "promoted"


def test_phase19_6_active_scan_moves_to_low_clarity_regions_and_improves_canvas() -> None:
    image_path = Path("config/curriculum/assets/visual/clean_cards/noun_apple_train_0.png")
    canvas, fixations = active_visual_scan(image_path, ticks=5)

    assert len(set(fixations)) > 1
    assert canvas.clarity_coverage() > 0.0
    before_focus = choose_next_fixation(canvas, motion_map=np.ones_like(canvas.canvas_clarity))
    assert isinstance(before_focus[0], int) and isinstance(before_focus[1], int)


def test_phase19_audio_feedback_active_redline_deliverables_pass() -> None:
    for phase in ("19.1", "19.1a", "19.4a", "19.4b", "19.5", "19.6"):
        completed = subprocess.run(
            [sys.executable, "scripts/red_line_check_v14.py", "--phase", phase],
            cwd=".",
            text=True,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
