from __future__ import annotations

from apv3test.config import APV3EnergyConfig
from apv3test.runtime import PredictionRuler


def test_empty_ticks_decay_target_cap_toward_zero() -> None:
    ruler = PredictionRuler(config=APV3EnergyConfig(real_decay=0.8, base_ratio=0.6))
    ruler.observe_external([1.0])

    caps = []
    for _ in range(8):
        ruler.begin_tick()
        caps.append(ruler.target_cap())

    assert all(left > right for left, right in zip(caps, caps[1:]))
    assert caps[-1] < caps[0]


def test_live_external_object_uses_object_level_ruler() -> None:
    ruler = PredictionRuler(config=APV3EnergyConfig(real_decay=0.8, base_ratio=0.6))
    ruler.observe_external([0.2])
    stale_cap = ruler.target_cap(support_level=1.0)
    live_cap = ruler.target_cap(support_level=1.0, live_real_energy=2.0)

    assert live_cap > stale_cap
    assert live_cap == 2.0

def test_initial_ruler_has_no_magic_floor() -> None:
    ruler = PredictionRuler(config=APV3EnergyConfig())

    assert ruler.baseline == 0.0
    assert ruler.target_cap() == 0.0

