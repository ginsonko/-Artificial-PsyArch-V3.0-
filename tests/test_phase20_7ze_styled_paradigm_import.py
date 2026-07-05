from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from apv3test.runtime.phase20_7.runtime import import_styled_paradigm_seeds


def test_phase20_7ze_styled_paradigm_seeds_imported_to_experience_flow(tmp_path: Path) -> None:
    """§38.2: 一千来句风格化对话示例导入经验流. 130个范式种子."""
    result = import_styled_paradigm_seeds(tmp_path / "seeds.sqlite")
    assert result["imported"] >= 100  # 至少100个范式种子
    assert result["paradigms"] >= 100  # 至少100个不同paradigm
    assert result["event_kind"] == "styled_paradigm_seed"
    with sqlite3.connect(tmp_path / "seeds.sqlite") as conn:
        cnt = conn.execute(
            "SELECT COUNT(*) FROM phase20_7_experience_events WHERE event_kind='styled_paradigm_seed'"
        ).fetchone()[0]
    assert cnt >= 100


def test_phase20_7ze_seeds_contain_paradigm_metadata_not_answer_table(tmp_path: Path) -> None:
    """§38.3红线: 范式种子含paradigm元数据, 非答案表. 每条是表达范式种子."""
    import_styled_paradigm_seeds(tmp_path / "meta.sqlite")
    with sqlite3.connect(tmp_path / "meta.sqlite") as conn:
        rows = conn.execute(
            "SELECT payload_json FROM phase20_7_experience_events WHERE event_kind='styled_paradigm_seed' LIMIT 10"
        ).fetchall()
    for row in rows:
        payload = json.loads(row[0])
        assert "paradigm_id" in payload
        assert "paradigm_label" in payload
        assert "response_text" in payload
        assert "response_tokens" in payload
        assert "affect_bucket" in payload
        assert "source_policy" in payload  # §37源分化标记


def test_phase20_7ze_seeds_not_all_same_reply(tmp_path: Path) -> None:
    """§38.3红线: 不许p:resp:hello压倒所有上下文. 导入的种子有不同回复."""
    import_styled_paradigm_seeds(tmp_path / "variety.sqlite")
    with sqlite3.connect(tmp_path / "variety.sqlite") as conn:
        rows = conn.execute(
            "SELECT json_extract(payload_json, '$.response_text') FROM phase20_7_experience_events "
            "WHERE event_kind='styled_paradigm_seed'"
        ).fetchall()
    replies = {r[0] for r in rows if r[0]}
    # 有多种不同回复 (非全是"你好")
    assert len(replies) >= 20


def test_phase20_7ze_seeds_no_forbidden_convergence(tmp_path: Path) -> None:
    """红线: 导入不声称范式收敛/完成."""
    result = import_styled_paradigm_seeds(tmp_path / "redline.sqlite")
    forbidden = ("paradigm_converged", "paradigm_complete", "seeds_complete", "style_converged")
    for token in forbidden:
        assert token not in str(result).lower()


def test_phase20_7ze_seeds_cover_core_paradigms(tmp_path: Path) -> None:
    """导入覆盖白皮书§36核心范式: 问候/共情/学习/拒绝/询问等."""
    import_styled_paradigm_seeds(tmp_path / "cover.sqlite")
    with sqlite3.connect(tmp_path / "cover.sqlite") as conn:
        rows = conn.execute(
            "SELECT json_extract(payload_json, '$.paradigm_id') FROM phase20_7_experience_events "
            "WHERE event_kind='styled_paradigm_seed'"
        ).fetchall()
    paradigm_ids = {r[0] for r in rows if r[0]}
    # 至少覆盖 PAR-A(问候) 到 PAR-G 多类
    prefixes = {pid.split(".")[0] for pid in paradigm_ids if pid}
    assert len(prefixes) >= 5  # 至少5类范式