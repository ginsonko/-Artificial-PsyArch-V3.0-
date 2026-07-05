from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

from apv3test.chat import APV3MinimalistChatSession
from apv3test.runtime import ExpressionPhraseMemory, assert_style_compliant, load_runtime_profile
from apv3test.web_chat import APV3WebChatApp, make_handler


def test_phase8_1_cold_unknown_uses_honest_presented_fallback(tmp_path: Path) -> None:
    session = APV3MinimalistChatSession(
        profile=load_runtime_profile(sqlite_state_path=tmp_path / "cold.sqlite"),
        autoload=False,
    )

    turn = session.say("这是什么情况")
    trace = session.state["chat_session_trace"]

    assert turn.reply_text == "不知道"
    assert turn.learned_phrase_id == ""
    assert turn.committed_phrase_id == ""
    assert trace[-1]["runtime_committed_text"] == ""
    assert trace[-1]["used_honest_fallback"] is True
    assert_style_compliant(turn.reply_tokens)


def test_phase8_1_structure_modes_do_not_collapse_into_same_feeling(tmp_path: Path) -> None:
    session = APV3MinimalistChatSession(
        profile=load_runtime_profile(sqlite_state_path=tmp_path / "modes.sqlite"),
        autoload=False,
    )

    uncertain = session.say("嗯", mode="uncertain")
    flow = session.say("好", mode="flow")
    request = session.say("教教", mode="request")
    corrective = session.say("不对", mode="corrective")
    flow_again = session.say("普通输入", mode="flow")

    assert len({uncertain.feeling_label, flow.feeling_label, request.feeling_label, corrective.feeling_label}) == 4
    assert request.reply_text == "教教"
    assert corrective.reply_text == "不对"
    assert flow_again.reply_text == "好"


def test_phase8_1_web_api_message_feedback_and_snapshot(tmp_path: Path) -> None:
    app = APV3WebChatApp(state_db_path=tmp_path / "web.sqlite")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        html = urlopen(f"{base}/", timeout=5).read().decode("utf-8")
        assert "Phase20.6" in html

        first = _post_json(f"{base}/api/message", {"text": "这是什么情况", "mode": "uncertain"})
        assert first["turn"]["reply_text"] == "不知道"
        assert first["snapshot"]["metrics"]["fallback_count"] == 1

        second = _post_json(f"{base}/api/message", {"text": "嗯", "mode": "uncertain"})
        assert second["turn"]["learned_phrase_id"]

        feedback = _post_json(f"{base}/api/feedback", {"kind": "reward"})
        assert feedback["snapshot"]["tick"] == 3
        assert (tmp_path / "web.sqlite").exists()
        assert not (Path.cwd() / "web.sqlite").exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_phase8_1_unknown_text_still_does_not_pollute_phrase_memory(tmp_path: Path) -> None:
    session = APV3MinimalistChatSession(
        profile=load_runtime_profile(sqlite_state_path=tmp_path / "pollution.sqlite"),
        autoload=False,
    )

    for text in ("这是什么情况", "你知道吗", "随便聊聊"):
        session.say(text)
    memory = ExpressionPhraseMemory.from_state(session.state.get("expression_phrase_memory"))

    assert len(memory.records) == 120
    assert all("随便聊聊" not in "".join(record.tokens) for record in memory.records)


def test_phase8_1_web_chat_redline_has_no_answer_routes() -> None:
    root = Path(__file__).resolve().parents[1] / "apv3test"
    targets = [
        root / "chat.py",
        root / "web_chat.py",
        root / "web" / "static" / "app.js",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in targets)
    for forbidden in (
        "incoming_external_query ==",
        "case_name ==",
        "answer_table",
        "student_side_llm",
        "_most_common_reply",
        "must_reply",
        "USER_A",
        "USER_B",
        "user_style ==",
    ):
        assert forbidden not in combined


def _post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=raw, headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urlopen(req, timeout=5).read().decode("utf-8"))
