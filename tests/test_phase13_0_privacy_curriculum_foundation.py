from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from apv3test.chat import APV3MinimalistChatSession
from apv3test.runtime import load_runtime_profile
from apv3test.util.pseudonymous_id import _canonicalize_input, compute_pseudonymous_identifier
from apv3test.web_chat import APV3WebChatApp
from runtime.cognitive.curriculum import (
    EvaluatorMetadata,
    HeldOutEventPool,
    PromotionEvidence,
    PublicHeldOutEvent,
    spawn_pending_perceived_revalidation,
    trust_promote_gate,
)
from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.sdpl.packet import make_packet
from runtime.cognitive.state_pool.state_pool import StateItem


def _redline_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "red_line_check_v14.py"
    spec = importlib.util.spec_from_file_location("red_line_check_v14", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _item(
    sa_id: str,
    *,
    cognitive_content: object | None = None,
    metadata: dict[str, object] | None = None,
) -> StateItem:
    payload = dict(metadata or {})
    if cognitive_content is not None:
        payload["cognitive_content"] = cognitive_content
    return StateItem(
        sa_id=sa_id,
        family="percept",
        label="raw_sensor",
        real_energy=0.8,
        cognitive_pressure=0.3,
        channel_signature=("vision",),
        source="sensor",
        metadata=payload,
    )


def _perceived(target: str) -> MarkerEvent:
    return MarkerEvent(tick=1, kind="PERCEIVED", target_sa_id=target, real_energy=0.8)


def test_phase13_0_pseudonymous_identifier_uses_canonical_hmac(tmp_path: Path) -> None:
    tuple_id = compute_pseudonymous_identifier(("你好", "在吗"), state_dir=tmp_path)
    list_id = compute_pseudonymous_identifier(["你好", "在吗"], state_dir=tmp_path)
    scalar_id = compute_pseudonymous_identifier("你好", state_dir=tmp_path)
    singleton_id = compute_pseudonymous_identifier(["你好"], state_dir=tmp_path)
    naive = hashlib.sha256(_canonicalize_input(("你好", "在吗")).encode("utf-8")).hexdigest()[:32]

    assert tuple_id == list_id
    assert scalar_id != singleton_id
    assert tuple_id != naive
    assert len(tuple_id) == 32
    assert "\\u" not in _canonicalize_input("你好")
    with pytest.raises(TypeError):
        compute_pseudonymous_identifier(("ok", 3), state_dir=tmp_path)  # type: ignore[arg-type]


def test_phase13_0_default_chat_and_web_do_not_persist_raw_user_text(tmp_path: Path) -> None:
    canary = "PHASE13_RAW_CANARY_不要进入状态"
    db_path = tmp_path / "chat.sqlite"
    session = APV3MinimalistChatSession(
        profile=load_runtime_profile(sqlite_state_path=db_path),
        autoload=False,
    )
    turn = session.say(canary)
    saved = session.store.load_state(turn.state_id)
    serialized = json.dumps(saved, ensure_ascii=False, sort_keys=True)
    latest_chat = saved["chat_session_trace"][-1]
    latest_runtime = saved["minimalist_dialogue_trace"][-1]

    assert canary not in serialized
    assert latest_chat["user_text"] is None
    assert latest_chat["user_text_hash"]
    assert latest_chat["user_text_length"] == len(canary)
    assert "incoming_external_query" not in latest_runtime
    assert latest_runtime["incoming_query_hash"] == latest_chat["incoming_query_hash"]

    web = APV3WebChatApp(state_db_path=tmp_path / "web.sqlite")
    payload = web.send({"text": canary, "mode": "uncertain"})
    web_serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    assert canary not in web_serialized
    assert payload["turn"]["user_text"] is None


def test_phase13_0_explicit_opt_in_is_required_for_raw_text_persistence(tmp_path: Path) -> None:
    canary = "PHASE13_OPT_IN_CANARY"
    session = APV3MinimalistChatSession(
        profile=load_runtime_profile(sqlite_state_path=tmp_path / "optin.sqlite"),
        autoload=False,
        persist_user_text=True,
    )
    turn = session.say(canary)
    saved = session.store.load_state(turn.state_id)

    assert saved["chat_session_trace"][-1]["user_text"] == canary
    assert turn.user_text_persisted is True


def test_phase13_0_held_out_private_handle_never_enters_public_ap_state() -> None:
    pool = HeldOutEventPool()
    public_a = PublicHeldOutEvent(
        content_sas=(_item("percept::opaque_a", cognitive_content={"shape": "same_cat"}),),
        source_markers=(_perceived("percept::opaque_a"),),
    )
    public_b = PublicHeldOutEvent(
        content_sas=(_item("percept::opaque_b", cognitive_content={"shape": "same_cat"}),),
        source_markers=(_perceived("percept::opaque_b"),),
    )
    handle_a = pool.reserve(public_a, EvaluatorMetadata(target_class="episode_a"))
    handle_b = pool.reserve(public_b, EvaluatorMetadata(target_class="episode_b"))
    batch = pool.sample_evaluation_batch(2)
    public_state = json.dumps(pool.export_public_state(), ensure_ascii=False, sort_keys=True)

    assert handle_a.handle_id != handle_b.handle_id
    assert len({pair.private_handle.handle_id for pair in batch}) == 2
    assert handle_a.handle_id not in public_state
    assert handle_b.handle_id not in public_state
    assert "episode_a" not in public_state
    assert "episode_b" not in public_state


def test_phase13_0_held_out_rejects_labeled_or_non_perceived_public_events() -> None:
    pool = HeldOutEventPool()
    with pytest.raises(ValueError):
        pool.reserve(
            PublicHeldOutEvent(
                content_sas=(_item("percept::labeled", metadata={"vocab_label": "cat"}),),
                source_markers=(_perceived("percept::labeled"),),
            ),
            EvaluatorMetadata(target_class="cat"),
        )
    with pytest.raises(ValueError):
        pool.reserve(
            PublicHeldOutEvent(
                content_sas=(_item("percept::hearsay"),),
                source_markers=(MarkerEvent(tick=1, kind="HEARSAY", target_sa_id="percept::hearsay", real_energy=0.8),),
            ),
            EvaluatorMetadata(target_class="cat"),
        )


def test_phase13_0_trust_gate_cannot_soften_effect_size_floor_or_training_only_effect() -> None:
    low_effect = trust_promote_gate(
        PromotionEvidence(
            effect_size=0.025,
            p_value=0.001,
            held_out_observations=100,
            effect_source="held_out_cold_fork",
        ),
        trust_score=1.0,
    )
    training_only = trust_promote_gate(
        PromotionEvidence(
            effect_size=0.20,
            p_value=0.001,
            held_out_observations=100,
            effect_source="training_episode",
            training_effect_size=0.20,
        ),
        trust_score=1.0,
    )
    high_trust = trust_promote_gate(
        PromotionEvidence(
            effect_size=0.04,
            p_value=0.08,
            held_out_observations=5,
            effect_source="held_out_cold_fork",
        ),
        trust_score=1.0,
    )
    low_trust = trust_promote_gate(
        PromotionEvidence(
            effect_size=0.04,
            p_value=0.08,
            held_out_observations=5,
            effect_source="held_out_cold_fork",
        ),
        trust_score=0.0,
    )

    assert low_effect.passed is False
    assert low_effect.status == "reject_effect_size_below_hard_floor"
    assert training_only.passed is False
    assert training_only.status == "reject_effect_source_not_held_out"
    assert high_trust.passed is True
    assert low_trust.passed is False


def test_phase13_0_correction_status_is_string_enum_not_new_marker_kind() -> None:
    resolution = spawn_pending_perceived_revalidation(target_sa_id="sa::conflict", tick=9, energy=0.6)
    mapping = Path("config/family_to_type_mapping.yaml").read_text(encoding="utf-8")

    assert resolution.status == "pending_perceived_revalidation"
    assert "PENDING_PERCEIVED_REVALIDATION" not in mapping
    assert "CORRECTION" in mapping
    assert isinstance(resolution.status, str)


def test_phase13_0_sdpl_packet_key_uses_cognitive_content_not_opaque_sa_id_or_status() -> None:
    a = _item(
        "percept::draft::absolute_3_5_a",
        cognitive_content={"char": "7", "rel_dr": "same", "rel_dc": "same"},
        metadata={"status": "pending_perceived_revalidation"},
    )
    b = _item(
        "percept::draft::absolute_9_1_b",
        cognitive_content={"char": "7", "rel_dr": "same", "rel_dc": "same"},
    )
    packet_a = make_packet(content_sas=(a,))
    packet_b = make_packet(content_sas=(b,))
    key_text = str(packet_a.packet_key())

    assert packet_a.content_key() == packet_b.content_key()
    assert "absolute_3_5" not in key_text
    assert "pending_perceived_revalidation" not in key_text


def test_phase13_0_redline_blocks_metadata_context_status_and_bool_routes() -> None:
    redline = _redline_module()

    assert redline.check_no_design_metadata_routing_from_source("value = table[style_tag]")
    assert redline.check_no_design_metadata_routing_from_source("value = getattr(obj, 'style_tag')")
    assert redline.check_no_context_tokens_literal_branching_from_source(
        "def f(episode):\n    if 'math_context' in episode.context_tokens:\n        return 1\n"
    )
    assert not redline.check_no_context_tokens_literal_branching_from_source(
        "def f(episode, learned_vec):\n    return similarity(episode.context_tokens, learned_vec)\n"
    )
    assert redline.check_no_status_metadata_access_from_source(
        "def f(marker):\n    return marker.metadata.get('status')\n"
    )
    assert redline.check_no_trust_pending_bool_fields_from_source(
        "from dataclasses import dataclass\n@dataclass\nclass X:\n    trust_promoted_pending_perceived: bool = False\n"
    )


def test_phase13_0_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "13.0"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "OK: Phase 13.0 deliverables present" in completed.stdout
