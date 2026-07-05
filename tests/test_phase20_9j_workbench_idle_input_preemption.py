from __future__ import annotations

from pathlib import Path


WORKBENCH_JS = Path("apv3test/web/static/phase20_7_workbench.js")


def test_phase20_9j_workbench_queues_user_turn_during_idle_request() -> None:
    js = WORKBENCH_JS.read_text(encoding="utf-8")

    assert "let pendingUserTurn = null;" in js
    assert "function hasUserPayload(payload)" in js
    assert "async function sendTurn({ idle = false, queuedPayload = null } = {})" in js
    assert "if (requestInFlight)" in js
    assert "pendingUserTurn = payloadToSend;" in js
    assert "stopAutoIdle();" in js
    assert 'setStatus("已暂停闲时，排队处理你的输入", "running");' in js
    assert "sendTurn({ idle: false, queuedPayload: queued })" in js


def test_phase20_9j_workbench_idle_tick_still_does_not_queue_empty_idle() -> None:
    js = WORKBENCH_JS.read_text(encoding="utf-8")
    request_block = js[js.index("if (requestInFlight)") : js.index("const payload = payloadToSend;")]

    assert "if (!idle && hasUserPayload(payloadToSend))" in request_block
    assert "return;" in request_block
