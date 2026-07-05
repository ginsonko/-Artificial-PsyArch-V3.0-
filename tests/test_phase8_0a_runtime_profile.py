from __future__ import annotations

from pathlib import Path

from apv3test.chat import APV3MinimalistChatSession
from apv3test.runtime import ExpressionPhraseMemory, assert_style_compliant, load_runtime_profile


def test_phase8_0a_runtime_profile_loads_clean_paths(tmp_path: Path) -> None:
    profile = load_runtime_profile(sqlite_state_path=tmp_path / "chat.sqlite")

    assert profile.profile_id == "apv3_minimalist_cli"
    assert profile.seed_corpus_path.exists()
    assert profile.sqlite_state_path == (tmp_path / "chat.sqlite").resolve()
    assert profile.allow_new_phrases is False
    assert profile.style_gate_enabled is True
    assert profile.style_max_tokens <= 3
    assert all(not module.startswith("tests.") for module in profile.runtime_modules)


def test_phase8_0a_profile_instantiates_minimal_runtime_without_fixture(tmp_path: Path) -> None:
    profile = load_runtime_profile(sqlite_state_path=tmp_path / "runtime.sqlite")
    session = APV3MinimalistChatSession(profile=profile, autoload=False)

    turn = session.say("嗯")
    memory = ExpressionPhraseMemory.from_state(session.state.get("expression_phrase_memory"))

    assert turn.reply_text
    assert turn.learned_phrase_id
    assert len(memory.records) == profile.seed_phrase_count
    assert session.store.db_path == profile.sqlite_state_path
    assert profile.sqlite_state_path.exists()
    assert not (Path.cwd() / "runtime.sqlite").exists()
    assert_style_compliant(turn.reply_tokens, max_tokens=profile.style_max_tokens)


def test_phase8_0a_runtime_profile_has_no_fixture_route_fields() -> None:
    profile = load_runtime_profile()

    assert "tmp_path" in profile.disabled_dev_fields
    assert "test_fixture" in profile.disabled_dev_fields
    assert "answer_table" in profile.forbidden_runtime_markers
    assert "student_side_llm" in profile.forbidden_runtime_markers
    assert "phase" not in profile.profile_id
    assert not profile.runtime_entry.startswith("tests.")
    assert "fixture" not in profile.runtime_entry
    assert "tmp_path" not in profile.runtime_entry
