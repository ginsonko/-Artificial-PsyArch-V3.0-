from __future__ import annotations

from apv3test.runtime import AnchorRelativeAligner, ParadigmDiscoveryEngine, ParadigmObservation, RelationCoherenceScorer


def test_relation_coherence_scores_slot_by_shared_neighbors() -> None:
    aligner = AnchorRelativeAligner()

    alignment = aligner.align(
        [
            ("color::red", "object::apple"),
            ("color::yellow", "object::apple"),
            ("color::blue", "object::apple"),
        ]
    )
    slot = alignment.columns[0]

    assert slot.role == "slot"
    assert slot.relation_coherence == 1.0
    assert slot.relation_signature_tokens == ("color::blue", "color::red", "color::yellow")


def test_low_relation_overlap_drags_discovered_paradigm_confidence_down() -> None:
    engine = ParadigmDiscoveryEngine()

    good = engine.discover(
        [
            ParadigmObservation("good_color_object", ("cue",), ("color::red", "object::apple")),
            ParadigmObservation("good_color_object", ("cue",), ("color::yellow", "object::apple")),
            ParadigmObservation("good_color_object", ("cue",), ("color::blue", "object::apple")),
        ]
    )[0]
    bad = engine.discover(
        [
            ParadigmObservation("bad_mixed_slot", ("cue",), ("color::red", "object::apple")),
            ParadigmObservation("bad_mixed_slot", ("cue",), ("sound::loud", "place::river")),
            ParadigmObservation("bad_mixed_slot", ("cue",), ("touch::soft", "object::stone")),
        ]
    )[0]

    assert good.conf > bad.conf
    assert good.columns[0].relation_coherence > bad.columns[0].relation_coherence


def test_relation_coherence_is_modality_agnostic_for_first_class_sa() -> None:
    scorer = RelationCoherenceScorer()

    coherence = scorer.score_column(
        [
            ("vision::yellow", "object::apple"),
            ("text::黄色", "object::apple"),
            ("audio::yellow_word", "object::apple"),
        ],
        ("vision::yellow", "text::黄色", "audio::yellow_word"),
    )

    assert coherence.score == 1.0
    assert coherence.pair_count == 3
