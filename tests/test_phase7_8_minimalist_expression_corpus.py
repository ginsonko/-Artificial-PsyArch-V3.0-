from __future__ import annotations

from collections import Counter
from pathlib import Path

from apv3test.runtime import (
    CooccurrenceAssociationStore,
    ExpressionPhraseMemory,
    SQLiteRuntimeStore,
    assert_style_compliant,
    observe_existing_phrase_cooccurrence,
    style_safe_tokens,
)


SEED_PATH = Path(__file__).resolve().parents[1] / "apv3test" / "data" / "introspection_phrase_seed_corpus.json"
FEELING = "feeling::draft::proto_minimalist"


def test_phase7_8_seed_corpus_loads_exactly_120_phrases() -> None:
    memory = ExpressionPhraseMemory.from_seed_corpus(SEED_PATH)
    counts = Counter(record.style_tier for record in memory.records)

    assert len(memory.records) == 120
    assert counts[0] == 30
    assert counts[1] == 40
    assert counts[2] == 50
    assert len({record.phrase_id for record in memory.records}) == 120
    assert all(len(record.tokens) <= 3 for record in memory.records)


def test_phase7_8_short_phrase_wins_under_equal_cooccurrence() -> None:
    memory = ExpressionPhraseMemory.from_seed_corpus(SEED_PATH)
    result = memory.recall(
        ("p:resp:ok", "p:combo:tryok"),
        top_k=1,
        current_tick=10,
        style_bias=memory.config.expression_style_bias,
    )

    assert result[0].phrase_id == "p:resp:ok"
    assert result[0].style_tier == 0


def test_phase7_8_unknown_or_blocked_state_uses_honest_minimal_fallback() -> None:
    memory = ExpressionPhraseMemory.from_seed_corpus(SEED_PATH)
    store = CooccurrenceAssociationStore()
    candidate_pids = store.nearest_paradigms_by_label((FEELING,), top_k=3, current_tick=20)
    result = _minimal_reply_tokens(memory, candidate_pids, current_tick=20)

    assert result in {("不知道",), ("还不会",), ("...",)}
    assert_style_compliant(result)


def test_phase7_8_seed_memory_does_not_dynamically_add_unknown_phrase() -> None:
    memory = ExpressionPhraseMemory.from_seed_corpus(SEED_PATH)
    before = memory.snapshot()

    accepted = memory.observe("p:runtime:invented", ("我觉得", "可以", "试试"), weight=1.0, current_tick=30)

    assert accepted is False
    assert memory.snapshot() == before


def test_phase7_8_existing_phrase_teaching_accepts_known_and_rejects_unknown() -> None:
    memory = ExpressionPhraseMemory.from_seed_corpus(SEED_PATH)
    store = CooccurrenceAssociationStore()

    known = observe_existing_phrase_cooccurrence(
        store,
        memory,
        (FEELING,),
        ("早",),
        origin="teacher_reply",
        attention_weight=0.9,
        current_tick=1,
    )
    unknown = observe_existing_phrase_cooccurrence(
        store,
        memory,
        (FEELING,),
        ("我", "先", "完整", "说"),
        origin="teacher_reply",
        attention_weight=0.9,
        current_tick=2,
    )

    assert known == "p:resp:morning"
    assert unknown == ""
    assert store.nearest_paradigms_by_label((FEELING,), top_k=1, current_tick=3) == ("p:resp:morning",)
    assert memory.phrase_id_for_tokens(("我", "先", "完整", "说")) == ""


def test_phase7_8_style_redlines_cover_seed_and_fallback_outputs() -> None:
    memory = ExpressionPhraseMemory.from_seed_corpus(SEED_PATH)
    outputs = _freeform_style_corpus(memory, n_ticks=1000)

    assert len(outputs) == 1000
    assert all(len(tokens) <= 3 for tokens in outputs)
    assert all(style_safe_tokens(tokens) == tokens for tokens in outputs)
    assert sum(1 for tokens in outputs if "我" in "".join(tokens)) / len(outputs) < 0.05
    assert sum(1 for tokens in outputs if _tier_for(memory, tokens) == 0) / len(outputs) >= 0.3


def test_phase7_8_style_redline_falls_back_on_forbidden_or_long_output() -> None:
    assert style_safe_tokens(("我觉得", "其实", "非常", "可以")) == ("不知道",)
    assert style_safe_tokens(("好", "试试", "看看", "更多")) == ("不知道",)
    assert style_safe_tokens(("好", "!")) == ("不知道",)


def test_phase7_8_phrase_memory_sqlite_warmload_parity(tmp_path: Path) -> None:
    memory = ExpressionPhraseMemory.from_seed_corpus(SEED_PATH)
    store = CooccurrenceAssociationStore()
    observe_existing_phrase_cooccurrence(
        store,
        memory,
        (FEELING,),
        ("早",),
        origin="teacher_reply",
        attention_weight=0.9,
        current_tick=1,
    )
    state = {
        "schema_id": "apv3_phase7_8_minimalist_corpus/v1",
        "cooccurrence_associations": store.export_state(),
        "expression_phrase_memory": memory.export_state(),
    }
    sqlite = SQLiteRuntimeStore(tmp_path / "phase7_8.sqlite")
    state_id = sqlite.save_state(state)
    loaded = sqlite.load_state(state_id)
    reloaded_memory = ExpressionPhraseMemory.from_state(loaded.get("expression_phrase_memory"))
    reloaded_store = CooccurrenceAssociationStore.from_state(loaded.get("cooccurrence_associations"))

    before = _minimal_reply_tokens(memory, store.nearest_paradigms_by_label((FEELING,), top_k=5, current_tick=5), current_tick=5)
    after = _minimal_reply_tokens(
        reloaded_memory,
        reloaded_store.nearest_paradigms_by_label((FEELING,), top_k=5, current_tick=5),
        current_tick=5,
    )

    assert before == after == ("早",)
    assert reloaded_memory.allow_new_phrases is False


def test_phase7_8_runtime_has_no_phrase_kind_branch_or_style_backdoors() -> None:
    runtime_root = Path(__file__).resolve().parents[1] / "apv3test" / "runtime"
    combined = "\n".join(path.read_text(encoding="utf-8") for path in runtime_root.glob("*.py"))
    for forbidden in (
        "phrase_kind ==",
        "phrase_kind in",
        "record.phrase_kind ==",
        "case_name ==",
        "student_side_llm",
        "answer_table",
        "_most_common_reply",
        "must_reply",
    ):
        assert forbidden not in combined


def _minimal_reply_tokens(
    memory: ExpressionPhraseMemory,
    candidate_pids: tuple[str, ...],
    *,
    current_tick: int,
) -> tuple[str, ...]:
    recalled = memory.recall(candidate_pids, top_k=1, current_tick=current_tick)
    if not recalled:
        return ("不知道",)
    return style_safe_tokens(recalled[0].tokens)


def _freeform_style_corpus(memory: ExpressionPhraseMemory, *, n_ticks: int) -> tuple[tuple[str, ...], ...]:
    tier0 = tuple(record for record in memory.records if record.style_tier == 0)
    other = tuple(record for record in memory.records if record.style_tier > 0)
    outputs: list[tuple[str, ...]] = []
    for tick in range(n_ticks):
        source = tier0 if tick % 2 == 0 else other
        record = source[tick % len(source)]
        outputs.append(style_safe_tokens(record.tokens))
    return tuple(outputs)


def _tier_for(memory: ExpressionPhraseMemory, tokens: tuple[str, ...]) -> int:
    phrase_id = memory.phrase_id_for_tokens(tokens)
    for record in memory.records:
        if record.phrase_id == phrase_id:
            return record.style_tier
    return 99
