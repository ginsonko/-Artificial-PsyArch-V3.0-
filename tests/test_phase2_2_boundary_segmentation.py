from __future__ import annotations

from apv3test.runtime import BoundaryFeelingSegmenter, FocusTick, ParadigmDiscoveryEngine, ParadigmObservation


def test_boundary_feeling_segments_cross_tick_units_without_turn_flag() -> None:
    segmenter = BoundaryFeelingSegmenter()

    segments = segmenter.segment(
        [
            FocusTick(0, ("text::三", "text::顾")),
            FocusTick(1, ("text::茅", "text::庐"), step_closure=0.75),
            FocusTick(2, ("text::问候", "text::你好")),
            FocusTick(3, ("text::我", "text::在")),
        ]
    )

    assert len(segments) == 2
    assert segments[0].flattened_sa == ("text::三", "text::顾", "text::茅", "text::庐")
    assert segments[1].flattened_sa == ("text::问候", "text::你好", "text::我", "text::在")
    assert segments[0].boundary_feelings[-1].sa_label == "feeling::boundary::step_closure"


def test_boundary_supports_mixed_modality_first_class_sa() -> None:
    segmenter = BoundaryFeelingSegmenter()

    segments = segmenter.segment(
        [
            FocusTick(10, ("vision::yellow", "vision::apple")),
            FocusTick(11, ("text::黄色", "text::苹果"), quantity_closure=0.8),
            FocusTick(12, ("audio::ding", "feeling::surprise"), rhythm_reset=0.9),
            FocusTick(13, ("action::look_back", "feeling::explained")),
        ]
    )

    assert len(segments) == 2
    assert "vision::yellow" in segments[0].flattened_sa
    assert "audio::ding" in segments[1].flattened_sa
    assert segments[0].boundary_feelings[-1].sa_label == "feeling::boundary::quantity_closure"


def test_boundary_is_independent_of_label_text_when_signals_match() -> None:
    segmenter = BoundaryFeelingSegmenter()
    first = [
        FocusTick(0, ("text::A", "vision::B")),
        FocusTick(1, ("text::C", "vision::D"), step_closure=0.75),
        FocusTick(2, ("action::E",)),
    ]
    second = [
        FocusTick(0, ("sound::x", "motor::y")),
        FocusTick(1, ("sound::z", "motor::w"), step_closure=0.75),
        FocusTick(2, ("feeling::q",)),
    ]

    first_boundaries = [feeling.boundary for segment in segmenter.segment(first) for feeling in segment.boundary_feelings]
    second_boundaries = [feeling.boundary for segment in segmenter.segment(second) for feeling in segment.boundary_feelings]

    assert first_boundaries == second_boundaries


def test_segmented_units_can_feed_paradigm_discovery() -> None:
    segmenter = BoundaryFeelingSegmenter()
    engine = ParadigmDiscoveryEngine()
    episodes = [
        [
            FocusTick(0, ("cue::三", "cue::顾")),
            FocusTick(1, ("reply::茅", "reply::庐"), step_closure=0.75),
        ],
        [
            FocusTick(10, ("cue::三", "cue::顾")),
            FocusTick(11, ("reply::臣", "reply::于", "reply::草", "reply::庐"), step_closure=0.75),
        ],
    ]
    observations = []
    for episode in episodes:
        segment = segmenter.segment(episode)[0]
        cue = tuple(label for label in segment.flattened_sa if label.startswith("cue::"))
        reply = tuple(label for label in segment.flattened_sa if label.startswith("reply::"))
        observations.append(ParadigmObservation("cross_tick_idiom", cue, reply))

    discovered = engine.discover(observations)

    assert discovered[0].cue_text == "cue::三cue::顾"
    assert any(column.role == "shared_fragment" for column in discovered[0].columns)
