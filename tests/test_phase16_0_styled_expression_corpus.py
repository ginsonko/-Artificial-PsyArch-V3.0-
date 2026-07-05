from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from runtime.cognitive.curriculum.package_schema import (
    load_curriculum_package,
    validate_curriculum_package,
)
from runtime.cognitive.curriculum.asset_governance import load_neutral_curriculum_pack_file
from runtime.cognitive.state_pool.state_pool import load_constant


PACKAGE_ROOT = Path("config/curriculum/packages/styled")
GENERATOR = Path("scripts/curriculum/generate_styled_corpus.py")
DESIGN_DOC = Path("docs/Design_APV3.0_Phase16_StyledExpressionCorpus_v1_20260618.md")
REPO_ROOT = Path(".")

FORBIDDEN_LLM_TOKENS = (
    "哥哥", "姐姐", "主人", "宝贝", "亲爱的", "小可爱",
    "很高兴", "希望", "可以帮你", "为您", "请您",
    "加油", "好棒", "你最棒", "你是最好的", "相信自己",
    "作为AI", "作为 AI", "作为一个", "我是一个",
    "理解你的感受", "我能感受到", "明白您的意思",
    "王嘉豪", "wangjiahao",
)


def _styled_packages() -> list[dict[str, object]]:
    return [dict(load_neutral_curriculum_pack_file(p)) for p in sorted(PACKAGE_ROOT.glob("*.yaml"))]


def _all_entries(packages):
    for p in packages:
        for entry in p["entries"]:
            yield p, entry


def _payload(entry):
    return entry.get("public_payload", {})


def _is_train_or_held_out(entry):
    role = _payload(entry).get("role", "train")
    return role in ("train", "held_out")


def _meaningful_char_count(text: str) -> int:
    return sum(1 for ch in text if ch not in "。,?!…. \t\n")


# --- G1 / G2 / G3 ---------------------------------------------------------

def test_phase16_0_paradigm_coverage_meets_design_floor() -> None:
    packages = _styled_packages()
    paradigm_ids = {
        _payload(entry)["paradigm_id"]
        for _, entry in _all_entries(packages)
    }
    floor = int(load_constant("curriculum.styled_corpus.paradigm_count_min"))
    assert len(paradigm_ids) >= floor, (
        f"paradigm coverage {len(paradigm_ids)} below floor {floor}"
    )


def test_phase16_0_candidates_per_paradigm_meet_floor() -> None:
    packages = _styled_packages()
    by_par: dict[str, list] = {}
    for _, entry in _all_entries(packages):
        if _is_train_or_held_out(entry):
            by_par.setdefault(_payload(entry)["paradigm_id"], []).append(entry)
    floor = int(load_constant("curriculum.styled_corpus.candidates_per_paradigm_min"))
    short = {pid: len(items) for pid, items in by_par.items() if len(items) < floor}
    assert not short, f"paradigms below per-paradigm floor {floor}: {short}"


def test_phase16_0_total_candidate_count_meets_floor() -> None:
    packages = _styled_packages()
    total = sum(1 for _, _ in _all_entries(packages))
    floor = int(load_constant("curriculum.styled_corpus.total_candidates_min"))
    assert total >= floor, f"total candidates {total} below floor {floor}"


# --- G4 / G5 / G6 ---------------------------------------------------------

def test_phase16_0_average_meaningful_char_count_ceiling() -> None:
    packages = _styled_packages()
    chars = [
        _meaningful_char_count(str(_payload(entry)["response_text"]))
        for _, entry in _all_entries(packages)
        if _is_train_or_held_out(entry)
    ]
    avg = sum(chars) / max(1, len(chars))
    ceiling = float(load_constant("curriculum.styled_corpus.avg_char_count_max"))
    assert avg <= ceiling, f"avg meaningful char_count {avg:.3f} above {ceiling}"


def test_phase16_0_no_response_exceeds_hard_max_raw_len() -> None:
    packages = _styled_packages()
    hard_max = int(load_constant("curriculum.styled_corpus.char_count_hard_max"))
    overlong = [
        (entry["entry_id"], str(_payload(entry)["response_text"]))
        for _, entry in _all_entries(packages)
        if len(str(_payload(entry)["response_text"])) > hard_max
        and _is_train_or_held_out(entry)
    ]
    assert not overlong, f"overlong responses (raw_len > {hard_max}): {overlong[:5]}"


def test_phase16_0_long_reply_share_under_ceiling() -> None:
    packages = _styled_packages()
    chars = [
        _meaningful_char_count(str(_payload(entry)["response_text"]))
        for _, entry in _all_entries(packages)
        if _is_train_or_held_out(entry)
    ]
    long_share = sum(1 for n in chars if 8 <= n <= 15) / max(1, len(chars))
    ceiling = float(load_constant("curriculum.styled_corpus.long_reply_ratio_max"))
    assert long_share <= ceiling, (
        f"long_reply_share {long_share:.4f} above ceiling {ceiling}"
    )


# --- G7 / G8 / G9 ---------------------------------------------------------

def test_phase16_0_forbidden_llm_tokens_zero_in_train_and_held_out() -> None:
    packages = _styled_packages()
    hits: list[str] = []
    for _, entry in _all_entries(packages):
        if not _is_train_or_held_out(entry):
            continue
        text = str(_payload(entry)["response_text"])
        for bad in FORBIDDEN_LLM_TOKENS:
            if bad in text:
                hits.append(f"{entry['entry_id']}:{bad}")
    assert not hits, f"forbidden tokens in styled corpus: {hits[:5]}"


def test_phase16_0_forbidden_tokens_in_contrast_are_expected() -> None:
    """contrast role IS the LLM-病 anti-example. It MUST contain some forbidden."""
    packages = _styled_packages()
    contrast_entries = [
        entry for _, entry in _all_entries(packages)
        if _payload(entry).get("role") == "contrast"
    ]
    assert len(contrast_entries) >= int(
        load_constant("curriculum.styled_corpus.paradigm_count_min")
    ), "every paradigm must have at least one contrast"


def test_phase16_0_real_name_zero_match_across_all_phase16_files() -> None:
    bad_names = ("王嘉豪", "wangjiahao")
    for path in PACKAGE_ROOT.glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        for bad in bad_names:
            assert bad not in text, f"{path}: real name '{bad}' leaked"
    if DESIGN_DOC.exists():
        text = DESIGN_DOC.read_text(encoding="utf-8")
        for bad in bad_names:
            assert bad not in text, f"{DESIGN_DOC}: real name '{bad}' leaked"


# --- G10 / G11 ------------------------------------------------------------

def test_phase16_0_every_paradigm_has_held_out_candidate() -> None:
    packages = _styled_packages()
    held_out_by_par: dict[str, int] = {}
    for _, entry in _all_entries(packages):
        if entry.get("held_out") is True:
            pid = _payload(entry)["paradigm_id"]
            held_out_by_par[pid] = held_out_by_par.get(pid, 0) + 1
    floor = int(load_constant("curriculum.styled_corpus.held_out_min_per_paradigm"))
    all_pids = {
        _payload(entry)["paradigm_id"]
        for _, entry in _all_entries(packages)
    }
    missing = [pid for pid in all_pids if held_out_by_par.get(pid, 0) < floor]
    assert not missing, f"paradigms missing held_out: {missing}"


def test_phase16_0_every_paradigm_has_contrast_candidate() -> None:
    packages = _styled_packages()
    contrast_by_par: dict[str, int] = {}
    for _, entry in _all_entries(packages):
        if _payload(entry).get("role") == "contrast":
            pid = _payload(entry)["paradigm_id"]
            contrast_by_par[pid] = contrast_by_par.get(pid, 0) + 1
    floor = int(load_constant("curriculum.styled_corpus.contrast_min_per_paradigm"))
    all_pids = {
        _payload(entry)["paradigm_id"]
        for _, entry in _all_entries(packages)
    }
    missing = [pid for pid in all_pids if contrast_by_par.get(pid, 0) < floor]
    assert not missing, f"paradigms missing contrast: {missing}"


# --- G12 ------------------------------------------------------------------

def test_phase16_0_train_held_out_contrast_response_texts_have_no_collision() -> None:
    """Same text across train/held_out/contrast would erode SDPL invariants."""
    packages = _styled_packages()
    train_texts: set[str] = set()
    held_out_texts: set[str] = set()
    contrast_texts: set[str] = set()
    for _, entry in _all_entries(packages):
        text = str(_payload(entry)["response_text"])
        role = _payload(entry).get("role")
        if role == "contrast":
            contrast_texts.add(text)
        elif entry.get("held_out") is True:
            held_out_texts.add(text)
        else:
            train_texts.add(text)
    # Train vs contrast must have ZERO overlap (contrast is the anti-example)
    overlap_train_contrast = train_texts & contrast_texts
    assert not overlap_train_contrast, (
        f"train/contrast text overlap: {list(overlap_train_contrast)[:3]}"
    )
    # held_out may share some short tokens with train (e.g. "好。" recurs across
    # paradigms — that's quiet_girl's signature); but held_out vs contrast must
    # not overlap.
    overlap_ho_contrast = held_out_texts & contrast_texts
    assert not overlap_ho_contrast, (
        f"held_out/contrast text overlap: {list(overlap_ho_contrast)[:3]}"
    )


# --- G13 ------------------------------------------------------------------

def test_phase16_0_runtime_cognitive_has_no_paradigm_id_branching() -> None:
    """paradigm_id and affect_bucket must never branch runtime logic."""
    forbidden_patterns = (
        r'paradigm_id\s*==',
        r'\["paradigm_id"\]',
        r'\.get\("paradigm_id"\)',
        r'affect_bucket\s*==',
        r'\["affect_bucket"\]',
        r'\.get\("affect_bucket"\)',
    )
    bad: list[str] = []
    for root in ("runtime/cognitive", "runtime/demo_substrate"):
        for py in Path(root).rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            for pat in forbidden_patterns:
                if re.search(pat, text):
                    bad.append(f"{py}:{pat}")
    assert not bad, f"paradigm_id/affect_bucket branching leaked into runtime: {bad}"


# --- G14 ------------------------------------------------------------------

def test_phase16_0_styled_packages_validate_under_curriculum_schema() -> None:
    paths = sorted(PACKAGE_ROOT.glob("*.yaml"))
    assert paths, "no styled packages produced"
    package_min = int(load_constant("curriculum.styled_corpus.styled_package_count_min"))
    assert len(paths) >= package_min, (
        f"styled package count {len(paths)} below floor {package_min}"
    )
    for path in paths:
        raw = load_neutral_curriculum_pack_file(path)
        package = load_curriculum_package(raw)
        trace = validate_curriculum_package(package)
        assert trace.accepted, f"{path}: validation rejected with reasons {trace.reasons}"


# --- G15 (subset — full regression run from CLI) --------------------------

def test_phase16_0_generator_is_idempotent_and_summary_passes_floors() -> None:
    """Running the generator twice produces identical output and meets floors."""
    res = subprocess.run(
        [sys.executable, "-m", "scripts.curriculum.generate_styled_corpus", "--summary-only"],
        capture_output=True, text=True, check=True, encoding="utf-8",
    )
    summary = json.loads(res.stdout)
    assert summary["paradigm_count"] >= int(
        load_constant("curriculum.styled_corpus.paradigm_count_min")
    )
    assert summary["candidate_count"] >= int(
        load_constant("curriculum.styled_corpus.total_candidates_min")
    )
    assert summary["avg_char_count"] <= float(
        load_constant("curriculum.styled_corpus.avg_char_count_max")
    )
    assert summary["max_char_count"] <= int(
        load_constant("curriculum.styled_corpus.char_count_hard_max")
    )
    assert summary["long_share"] <= float(
        load_constant("curriculum.styled_corpus.long_reply_ratio_max")
    )
    assert summary["forbidden_hits"] == []
