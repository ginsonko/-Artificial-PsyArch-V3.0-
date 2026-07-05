from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


STYLE_FORBIDDEN_TOKENS: frozenset[str] = frozenset(
    {
        "非常",
        "特别",
        "真的",
        "实在",
        "其实",
        "那么",
        "然而",
        "但是",
        "不过",
        "因为",
        "所以",
        "于是",
        "因此",
        "我觉得",
        "我认为",
        "我想说",
        "我的意思是",
        "也就是说",
        "你能",
        "你应该",
        "你可以",
        "你需要",
        "请你",
        "作为",
        "由于",
        "鉴于",
        "请允许我",
    }
)

HONEST_FALLBACK_TOKENS: tuple[str, ...] = ("不知道",)


@dataclass(frozen=True)
class StyleComplianceResult:
    ok: bool
    reason: str = ""
    fallback_tokens: tuple[str, ...] = HONEST_FALLBACK_TOKENS


def check_style_compliance(tokens: Sequence[str], *, max_tokens: int = 3) -> StyleComplianceResult:
    phrase = "".join(str(token) for token in tokens)
    if len(tuple(tokens)) > int(max_tokens):
        return StyleComplianceResult(False, "token_count_exceeded")
    if "!" in phrase or "！" in phrase:
        return StyleComplianceResult(False, "exclamation_forbidden")
    if "??" in phrase or "？？" in phrase:
        return StyleComplianceResult(False, "question_repetition_forbidden")
    for forbidden in STYLE_FORBIDDEN_TOKENS:
        if forbidden in phrase:
            return StyleComplianceResult(False, f"forbidden:{forbidden}")
    return StyleComplianceResult(True)


def style_safe_tokens(tokens: Sequence[str], *, max_tokens: int = 3) -> tuple[str, ...]:
    result = check_style_compliance(tokens, max_tokens=max_tokens)
    if result.ok:
        return tuple(str(token) for token in tokens)
    return result.fallback_tokens


def assert_style_compliant(tokens: Sequence[str], *, max_tokens: int = 3) -> None:
    result = check_style_compliance(tokens, max_tokens=max_tokens)
    if not result.ok:
        raise AssertionError(result.reason)
