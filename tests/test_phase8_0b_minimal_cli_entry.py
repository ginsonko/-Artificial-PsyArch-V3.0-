from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from apv3test.chat import APV3MinimalistChatSession
from apv3test.runtime import ExpressionPhraseMemory, assert_style_compliant, load_runtime_profile


def test_phase8_0b_chat_session_persists_user_style_across_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "chat.sqlite"
    first = APV3MinimalistChatSession(
        profile=load_runtime_profile(sqlite_state_path=db_path),
        autoload=False,
    )
    for _ in range(12):
        turn = first.say("嗯")
        assert turn.reply_text

    before = tuple(item.text for item in first.top_phrases(top_k=3))
    second = APV3MinimalistChatSession(profile=load_runtime_profile(sqlite_state_path=db_path))
    after = tuple(item.text for item in second.top_phrases(top_k=3))
    warm_turn = second.say("随便说一个词库外长句")

    assert "嗯" in before
    assert before == after
    assert warm_turn.learned_phrase_id == ""
    assert_style_compliant(warm_turn.reply_tokens)


def test_phase8_0b_unknown_user_text_does_not_pollute_seed_phrase_memory(tmp_path: Path) -> None:
    session = APV3MinimalistChatSession(
        profile=load_runtime_profile(sqlite_state_path=tmp_path / "clean.sqlite"),
        autoload=False,
    )

    turn = session.say("我想让你新增一个很长的新口头禅")
    memory = ExpressionPhraseMemory.from_state(session.state.get("expression_phrase_memory"))

    assert turn.learned_phrase_id == ""
    assert len(memory.records) == session.profile.seed_phrase_count
    assert all("我想让你新增" not in "".join(record.tokens) for record in memory.records)
    assert_style_compliant(turn.reply_tokens)


def test_phase8_0b_cli_module_runs_once_and_writes_runtime_db(tmp_path: Path) -> None:
    db_path = tmp_path / "cli_once.sqlite"
    project_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "apv3test.chat",
            "--state-db",
            str(db_path),
            "--once",
            "嗯",
        ],
        cwd=project_root,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    )

    reply = completed.stdout.strip()
    assert reply
    assert db_path.exists()
    assert "Traceback" not in completed.stderr


def test_phase8_0b_runtime_redline_has_no_cli_answer_routes() -> None:
    root = Path(__file__).resolve().parents[1] / "apv3test"
    targets = [root / "chat.py", *(root / "runtime").glob("*.py")]
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
