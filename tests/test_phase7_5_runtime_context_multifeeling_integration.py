from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from apv3test.runtime import (
    APV3ActiveTeacherRequestRuntime,
    APV3WorkMemoryRuntime,
    ExternalExpressionToken,
    IncrementalTickInput,
    IncrementalTickRuntime,
    TeacherRequestSignal,
    WorkMemoryTickInput,
    observe_feeling_expression_cooccurrence,
)
from apv3test.runtime.cooccurrence_store import CooccurrenceAssociationStore
from apv3test.runtime.draft_introspection import emit_draft_introspection_feelings


SAN = "\u4e09"
GU = "\u987e"
MAO = "\u8305"
LU = "\u5e90"
CAO = "\u8349"
ZHI = "\u4e4b"
ZHONG = "\u4e2d"


@dataclass(frozen=True)
class _View:
    role: str
    is_filled: bool
    fit_margin: float = 0.7
    occupancy: float = 0.7
    commit_readiness: float = 0.5


@dataclass(frozen=True)
class _SituationFacts:
    situation_id: str
    views: tuple[_View, ...]
    expression_token: str
    expression_pid: str
    paradigm_competition: float = 0.0
    recent_punishment_resemblance: float = 0.0
    evidence_kind: str = ""


class _RuntimeSituationDriver:
    def __init__(self) -> None:
        self.dialogue_runtime = IncrementalTickRuntime()
        self.dialogue_state = _teach_multi_reply(_base_state(), self.dialogue_runtime)
        self.work_memory_runtime = APV3WorkMemoryRuntime()
        self.work_memory_state = _base_state()
        self.teacher_request_runtime = APV3ActiveTeacherRequestRuntime()
        self.teacher_request_state = _base_state()
        self.punish_runtime = IncrementalTickRuntime()
        self.punish_state = _base_state()
        self.flow_runtime = IncrementalTickRuntime()
        self.flow_state = _base_state()

    def dialogue_uncertain(self, tick: int) -> _SituationFacts:
        result = self.dialogue_runtime.run_tick(
            self.dialogue_state,
            IncrementalTickInput(
                tick=tick,
                cue_tokens=(SAN, GU),
                context_tokens=("ctx_idiom",),
                emit_reply=True,
                commit_after_draft=True,
                grasp=1.2,
                demand_slow=0.1,
                incoming_external_query=("?",),
            ),
        )
        self.dialogue_state = result.state
        assert result.dialogue_result is not None
        assert result.dialogue_result.emitted_tokens == (LU,)
        assert result.dialogue_result.committed_text == ""
        return _SituationFacts(
            "dialogue_uncertain",
            (
                _View("slot", False, fit_margin=0.0, occupancy=0.0, commit_readiness=0.0),
                _View("shared_fragment", True, fit_margin=0.9, occupancy=1.0, commit_readiness=0.35),
            ),
            "expr::runtime_dialogue",
            "p:expr:runtime_dialogue",
            evidence_kind="dialogue_undecidable_draft",
        )

    def work_memory_unfinished(self, tick: int) -> _SituationFacts:
        result = self.work_memory_runtime.run_tick(
            self.work_memory_state,
            WorkMemoryTickInput(
                tick=tick,
                focus_tokens=("goal::resume", "ctx::work"),
                pressure=0.92,
                closure=0.1,
            ),
        )
        self.work_memory_state = result.state
        assert result.active_item is not None
        assert result.active_item.closed is False
        return _SituationFacts(
            "work_memory_unfinished",
            (
                _View("slot", True, fit_margin=0.9, occupancy=1.0, commit_readiness=0.06),
                _View("fixed_anchor", True, fit_margin=0.9, occupancy=1.0, commit_readiness=0.06),
            ),
            "expr::runtime_work_memory",
            "p:expr:runtime_work_memory",
            evidence_kind="work_memory_unfinished_pool_entry",
        )

    def teacher_request_pressure(self, tick: int) -> _SituationFacts:
        result = self.teacher_request_runtime.observe(
            self.teacher_request_state,
            TeacherRequestSignal(
                tick=tick,
                cue_tokens=("need::answer", f"turn::{tick}"),
                context_tokens=("ctx::ask",),
                cognitive_pressure=0.95,
                recall_failed=True,
                remediation_need=0.7,
            ),
        )
        self.teacher_request_state = result.state
        assert result.request is not None
        return _SituationFacts(
            "teacher_request_pressure",
            (
                _View("slot", True, fit_margin=0.8, occupancy=1.0, commit_readiness=0.55),
                _View("fixed_anchor", True, fit_margin=0.8, occupancy=1.0, commit_readiness=0.55),
            ),
            "expr::runtime_teacher_request",
            "p:expr:runtime_teacher_request",
            paradigm_competition=1.0,
            evidence_kind="teacher_request_sa",
        )

    def recent_punishment(self, tick: int) -> _SituationFacts:
        self.punish_state = self.punish_runtime.run_tick(
            self.punish_state,
            IncrementalTickInput(
                tick=tick,
                case_name="phase7_5_punished_runtime",
                cue_tokens=("cue::retry",),
                reply_tokens=("bad::move",),
                context_tokens=("ctx::retry",),
                commit_observation=True,
                punish_delta=12.0,
            ),
        ).state
        assert any(
            float(row.get("punish_delta", 0.0)) > 0.0
            for row in self.punish_state.get("paradigm_observations", [])
            if isinstance(row, dict)
        )
        return _SituationFacts(
            "recent_punishment",
            (
                _View("slot", True, fit_margin=0.8, occupancy=1.0, commit_readiness=0.7),
                _View("fixed_anchor", True, fit_margin=0.8, occupancy=1.0, commit_readiness=0.7),
            ),
            "expr::runtime_punishment",
            "p:expr:runtime_punishment",
            recent_punishment_resemblance=1.0,
            evidence_kind="punished_action_outcome",
        )

    def rewarded_flow(self, tick: int) -> _SituationFacts:
        self.flow_state = self.flow_runtime.run_tick(
            self.flow_state,
            IncrementalTickInput(
                tick=tick,
                case_name="phase7_5_rewarded_flow",
                cue_tokens=("cue::smooth",),
                reply_tokens=("ok::smooth",),
                context_tokens=("ctx::flow",),
                commit_observation=True,
                reward_delta=1.0,
            ),
        ).state
        assert any(
            float(row.get("reward_delta", 0.0)) > 0.0
            for row in self.flow_state.get("paradigm_observations", [])
            if isinstance(row, dict)
        )
        return _SituationFacts(
            "rewarded_flow",
            (
                _View("slot", True, fit_margin=0.95, occupancy=1.0, commit_readiness=0.95),
                _View("fixed_anchor", True, fit_margin=0.95, occupancy=1.0, commit_readiness=0.95),
            ),
            "expr::runtime_flow",
            "p:expr:runtime_flow",
            evidence_kind="rewarded_smooth_commit",
        )


SITUATIONS: tuple[Callable[[_RuntimeSituationDriver, int], _SituationFacts], ...] = (
    _RuntimeSituationDriver.dialogue_uncertain,
    _RuntimeSituationDriver.work_memory_unfinished,
    _RuntimeSituationDriver.teacher_request_pressure,
    _RuntimeSituationDriver.recent_punishment,
    _RuntimeSituationDriver.rewarded_flow,
)


def test_phase7_5_runtime_contexts_learn_distinct_multifeeling_expressions() -> None:
    state, store, labels, evidence = _run_runtime_context_curriculum()

    stable_labels = _stable_labels(labels)
    assert len(set(stable_labels.values())) >= 5
    assert set(evidence.values()) == {
        "dialogue_undecidable_draft",
        "work_memory_unfinished_pool_entry",
        "teacher_request_sa",
        "punished_action_outcome",
        "rewarded_smooth_commit",
    }

    confusion = _teacher_off_replay(state, store, start_tick=500)
    for situation_id, row in confusion.items():
        assert row["label"] == stable_labels[situation_id]
        assert row["top_token"] == row["expected_token"]
        assert row["top_paradigm"] == row["expected_pid"]
        assert row["target_score"] > row["best_other_score"] * 1.4
    assert len({row["top_token"] for row in confusion.values()}) == 5


def test_phase7_5_teacher_off_replay_does_not_update_association_store() -> None:
    state, store, _, _ = _run_runtime_context_curriculum()
    before = store.snapshot()

    replay = _teacher_off_replay(state, store, start_tick=800)

    assert store.snapshot() == before
    assert all(row["observed_external_tokens"] == () for row in replay.values())


def test_phase7_5_runtime_redline_has_no_context_expression_routes() -> None:
    runtime_root = Path(__file__).resolve().parents[1] / "apv3test" / "runtime"
    combined = "\n".join(
        (runtime_root / name).read_text(encoding="utf-8")
        for name in (
            "draft_introspection.py",
            "cooccurrence_store.py",
            "cooccurrence_learning.py",
            "incremental_tick_runtime.py",
            "reply_pressure.py",
            "work_memory.py",
            "active_teacher_request.py",
        )
    )
    for forbidden in (
        "expr::runtime_",
        "dialogue_uncertain",
        "teacher_request_pressure",
        "rewarded_flow",
        "must_reply",
        "undecidable_feeling_tokens",
        "feeling::undecidable",
        "find_by_cue_token",
        "_most_common_reply",
        "pressure_type_weights",
        "student_side_llm",
        "answer_table",
        "LLM policy",
    ):
        assert forbidden not in combined


def _run_runtime_context_curriculum() -> tuple[dict[str, object], CooccurrenceAssociationStore, dict[str, list[str]], dict[str, str]]:
    driver = _RuntimeSituationDriver()
    state: dict[str, object] = {"tick": 0}
    store = CooccurrenceAssociationStore()
    labels: dict[str, list[str]] = {}
    evidence: dict[str, str] = {}
    for offset in range(150):
        tick = offset + 1
        facts = SITUATIONS[offset % len(SITUATIONS)](driver, tick)
        state = emit_draft_introspection_feelings(
            state,
            facts.views,
            current_tick=tick,
            paradigm_competition=facts.paradigm_competition,
            recent_punishment_resemblance=facts.recent_punishment_resemblance,
        )
        label = _latest_label(state, tick)
        labels.setdefault(facts.situation_id, []).append(label)
        evidence[facts.situation_id] = facts.evidence_kind
        distractor = _distractor_for(facts)
        observe_feeling_expression_cooccurrence(
            store,
            (label,),
            (
                ExternalExpressionToken(
                    facts.expression_token,
                    "teacher_reply",
                    attention_weight=0.9,
                    paradigm_id=facts.expression_pid,
                ),
                ExternalExpressionToken(
                    distractor.expression_token,
                    "perception_other",
                    attention_weight=0.13,
                    paradigm_id=distractor.expression_pid,
                ),
            ),
            current_tick=tick,
        )
    state["cooccurrence_associations"] = store.export_state()
    return state, store, labels, evidence


def _teacher_off_replay(
    state: Mapping[str, object],
    store: CooccurrenceAssociationStore,
    *,
    start_tick: int,
) -> dict[str, dict[str, object]]:
    driver = _RuntimeSituationDriver()
    replay_state = dict(state)
    result: dict[str, dict[str, object]] = {}
    all_tokens = _all_expression_tokens()
    for index, situation in enumerate(SITUATIONS):
        tick = start_tick + index
        facts = situation(driver, tick)
        replay_state = emit_draft_introspection_feelings(
            replay_state,
            facts.views,
            current_tick=tick,
            paradigm_competition=facts.paradigm_competition,
            recent_punishment_resemblance=facts.recent_punishment_resemblance,
        )
        label = _latest_label(replay_state, tick)
        other_scores = [
            store.similarity(label, token, tick)
            for token in all_tokens
            if token != facts.expression_token
        ]
        result[facts.situation_id] = {
            "label": label,
            "top_token": store.nearest_by_label((label,), top_k=1, current_tick=tick)[0],
            "top_paradigm": store.nearest_paradigms_by_label((label,), top_k=1, current_tick=tick)[0],
            "expected_token": facts.expression_token,
            "expected_pid": facts.expression_pid,
            "target_score": store.similarity(label, facts.expression_token, tick),
            "best_other_score": max(other_scores, default=0.0),
            "observed_external_tokens": (),
        }
    return result


def _base_state() -> dict[str, object]:
    return {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {
            "tokens": {
                "ctx_idiom": {"vector": [0.0, 1.0], "support": 4.0, "promoted": True},
            }
        },
        "transitions": [],
        "paradigms": [],
        "action_outcomes": {},
        "percept_prototypes": [],
    }


def _teach_multi_reply(state: dict[str, object], runtime: IncrementalTickRuntime) -> dict[str, object]:
    for tick, reply in tuple((tick, (MAO, LU)) for tick in range(1, 8)) + tuple(
        (tick, (CAO, LU, ZHI, ZHONG)) for tick in range(8, 15)
    ):
        state = runtime.run_tick(
            state,
            IncrementalTickInput(
                tick=tick,
                case_name="phase7_5_dialogue_uncertain",
                cue_tokens=(SAN, GU),
                reply_tokens=reply,
                context_tokens=("ctx_idiom",),
                commit_observation=True,
                reward_delta=1.0,
            ),
        ).state
    return state


def _latest_label(state: Mapping[str, object], tick: int) -> str:
    rows = state.get("introspection_feelings", [])
    if not isinstance(rows, list):
        raise AssertionError("missing introspection feelings")
    for item in reversed(rows):
        if isinstance(item, Mapping) and int(item.get("tick", -1)) == int(tick):
            return str(item.get("sa_label", ""))
    raise AssertionError(f"missing feeling at tick {tick}")


def _stable_labels(labels: Mapping[str, list[str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for situation_id, values in labels.items():
        tail = values[-10:]
        label, count = Counter(tail).most_common(1)[0]
        assert count >= 8
        result[situation_id] = label
    return result


def _distractor_for(facts: _SituationFacts) -> _SituationFacts:
    items = _canonical_situations()
    index = next(i for i, item in enumerate(items) if item.situation_id == facts.situation_id)
    return items[(index + 2) % len(items)]


def _canonical_situations() -> tuple[_SituationFacts, ...]:
    return (
        _SituationFacts("dialogue_uncertain", (), "expr::runtime_dialogue", "p:expr:runtime_dialogue"),
        _SituationFacts("work_memory_unfinished", (), "expr::runtime_work_memory", "p:expr:runtime_work_memory"),
        _SituationFacts("teacher_request_pressure", (), "expr::runtime_teacher_request", "p:expr:runtime_teacher_request"),
        _SituationFacts("recent_punishment", (), "expr::runtime_punishment", "p:expr:runtime_punishment"),
        _SituationFacts("rewarded_flow", (), "expr::runtime_flow", "p:expr:runtime_flow"),
    )


def _all_expression_tokens() -> tuple[str, ...]:
    return tuple(item.expression_token for item in _canonical_situations())
