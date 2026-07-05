from __future__ import annotations

from runtime.cognitive.endogenous.imagined_marker_spawn import spawn_imagined
from runtime.cognitive.fast_mapping.mapper import (
    fast_map_label_to_candidates,
    inject_epistemic_drive_for_mapping_gap,
    reverse_imagine_from_mapping,
)
from runtime.cognitive.state_pool.state_pool import StateItem


def _label() -> StateItem:
    return StateItem(sa_id="text::label::novel", family="vocab", label="novel", real_energy=0.8)


def _vision(sa_id: str, channel: str) -> StateItem:
    return StateItem(
        sa_id=sa_id,
        family="percept",
        label=sa_id,
        real_energy=0.8,
        attention_energy=0.4,
        channel_signature=("vision", channel),
    )


def test_fast_mapping_prefers_shape_over_color_with_same_energy() -> None:
    result = fast_map_label_to_candidates(
        _label(),
        (
            _vision("vision::color::target", "color"),
            _vision("vision::shape::target", "shape"),
        ),
    )

    assert result.best is not None
    assert result.best.channel == "shape"


def test_epistemic_drive_increases_pressure_for_mapping_gap() -> None:
    item = _label()
    before = item.cognitive_pressure

    gain = inject_epistemic_drive_for_mapping_gap(item, known_support=0.1)

    assert gain > 0.0
    assert item.cognitive_pressure > before
    assert item.gain_ledger.gain_by_source["unfinished_pressure"] > 0.0


def test_reverse_imagination_spawns_imagined_source_from_learned_mapping() -> None:
    result = fast_map_label_to_candidates(_label(), (_vision("vision::shape::target", "shape"),))
    imagined = reverse_imagine_from_mapping(result.best, support=0.8) if result.best else None

    assert imagined is not None
    marker = spawn_imagined(imagined, tick=4)
    assert marker is not None
    assert marker.kind == "IMAGINED"
