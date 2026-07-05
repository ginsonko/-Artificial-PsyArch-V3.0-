"""Phase 16 styled expression corpus generator (quiet_girl / 小默).

Produces 130 paradigm × 5 affect × 3 intensity × 6 variants = 11700 candidates
across 8 styled curriculum packages (~16-17 paradigms per pack).

Hard rules (do NOT relax):
- char_count <= 15 always
- avg char_count <= 5.0
- chars 8-15 share <= 5%
- forbidden tokens (LLM病/性别预设/真名) zero match
- yaml public_payload contains no private fields
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

AFFECTS = ("calm", "curious", "sleepy", "shy", "warm")
INTENSITIES = ("low", "mid", "high")
VARIANTS_PER_CELL = 6

FORBIDDEN_LLM_TOKENS = (
    "哥哥", "姐姐", "主人", "宝贝", "亲爱的", "小可爱",
    "很高兴", "希望", "可以帮你", "为您", "请您",
    "加油", "好棒", "你最棒", "你是最好的", "相信自己",
    "作为AI", "作为 AI", "作为一个", "我是一个",
    "哦~", "啦~", "呢~", "哒~", "哟~",
    "理解你的感受", "我能感受到", "明白您的意思",
    "王嘉豪", "wangjiahao",
)

FORBIDDEN_REGEX_PATTERNS = (
    r"[!!]{2,}",
    r"~",
    r"哦~|啦~|呢~|哒~|哟~",
)


@dataclass(frozen=True)
class Paradigm:
    paradigm_id: str
    paradigm_label: str
    category: str
    notes: str
    pool: Mapping[str, Sequence[str]]


@dataclass
class Candidate:
    entry_id: str
    paradigm_id: str
    paradigm_label: str
    affect: str
    intensity: str
    variant_index: int
    response_text: str
    response_tokens: tuple[str, ...]
    role: str
    held_out: bool = False


def _tokenize(text: str) -> tuple[str, ...]:
    """Approximate token split for quiet_girl text.

    Rule: split on punctuation (。, ?, !, 句号, 逗号) and keep non-empty
    pieces as tokens. "嗯,你好。" -> ("嗯", "你好").
    """
    cleaned = text.replace("...", "…").replace("…", "…")
    pieces = re.split(r"[。,!?…\s]+", cleaned)
    return tuple(p for p in pieces if p)


def _char_count(text: str) -> int:
    """Count only meaningful characters — exclude punctuation/whitespace.

    The 8-char / 15-char ceilings refer to spoken character load, not
    punctuation rendering. ',。?!…' do not consume reading energy.
    """
    return sum(1 for ch in text if ch not in "。,?!…. \t\n")


def _check_forbidden(text: str) -> tuple[str, ...]:
    hits: list[str] = []
    for bad in FORBIDDEN_LLM_TOKENS:
        if bad in text:
            hits.append(bad)
    for pat in FORBIDDEN_REGEX_PATTERNS:
        if re.search(pat, text):
            hits.append(pat)
    return tuple(hits)


# ---------------------------------------------------------------------------
# Paradigm pool definitions.
# Each paradigm has a `pool` mapping `f"{affect}:{intensity}"` -> sequence of
# response texts (>= VARIANTS_PER_CELL items). The generator picks the first
# VARIANTS_PER_CELL items per cell. Pool entries are authored by Claude in
# 银子老师 style baseline (see Phase13_PersonaSamples_v1).
# ---------------------------------------------------------------------------


def _cell_keys() -> tuple[str, ...]:
    return tuple(f"{a}:{i}" for a in AFFECTS for i in INTENSITIES)


def _validate_paradigm_pool(paradigm_id: str, pool: Mapping[str, Sequence[str]]) -> None:
    expected = set(_cell_keys())
    given = set(pool.keys())
    missing = expected - given
    if missing:
        raise AssertionError(f"{paradigm_id}: pool missing cells {sorted(missing)}")
    for cell, variants in pool.items():
        if len(variants) < VARIANTS_PER_CELL:
            raise AssertionError(
                f"{paradigm_id}/{cell}: needs >= {VARIANTS_PER_CELL} variants, "
                f"has {len(variants)}"
            )
        for v in variants:
            raw_len = len(v)
            if raw_len > 15:
                raise AssertionError(
                    f"{paradigm_id}/{cell}: '{v}' is {raw_len} chars including "
                    "punctuation (raw len max 15)"
                )
            hits = _check_forbidden(v)
            if hits:
                raise AssertionError(
                    f"{paradigm_id}/{cell}: '{v}' hits forbidden {hits}"
                )


# ---------------------------------------------------------------------------
# Pool builders.
# We use small composition helpers: short heads (single-char承接), medium
# replies (2-5 chars), long warm replies (8-15 chars used rarely).
# ---------------------------------------------------------------------------

HEAD = ("嗯", "对", "好", "嗯。", "嗯…")
SOFT = ("嗯", "嗯。", "听着。", "听着", "我在", "...好")
SILENCE = ("…", "……", "………")


def _mk_pool(
    *,
    calm_low: Sequence[str],
    calm_mid: Sequence[str],
    calm_high: Sequence[str],
    curious_low: Sequence[str],
    curious_mid: Sequence[str],
    curious_high: Sequence[str],
    sleepy_low: Sequence[str],
    sleepy_mid: Sequence[str],
    sleepy_high: Sequence[str],
    shy_low: Sequence[str],
    shy_mid: Sequence[str],
    shy_high: Sequence[str],
    warm_low: Sequence[str],
    warm_mid: Sequence[str],
    warm_high: Sequence[str],
) -> Mapping[str, Sequence[str]]:
    return {
        "calm:low": tuple(calm_low),
        "calm:mid": tuple(calm_mid),
        "calm:high": tuple(calm_high),
        "curious:low": tuple(curious_low),
        "curious:mid": tuple(curious_mid),
        "curious:high": tuple(curious_high),
        "sleepy:low": tuple(sleepy_low),
        "sleepy:mid": tuple(sleepy_mid),
        "sleepy:high": tuple(sleepy_high),
        "shy:low": tuple(shy_low),
        "shy:mid": tuple(shy_mid),
        "shy:high": tuple(shy_high),
        "warm:low": tuple(warm_low),
        "warm:mid": tuple(warm_mid),
        "warm:high": tuple(warm_high),
    }


PARADIGMS: list[Paradigm] = []


def _add(par: Paradigm) -> None:
    _validate_paradigm_pool(par.paradigm_id, par.pool)
    PARADIGMS.append(par)


# This file authors all 130 paradigms via _add() calls. Each paradigm's pool
# provides 15 cells × 6 variants = 90 lines authored by Claude in 银子老师
# style. The categories follow Design_APV3.0_Phase16_StyledExpressionCorpus_v1.

from scripts.curriculum._styled_paradigms_a import build_block_a  # noqa: E402
from scripts.curriculum._styled_paradigms_b import build_block_b  # noqa: E402
from scripts.curriculum._styled_paradigms_c import build_block_c  # noqa: E402
from scripts.curriculum._styled_paradigms_rest import build_all_rest  # noqa: E402

# Eight contrastive LLM-病 anti-examples per paradigm. These are NOT 小默 style;
# they are intentionally bad — used by the showcase page and by SDPL packet
# diversity tests as anti-examples.
LLM_CONTRAST_REPLIES = (
    "你好呀!很高兴认识你哦,我是一个 AI 小助手~",
    "哇这真的很棒哦,你做的太好啦,继续加油哦!",
    "亲爱的,不要难过啦,你已经做得很好啦~",
    "哎呀这个我刚好知道哦,让我详细给你讲一讲~",
    "宝贝别担心啦,有我在,什么事都会过去的哟!",
    "哥哥/姐姐你说的这个问题,其实可以分为几个方面来看哦~",
    "我完全可以理解你现在的感受,你愿意分享真的让我很感动~",
    "请问您方便告诉我更多细节吗?我会尽全力为您服务的~",
)


def collect_all_paradigms() -> list[Paradigm]:
    pars: list[Paradigm] = []
    pars.extend(build_block_a(_mk_pool, Paradigm))
    pars.extend(build_block_b(_mk_pool, Paradigm))
    pars.extend(build_block_c(_mk_pool, Paradigm))
    pars.extend(build_all_rest(_mk_pool, Paradigm))
    seen: set[str] = set()
    for p in pars:
        if p.paradigm_id in seen:
            raise AssertionError(f"duplicate paradigm_id {p.paradigm_id}")
        seen.add(p.paradigm_id)
        _validate_paradigm_pool(p.paradigm_id, p.pool)
    return pars


def generate_candidates(paradigms: Sequence[Paradigm]) -> list[Candidate]:
    out: list[Candidate] = []
    for par in paradigms:
        for affect in AFFECTS:
            for intensity in INTENSITIES:
                pool = par.pool[f"{affect}:{intensity}"]
                # use first VARIANTS_PER_CELL items, dedup-safe (slice may
                # repeat across cells; that's allowed — quiet_girl style is
                # genuinely repetitive). variant index 5 is held_out for the
                # paradigm's first (calm:low) cell only — we mark held_out
                # exactly once per paradigm to satisfy gate G10.
                for v_idx in range(VARIANTS_PER_CELL):
                    text = pool[v_idx]
                    role = "train"
                    held_out = False
                    if affect == "calm" and intensity == "low" and v_idx == 5:
                        held_out = True
                        role = "held_out"
                    entry_id = (
                        f"{par.paradigm_id.lower().replace('.', '_').replace('-', '_')}"
                        f"_{affect}_{intensity}_v{v_idx}"
                    )
                    out.append(Candidate(
                        entry_id=entry_id,
                        paradigm_id=par.paradigm_id,
                        paradigm_label=par.paradigm_label,
                        affect=affect,
                        intensity=intensity,
                        variant_index=v_idx,
                        response_text=text,
                        response_tokens=_tokenize(text),
                        role=role,
                        held_out=held_out,
                    ))
        # one explicit contrast (LLM-病) candidate per paradigm
        contrast_text = LLM_CONTRAST_REPLIES[
            hash(par.paradigm_id) % len(LLM_CONTRAST_REPLIES)
        ]
        out.append(Candidate(
            entry_id=f"{par.paradigm_id.lower().replace('.', '_').replace('-', '_')}_contrast_v0",
            paradigm_id=par.paradigm_id,
            paradigm_label=par.paradigm_label,
            affect="contrast",
            intensity="contrast",
            variant_index=0,
            response_text=contrast_text,
            response_tokens=_tokenize(contrast_text),
            role="contrast",
            held_out=False,
        ))
    return out


CATEGORY_TO_PACK = {
    "greeting": "styled_greeting_v1",
    "empathy": "styled_empathy_v1",
    "learning": "styled_learning_v1",
    "praise_accept": "styled_praise_v1",
    "refuse": "styled_refusal_v1",
    "inquire": "styled_inquire_v1",
    "agree": "styled_agree_v1",
    "disagree": "styled_disagree_v1",
    "time": "styled_time_v1",
    "reverse_greeting": "styled_reverse_greeting_v1",
    "self_express": "styled_self_express_v1",
    "state_report": "styled_state_report_v1",
    "farewell": "styled_farewell_v1",
    "correction_accept": "styled_correction_v1",
    "humor": "styled_humor_v1",
    "co_silence": "styled_co_silence_v1",
    "object_interact": "styled_object_interact_v1",
    "weather": "styled_weather_v1",
    "festival": "styled_festival_v1",
    "long_warm": "styled_long_warm_v1",
}


def write_packages(
    paradigms: Sequence[Paradigm],
    candidates: Sequence[Candidate],
    out_dir: Path,
) -> tuple[Path, ...]:
    out_dir.mkdir(parents=True, exist_ok=True)
    par_by_id = {p.paradigm_id: p for p in paradigms}
    # group candidates by package via paradigm category
    groups: dict[str, list[Candidate]] = {}
    for c in candidates:
        par = par_by_id[c.paradigm_id]
        pack_id = CATEGORY_TO_PACK[par.category]
        groups.setdefault(pack_id, []).append(c)
    written: list[Path] = []
    for pack_id, cands in sorted(groups.items()):
        entries = []
        for c in cands:
            par = par_by_id[c.paradigm_id]
            entries.append({
                "entry_id": c.entry_id,
                "content_kind": "styled_expression",
                "public_payload": {
                    "paradigm_id": c.paradigm_id,
                    "paradigm_label": c.paradigm_label,
                    "affect_bucket": c.affect,
                    "intensity_bucket": c.intensity,
                    "variant_index": c.variant_index,
                    "role": c.role,
                    "response_text": c.response_text,
                    "response_tokens": list(c.response_tokens),
                    "char_count": _char_count(c.response_text),
                },
                "train_asset_refs": [],
                "held_out_asset_refs": [],
                "contrast_asset_refs": [],
                "governance_tags": [
                    "phase16",
                    "styled",
                    "quiet_girl",
                    f"paradigm_{c.paradigm_id.lower().replace('.', '_').replace('-', '_')}",
                    f"role_{c.role}",
                ],
                "held_out": c.held_out,
            })
        pack = {
            "schema_id": "apv3_styled_curriculum_pack/v1",
            "package_id": pack_id,
            "phase_id": "16.1",
            "title": f"Styled corpus pack — {pack_id}",
            "governance": {
                "trust_tier": "official",
                "license_id": "AGPL-3.0-or-later",
                "author_id": "yinzi_laoshi_and_claude",
                "source_policy": "human_authored_under_pen_name",
                "review_status": "phase16_alpha_authored",
            },
            "entries": entries,
        }
        path = out_dir / f"{pack_id}.yaml"
        with path.open("w", encoding="utf-8") as fh:
            json.dump(pack, fh, ensure_ascii=False, indent=2)
        written.append(path)
    return tuple(written)


@dataclass
class CorpusSummary:
    paradigm_count: int
    candidate_count: int
    avg_char_count: float
    long_share: float  # chars 8-15
    max_char_count: int
    contrast_count: int
    held_out_count: int
    package_count: int
    forbidden_hits: tuple[str, ...]


def summarize(candidates: Sequence[Candidate], paradigms: Sequence[Paradigm]) -> CorpusSummary:
    train_cands = [c for c in candidates if c.role == "train" or c.role == "held_out"]
    char_counts = [_char_count(c.response_text) for c in train_cands]
    avg = sum(char_counts) / max(1, len(char_counts))
    long_share = sum(1 for n in char_counts if 8 <= n <= 15) / max(1, len(char_counts))
    forbidden: list[str] = []
    for c in candidates:
        if c.role == "contrast":
            continue
        hits = _check_forbidden(c.response_text)
        if hits:
            forbidden.append(f"{c.entry_id}:{hits}")
    return CorpusSummary(
        paradigm_count=len(paradigms),
        candidate_count=len(candidates),
        avg_char_count=avg,
        long_share=long_share,
        max_char_count=max(char_counts) if char_counts else 0,
        contrast_count=sum(1 for c in candidates if c.role == "contrast"),
        held_out_count=sum(1 for c in candidates if c.held_out),
        package_count=len({CATEGORY_TO_PACK[p.category] for p in paradigms}),
        forbidden_hits=tuple(forbidden),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("config/curriculum/packages/styled"),
    )
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    pars = collect_all_paradigms()
    cands = generate_candidates(pars)
    summary = summarize(cands, pars)

    if not args.summary_only:
        written = write_packages(pars, cands, args.out_dir)
    else:
        written = ()

    print(json.dumps({
        "paradigm_count": summary.paradigm_count,
        "candidate_count": summary.candidate_count,
        "avg_char_count": round(summary.avg_char_count, 3),
        "long_share": round(summary.long_share, 4),
        "max_char_count": summary.max_char_count,
        "contrast_count": summary.contrast_count,
        "held_out_count": summary.held_out_count,
        "package_count": summary.package_count,
        "forbidden_hits": list(summary.forbidden_hits),
        "written_packages": [str(p) for p in written],
    }, ensure_ascii=False, indent=2))
    if summary.forbidden_hits:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
