from __future__ import annotations

from apv3test.runtime import APV3WorkMemoryRuntime, WorkMemoryTickInput


def test_phase5_7_open_multitick_bundle_can_be_recalled_after_idle() -> None:
    runtime = APV3WorkMemoryRuntime()
    state = {}

    first = runtime.run_tick(
        state,
        WorkMemoryTickInput(tick=1, focus_tokens=("goal::draw", "object::apple"), pressure=0.9),
    )
    second = runtime.run_tick(
        first.state,
        WorkMemoryTickInput(tick=2, focus_tokens=("goal::draw", "color::yellow"), pressure=0.7),
    )
    idle = runtime.run_tick(second.state, WorkMemoryTickInput(tick=3, idle=True))

    assert first.active_item is not None
    assert second.active_item is not None
    assert idle.recalled_item is not None
    assert idle.recalled_item.sa_bundle == ("goal::draw", "object::apple", "color::yellow")
    assert idle.recalled_item.closed is False


def test_phase5_7_surprise_interrupts_without_erasing_unfinished_work_memory() -> None:
    runtime = APV3WorkMemoryRuntime()
    state = runtime.run_tick(
        {},
        WorkMemoryTickInput(tick=1, focus_tokens=("goal::solve", "item::math"), pressure=0.95),
    ).state

    interrupted = runtime.run_tick(
        state,
        WorkMemoryTickInput(tick=2, focus_tokens=("interrupt::noise",), pressure=0.2, surprise=1.0),
    )
    recovered = runtime.run_tick(interrupted.state, WorkMemoryTickInput(tick=3, idle=True))

    assert interrupted.interrupted_item is not None
    assert interrupted.interrupted_item.sa_bundle == ("goal::solve", "item::math")
    assert recovered.recalled_item is not None
    assert recovered.recalled_item.sa_bundle == ("goal::solve", "item::math")
    assert recovered.recalled_item.interrupted_by == ("interrupt::noise",)


def test_phase5_7_closed_work_memory_does_not_pollute_next_idle_recall() -> None:
    runtime = APV3WorkMemoryRuntime()
    state = runtime.run_tick(
        {},
        WorkMemoryTickInput(tick=1, focus_tokens=("goal::reply", "topic::done"), pressure=0.9, closure=1.0),
    ).state

    idle = runtime.run_tick(state, WorkMemoryTickInput(tick=5, idle=True))

    assert idle.recalled_item is None
    assert state["working_memory_items"][0]["closed"] is True


def test_phase5_7_work_memory_is_modality_neutral_sa_bundle() -> None:
    runtime = APV3WorkMemoryRuntime()
    state = runtime.run_tick(
        {},
        WorkMemoryTickInput(
            tick=1,
            focus_tokens=("percept::yellow", "audio::tone_high", "action::point"),
            pressure=0.8,
        ),
    ).state
    recalled = runtime.run_tick(state, WorkMemoryTickInput(tick=2, idle=True))

    assert recalled.recalled_item is not None
    assert recalled.recalled_item.sa_bundle == ("percept::yellow", "audio::tone_high", "action::point")
    assert "vision" not in str(recalled.state).lower()
    assert "if text" not in str(recalled.state).lower()
