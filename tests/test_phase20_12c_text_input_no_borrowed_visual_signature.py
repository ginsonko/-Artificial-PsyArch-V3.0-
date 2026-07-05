"""Phase20.12c — pure-text input must not borrow a historical visual signature.

Whitepaper §16.1 mandates that a visual signature comes only from THIS tick's
visual receptor input (image / canvas / desktop). Before this fix, runtime.py
borrowed a visual signature from a historical experience window via
`_select_backward_attribution` and assigned it to the current pure-text
observation when the current tick had no image. That borrowed signature then
leaked through three paths at once:

  1. `_find_exact_b0` took the `_find_visual_exact_b0` branch and matched the
     most-recently-taught visual memory (e.g. taught banana -> every later
     pure-text question answered "是香蕉");
  2. `_select_visual_imagination_recall` fired a `visual_imagination_recall`
     tick for a pure-text input;
  3. `_observation_is_visual_reference_family` returned True and relaxed the
     B0 text-match threshold.

This is the whitepaper §269 "最近答案覆盖" failure mode ("如果系统总是说最近
教过的词，那不是 AP"). §1210 allows C_backward to *attribute* "我可能受刚教
香蕉影响" as a cause, but that attribution must NOT become the answer output.

The fix removes the borrow assignment (runtime.py:406-407) while keeping the
`backward_attribution` computation for §1160 C_backward attribution rows
(those use the backward_attribution's own recovered observation, decoupled from
the current observation's visual_signature). No new entity is added.

These tests run on stage6 (enable_visual) — the only stage where the borrow
path was active — and verify:
  (a) the §269 leak is gone (pure-text unknown question requests the teacher,
      not the last-taught visual item);
  (b) the pure-text observation carries no visual_signature;
  (c) no `visual_imagination_recall` tick fires for pure-text input;
  (d) image-input visual teaching still recalls correctly (no regression);
  (e) no over-claiming strings are emitted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apv3test.runtime.phase20_7 import (
    MediaInput,
    TeacherFeedback,
    run_phase20_7_turn,
)


_BANANA_IMAGE = "data/phase20_workbench_media/真实香蕉4_c2888e348a25d03b.webp"
_APPLE_IMAGE = "data/phase20_workbench_media/真实苹果2_2bf246de034bf5c4.jpg"


def _teach_visual_item(
    db_path: Path,
    *,
    image_path: str,
    question: str,
    answer: str,
    session_id: str = "phase20-12c",
) -> None:
    run_phase20_7_turn(
        user_text=question,
        media_inputs=(MediaInput(media_type="image", path=image_path),),
        teacher_feedback=TeacherFeedback(feedback_text=answer, reward_mag=1.0),
        session_id=session_id,
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )


def _observation_visual_signature(result: Any) -> str | None:
    for event in result.tick_trace:
        if event.selected_action.get("action_type") != "observe_text":
            continue
        for query in event.query_structures:
            sig = query.get("visual_signature") if isinstance(query, dict) else None
            if sig:
                return str(sig)
        # No visual signature on any query_structure of the observe_text tick.
        return None
    return None


def _has_visual_imagination_recall(result: Any) -> bool:
    return any(
        event.selected_action.get("action_type") == "visual_imagination_recall"
        for event in result.tick_trace
    )


# ---------------------------------------------------------------------------
# 1. The §269 leak is gone: after teaching banana via image, a pure-text
#    question that was never taught ("你是谁?") must NOT answer "是香蕉".
#    It must request the teacher and reply with the unknown-reply.
# ---------------------------------------------------------------------------
def test_phase20_12c_pure_text_unknown_question_requests_teacher_not_last_visual(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "phase20_12c.sqlite"
    _teach_visual_item(
        db_path,
        image_path=_BANANA_IMAGE,
        question="这是什么?",
        answer="是香蕉",
    )

    result = run_phase20_7_turn(
        user_text="你是谁?",
        session_id="phase20-12c",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    # The defining assertion: a never-taught pure-text question must NOT echo
    # the most-recently-taught visual item. This is the §269 "最近答案覆盖"
    # red line.
    assert result.reply_text != "是香蕉", (
        "pure-text '你是谁?' leaked the last-taught visual answer '是香蕉' "
        "(§269 最近答案覆盖 regression)"
    )
    assert result.reply_text == "不太会,教教"
    assert any(
        event.selected_action.get("action_type") == "request_teacher"
        for event in result.tick_trace
    ), "pure-text unknown question did not request the teacher"


# ---------------------------------------------------------------------------
# 2. The pure-text observation carries no visual_signature (§16.1: visual
#    signature comes only from THIS tick's visual receptor input).
# ---------------------------------------------------------------------------
def test_phase20_12c_pure_text_observation_has_no_visual_signature(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "phase20_12c.sqlite"
    _teach_visual_item(
        db_path,
        image_path=_BANANA_IMAGE,
        question="这是什么?",
        answer="是香蕉",
    )

    result = run_phase20_7_turn(
        user_text="你是谁?",
        session_id="phase20-12c",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    sig = _observation_visual_signature(result)
    assert sig is None, (
        f"pure-text observation borrowed a visual signature from history: {sig!r} "
        "(§16.1 violation: visual signature must come from this tick's receptor)"
    )


# ---------------------------------------------------------------------------
# 3. No `visual_imagination_recall` tick fires for a pure-text input. Before
#    the fix, the borrowed signature made `_select_visual_imagination_recall`
#    fire an imagination tick for "你是谁?".
# ---------------------------------------------------------------------------
def test_phase20_12c_pure_text_does_not_fire_visual_imagination_recall(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "phase20_12c.sqlite"
    _teach_visual_item(
        db_path,
        image_path=_BANANA_IMAGE,
        question="这是什么?",
        answer="是香蕉",
    )

    result = run_phase20_7_turn(
        user_text="你是谁?",
        session_id="phase20-12c",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    assert not _has_visual_imagination_recall(result), (
        "visual_imagination_recall fired for a pure-text input with no image "
        "(caused by a borrowed visual signature)"
    )


# ---------------------------------------------------------------------------
# 4. No regression on image-input visual teaching: asking a question WITH the
#    taught image still recalls the taught answer via the visual B0 path. The
#    fix only removes the borrow for pure-text (no-image) inputs; the
#    image-input path uses `_visual_signature_from_events` (this tick's
#    receptor) and is untouched.
# ---------------------------------------------------------------------------
def test_phase20_12c_image_input_visual_recall_still_works(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_12c.sqlite"
    _teach_visual_item(
        db_path,
        image_path=_BANANA_IMAGE,
        question="这是什么?",
        answer="是香蕉",
    )

    # Re-ask with the SAME image, no teacher feedback. The visual B0 path
    # should recall "是香蕉" from the just-taught visual alignment.
    result = run_phase20_7_turn(
        user_text="这呢?",
        media_inputs=(MediaInput(media_type="image", path=_BANANA_IMAGE),),
        session_id="phase20-12c",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    assert result.reply_text == "是香蕉", (
        f"image-input visual recall regressed: expected '是香蕉', got "
        f"{result.reply_text!r}"
    )
    # The image-input observation MUST still carry a visual signature (from
    # this tick's receptor, not borrowed).
    sig = _observation_visual_signature(result)
    assert sig is not None, "image-input observation lost its visual signature"


# ---------------------------------------------------------------------------
# 5. No over-claiming: the serialized turn must not emit forbidden convergence
#    / completion strings.
# ---------------------------------------------------------------------------
def test_phase20_12c_runtime_does_not_claim_visual_convergence(tmp_path: Path) -> None:
    db_path = tmp_path / "phase20_12c.sqlite"
    _teach_visual_item(
        db_path,
        image_path=_BANANA_IMAGE,
        question="这是什么?",
        answer="是香蕉",
    )

    result = run_phase20_7_turn(
        user_text="你是谁?",
        session_id="phase20-12c",
        db_path=db_path,
        post_commit_idle_ticks=0,
        runtime_stage="stage6",
    )

    serialized = json.dumps(result.to_dict(), ensure_ascii=False)
    for forbidden in (
        "l1_l2_l3_complete",
        "six_stage_learning_complete",
        "online_embedding_converged",
        "l1_vector_converged",
        "l2_vector_converged",
        "visual_embedding_converged",
    ):
        assert forbidden not in serialized, f"forbidden completion string: {forbidden}"
