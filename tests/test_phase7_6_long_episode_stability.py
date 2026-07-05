from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import random

from apv3test.runtime import (
    APV3ActiveTeacherRequestRuntime,
    APV3WorkMemoryRuntime,
    ExternalExpressionToken,
    IncrementalTickInput,
    IncrementalTickRuntime,
    SQLiteRuntimeStore,
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


class _LongRuntimeDriver:
    def __init__(self, snapshot: dict[str, object] | None = None) -> None:
        self.dialogue_runtime = IncrementalTickRuntime()
        self.work_memory_runtime = APV3WorkMemoryRuntime()
        self.teacher_request_runtime = APV3ActiveTeacherRequestRuntime()
        self.punish_runtime = IncrementalTickRuntime()
        self.flow_runtime = IncrementalTickRuntime()
        if snapshot is None:
            self.dialogue_state = _teach_multi_reply(_base_state(), self.dialogue_runtime)
            self.work_memory_state = _base_state()
            self.teacher_request_state = _base_state()
            self.punish_state = _base_state()
            self.flow_state = _base_state()
        else:
            self.dialogue_state = dict(snapshot["dialogue_state"])
            self.work_memory_state = dict(snapshot["work_memory_state"])
            self.teacher_request_state = dict(snapshot["teacher_request_state"])
            self.punish_state = dict(snapshot["punish_state"])
            self.flow_state = dict(snapshot["flow_state"])

    def snapshot(self) -> dict[str, object]:
        return {
            "dialogue_state": self.dialogue_state,
            "work_memory_state": self.work_memory_state,
            "teacher_request_state": self.teacher_request_state,
            "punish_state": self.punish_state,
            "flow_state": self.flow_state,
        }

    def emit(self, kind: int, tick: int) -> _SituationFacts:
        return (
            self.dialogue_uncertain,
            self.work_memory_unfinished,
            self.teacher_request_pressure,
            self.recent_punishment,
            self.rewarded_flow,
        )[kind](tick)

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
        return _canonical_situations()[0]

    def work_memory_unfinished(self, tick: int) -> _SituationFacts:
        result = self.work_memory_runtime.run_tick(
            self.work_memory_state,
            WorkMemoryTickInput(tick=tick, focus_tokens=("goal::resume", "ctx::work"), pressure=0.92, closure=0.1),
        )
        self.work_memory_state = result.state
        assert result.active_item is not None and result.active_item.closed is False
        return _canonical_situations()[1]

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
        return _canonical_situations()[2]

    def recent_punishment(self, tick: int) -> _SituationFacts:
        self.punish_state = self.punish_runtime.run_tick(
            self.punish_state,
            IncrementalTickInput(
                tick=tick,
                case_name="phase7_6_punished_runtime",
                cue_tokens=("cue::retry",),
                reply_tokens=("bad::move",),
                context_tokens=("ctx::retry",),
                commit_observation=True,
                punish_delta=12.0,
            ),
        ).state
        assert any(
            isinstance(row, dict) and float(row.get("punish_delta", 0.0)) > 0.0
            for row in self.punish_state.get("paradigm_observations", [])
        )
        return _canonical_situations()[3]

    def rewarded_flow(self, tick: int) -> _SituationFacts:
        self.flow_state = self.flow_runtime.run_tick(
            self.flow_state,
            IncrementalTickInput(
                tick=tick,
                case_name="phase7_6_rewarded_flow",
                cue_tokens=("cue::smooth",),
                reply_tokens=("ok::smooth",),
                context_tokens=("ctx::flow",),
                commit_observation=True,
                reward_delta=1.0,
            ),
        ).state
        assert any(
            isinstance(row, dict) and float(row.get("reward_delta", 0.0)) > 0.0
            for row in self.flow_state.get("paradigm_observations", [])
        )
        return _canonical_situations()[4]


class _LongEpisodeHarness:
    def __init__(self, snapshot: dict[str, object] | None = None) -> None:
        if snapshot is None:
            self.state: dict[str, object] = {"schema_id": "apv3_phase7_6_long_episode/v1", "tick": 0}
            self.store = CooccurrenceAssociationStore()
            self.labels: dict[str, list[str]] = {item.situation_id: [] for item in _canonical_situations()}
            self.driver = _LongRuntimeDriver()
        else:
            self.state = dict(snapshot["state"])
            self.store = CooccurrenceAssociationStore.from_state(snapshot["cooccurrence_store"])
            self.labels = {
                str(key): [str(item) for item in value]
                for key, value in dict(snapshot["labels"]).items()
            }
            self.driver = _LongRuntimeDriver(dict(snapshot["driver"]))

    def snapshot(self) -> dict[str, object]:
        self.state["cooccurrence_associations"] = self.store.export_state()
        return {
            "schema_id": "apv3_phase7_6_harness_snapshot/v1",
            "state": self.state,
            "cooccurrence_store": self.store.export_state(),
            "labels": self.labels,
            "driver": self.driver.snapshot(),
        }

    def run_one(self, kind: int, tick: int) -> None:
        facts = self.driver.emit(kind, tick)
        self.state = emit_draft_introspection_feelings(
            self.state,
            facts.views,
            current_tick=tick,
            paradigm_competition=facts.paradigm_competition,
            recent_punishment_resemblance=facts.recent_punishment_resemblance,
        )
        label = _latest_label(self.state, tick)
        self.labels[facts.situation_id].append(label)
        distractor = _canonical_situations()[(kind + 2) % len(_canonical_situations())]
        observe_feeling_expression_cooccurrence(
            self.store,
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
                    attention_weight=0.11,
                    paradigm_id=distractor.expression_pid,
                ),
            ),
            current_tick=tick,
        )


def test_phase7_6_long_episode_keeps_five_feelings_stable() -> None:
    harness = _run_long_episode()
    confusion = _teacher_off_replay(harness, start_tick=1500)
    stable = _stable_labels(harness.labels)
    max_gaps = _max_gaps_by_kind(_long_sequence())

    assert max_gaps[4] >= 120
    assert len(set(stable.values())) == 5
    for situation_id, row in confusion.items():
        assert row["label"] == stable[situation_id]
        assert row["top_token"] == row["expected_token"]
        assert row["top_paradigm"] == row["expected_pid"]
        assert row["target_score"] > row["best_other_score"] * 1.5
    assert len({row["top_token"] for row in confusion.values()}) == 5


def test_phase7_6_sqlite_warmload_parity_matches_continuous_run(tmp_path: Path) -> None:
    sequence = _long_sequence()
    continuous = _run_long_episode(sequence=sequence)
    split = _run_long_episode(sequence=sequence, split_at=600, tmp_path=tmp_path)

    continuous_confusion = _teacher_off_replay(continuous, start_tick=1700)
    split_confusion = _teacher_off_replay(split, start_tick=1700)

    assert _external_summary(split_confusion) == _external_summary(continuous_confusion)
    for key in continuous_confusion:
        assert abs(split_confusion[key]["target_score"] - continuous_confusion[key]["target_score"]) < 1e-9
        assert abs(split_confusion[key]["best_other_score"] - continuous_confusion[key]["best_other_score"]) < 1e-9


def test_phase7_6_runtime_redline_has_no_long_episode_routes() -> None:
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
            "sqlite_runtime_store.py",
        )
    )
    for forbidden in (
        "expr::long_",
        "phase7_6_",
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


def _run_long_episode(
    *,
    sequence: tuple[int, ...] | None = None,
    split_at: int | None = None,
    tmp_path: Path | None = None,
) -> _LongEpisodeHarness:
    seq = sequence or _long_sequence()
    harness = _LongEpisodeHarness()
    for index, kind in enumerate(seq, start=1):
        harness.run_one(kind, index)
        if split_at is not None and index == split_at:
            assert tmp_path is not None
            store = SQLiteRuntimeStore(tmp_path / "phase7_6_runtime.sqlite")
            state_id = store.save_state(harness.snapshot())
            harness = _LongEpisodeHarness(store.load_state(state_id))
    return harness


def _long_sequence() -> tuple[int, ...]:
    rng = random.Random(7306)
    seq: list[int] = []
    seq.extend(index % 5 for index in range(100))
    seq.extend(rng.randrange(0, 4) for _ in range(145))
    while len(seq) < 1200:
        seq.append(rng.randrange(0, 5))
    return tuple(seq)


def _teacher_off_replay(harness: _LongEpisodeHarness, *, start_tick: int) -> dict[str, dict[str, object]]:
    replay = _LongEpisodeHarness(harness.snapshot())
    result: dict[str, dict[str, object]] = {}
    all_tokens = tuple(item.expression_token for item in _canonical_situations())
    for index, facts in enumerate(_canonical_situations()):
        tick = start_tick + index
        replay.state = emit_draft_introspection_feelings(
            replay.state,
            facts.views,
            current_tick=tick,
            paradigm_competition=facts.paradigm_competition,
            recent_punishment_resemblance=facts.recent_punishment_resemblance,
        )
        label = _latest_label(replay.state, tick)
        other_scores = [
            harness.store.similarity(label, token, tick)
            for token in all_tokens
            if token != facts.expression_token
        ]
        result[facts.situation_id] = {
            "label": label,
            "top_token": harness.store.nearest_by_label((label,), top_k=1, current_tick=tick)[0],
            "top_paradigm": harness.store.nearest_paradigms_by_label((label,), top_k=1, current_tick=tick)[0],
            "expected_token": facts.expression_token,
            "expected_pid": facts.expression_pid,
            "target_score": harness.store.similarity(label, facts.expression_token, tick),
            "best_other_score": max(other_scores, default=0.0),
            "observed_external_tokens": (),
        }
    return result


def _canonical_situations() -> tuple[_SituationFacts, ...]:
    return (
        _SituationFacts(
            "dialogue_uncertain",
            (_View("slot", False, 0.0, 0.0, 0.0), _View("shared_fragment", True, 0.9, 1.0, 0.35)),
            "expr::long_dialogue",
            "p:expr:long_dialogue",
        ),
        _SituationFacts(
            "work_memory_unfinished",
            (_View("slot", True, 0.9, 1.0, 0.06), _View("fixed_anchor", True, 0.9, 1.0, 0.06)),
            "expr::long_work_memory",
            "p:expr:long_work_memory",
        ),
        _SituationFacts(
            "teacher_request_pressure",
            (_View("slot", True, 0.8, 1.0, 0.55), _View("fixed_anchor", True, 0.8, 1.0, 0.55)),
            "expr::long_teacher_request",
            "p:expr:long_teacher_request",
            paradigm_competition=1.0,
        ),
        _SituationFacts(
            "recent_punishment",
            (_View("slot", True, 0.8, 1.0, 0.7), _View("fixed_anchor", True, 0.8, 1.0, 0.7)),
            "expr::long_punishment",
            "p:expr:long_punishment",
            recent_punishment_resemblance=1.0,
        ),
        _SituationFacts(
            "rewarded_flow",
            (_View("slot", True, 0.95, 1.0, 0.95), _View("fixed_anchor", True, 0.95, 1.0, 0.95)),
            "expr::long_flow",
            "p:expr:long_flow",
        ),
    )


def _base_state() -> dict[str, object]:
    return {
        "schema_id": "apv3_runtime_ontology_state/v1",
        "online_embedding": {"tokens": {"ctx_idiom": {"vector": [0.0, 1.0], "support": 4.0, "promoted": True}}},
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
                case_name="phase7_6_dialogue_uncertain",
                cue_tokens=(SAN, GU),
                reply_tokens=reply,
                context_tokens=("ctx_idiom",),
                commit_observation=True,
                reward_delta=1.0,
            ),
        ).state
    return state


def _latest_label(state: dict[str, object], tick: int) -> str:
    rows = state.get("introspection_feelings", [])
    if not isinstance(rows, list):
        raise AssertionError("missing introspection feelings")
    for item in reversed(rows):
        if isinstance(item, dict) and int(item.get("tick", -1)) == int(tick):
            return str(item.get("sa_label", ""))
    raise AssertionError(f"missing feeling at tick {tick}")


def _stable_labels(labels: dict[str, list[str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for situation_id, values in labels.items():
        tail = values[-20:]
        label, count = Counter(tail).most_common(1)[0]
        assert count >= 17
        result[situation_id] = label
    return result


def _max_gaps_by_kind(sequence: tuple[int, ...]) -> dict[int, int]:
    last_seen: dict[int, int] = {}
    max_gap = {kind: 0 for kind in range(5)}
    for tick, kind in enumerate(sequence, start=1):
        if kind in last_seen:
            max_gap[kind] = max(max_gap[kind], tick - last_seen[kind])
        last_seen[kind] = tick
    return max_gap


def _external_summary(confusion: dict[str, dict[str, object]]) -> dict[str, tuple[object, object]]:
    return {
        key: (row["top_token"], row["top_paradigm"])
        for key, row in sorted(confusion.items())
    }
