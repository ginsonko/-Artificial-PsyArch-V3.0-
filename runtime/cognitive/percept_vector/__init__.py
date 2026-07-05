"""Phase 19 percept-vector substrate package."""

from .phase19_runtime import (
    AudioAuditTrace,
    ConfidenceDecision,
    CueEvidence,
    FeedbackAdjustment,
    RecognitionResult,
    SourceAwareWeights,
    VectorPopulationResult,
    VisualProbeResult,
    VisualTeachingExample,
    active_visual_scan,
    audio_loo_probe,
    choose_next_fixation,
    decide_humanlike_confidence,
    extract_audio_audit_path,
    populate_visual_vectors,
    promote_event_to_concept_if_ready,
    temporal_event_bind,
    vector_signature,
    visual_loo_probe,
    visual_recognize_v1_7,
)
