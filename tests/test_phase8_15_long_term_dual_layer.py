from __future__ import annotations

from runtime.cognitive.long_term.layers import LongTermDualLayer
from runtime.cognitive.state_pool.state_pool import StateItem


def _item(sa_id: str) -> StateItem:
    return StateItem(
        sa_id=sa_id,
        family="percept",
        label=sa_id,
        real_energy=0.8,
        cognitive_pressure=0.3,
        channel_signature=("vision", "shape"),
    )


def test_short_term_item_admits_to_cold_and_rehydrates_with_remembered_marker() -> None:
    layer = LongTermDualLayer(active_max=3, cold_capacity=5)
    item = _item("sa::remember")

    layer.admit_short_term(item)
    result = layer.rehydrate_by_cues(("sa::remember",), tick=7)

    assert "sa::remember" in layer.cold_index
    assert "sa::remember" in layer.active_pool
    assert result.items[0].source == "long_term_active"
    assert result.markers[0].kind == "REMEMBERED"


def test_active_pool_cap_eviction_returns_items_to_cold_layer() -> None:
    layer = LongTermDualLayer(active_max=2, cold_capacity=10)
    for index in range(5):
        layer.admit_short_term(_item(f"sa::{index}"))

    layer.rehydrate_by_cues(tuple(f"sa::{index}" for index in range(5)), tick=9)

    assert len(layer.active_pool) <= 2
    assert len(layer.cold_index) <= 10
    assert set(layer.active_pool).issubset(set(layer.cold_index))
