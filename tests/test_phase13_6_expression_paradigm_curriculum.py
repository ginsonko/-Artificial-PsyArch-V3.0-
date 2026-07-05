from __future__ import annotations

import subprocess
import sys

from runtime.cognitive.curriculum.expression_paradigm import ExpressionCandidate, validate_quiet_expression_corpus


def _quiet_candidates() -> tuple[ExpressionCandidate, ...]:
    texts = (
        ("嗯",),
        ("好",),
        ("可以",),
        ("试试",),
        ("不确定",),
        ("再说",),
        ("我看看",),
        ("慢点",),
        ("知道了",),
        ("不像",),
        ("有点难",),
        ("再来",),
        ("别急",),
        ("可能",),
        ("像这样",),
        ("等下",),
        ("我记得",),
        ("没懂",),
        ("学一下",),
        ("这样吗",),
    )
    return tuple(ExpressionCandidate(candidate_id=f"expr::{index}", tokens=tokens) for index, tokens in enumerate(texts))


def test_phase13_6_quiet_expression_corpus_accepts_short_minimalist_candidates() -> None:
    trace = validate_quiet_expression_corpus(_quiet_candidates())

    assert trace.accepted is True
    assert trace.candidate_count >= 20
    assert trace.long_reply_ratio == 0.0


def test_phase13_6_expression_corpus_rejects_long_macro_sentence() -> None:
    bad = _quiet_candidates() + (
        ExpressionCandidate(candidate_id="expr::long", tokens=("我", "现在", "完全", "理解", "你的", "意思")),
    )
    trace = validate_quiet_expression_corpus(bad)

    assert trace.accepted is False
    assert "expr::long" in trace.rejected_ids


def test_phase13_6_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "13.6"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr

