"""Phase20.7 AP 画板 — 逐轮廓投影绘画 v1 (§66/§187.2, 用户 2026-07-04 裁定).

发展路径 (用户理论): 画画一开始是临摹自己想象中的画面. AP 与人不同 — 它的想象
画布 (SensoryCanvas) 是可访问的内部状态, 可以**逐轮廓投影**到画板, 而非逐笔.
但"不是所有想象画面都投" — 每 tick 只投当轮竞争胜出的那个轮廓单元 (同 DraftGrid
逐字写的原理); 投影后观察自己的画 (readback 成视觉 SA), 最后 commit 外显给用户.

管线 (与文字草稿同构):
  想象画布 → 轮廓单元提取 (V2 边缘通道 + 颜色通道, 感受器级) →
  每 tick: project_contour(能量竞争胜者) / observe_painting / commit_painting →
  PNG 外显.

红线:
- 轮廓单元来自 AP 自己的想象画布 (从教过的视觉经验重建), 没教过的东西画不出;
- 无模板图库/无 clipart/无外部绘图模型;
- 单元能量低于阈值不投 ("决定要投的才投"), 每步是真 tick 行动可审计;
- 修改/擦除 (edit_projection) 是 v2 — 本 v1 只有 投/观察/提交.
"""
from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from PIL import Image

from .models import RuntimeTickEventV2


PAINT_SCHEMA_ID = "apv3_phase20_7_ap_paint_board/v1"


@dataclass
class ContourUnit:
    """一个可投影的轮廓单元: 想象画布上的连通高边缘区域 + 该区域的主色."""

    unit_id: int
    mask: np.ndarray            # HxW bool — 区域掩码
    edge_mask: np.ndarray       # HxW bool — 区域内的边缘像素
    mean_color: tuple[float, float, float]
    energy: float               # 先天显著性 (§29): fg-vs-bg 对比×清晰度. 仅作行动竞争 baseline 项,
                                 # 不参与排序 — 投影顺序由学到的共现决定 (删 units.sort 后).
    bbox: tuple[int, int, int, int]
    edge_ratio: float = 0.0     # 感受器: 该单元与背景邻接的边界像素占比 (几何感受)
    color_dev: float = 0.0      # 感受器: 该单元均色与主体均色的色距 (色彩感受)
    role_bucket: str = ""       # role = paint_role_bucket(edge_ratio, color_dev) — 无分类 if


@dataclass
class APPaintBoard:
    """AP 的画板 — 空白画布, 只能被投影行动改变 (类比 DraftGrid 只能被 write 改变)."""

    pixels: np.ndarray
    projected_units: list[int] = field(default_factory=list)

    @classmethod
    def blank(cls, height: int, width: int) -> "APPaintBoard":
        return cls(pixels=np.ones((height, width, 3), dtype=np.float32) * 0.97)


def _pixel_subject_mask(canvas_pixels: np.ndarray) -> np.ndarray:
    """像素级主体掩码: 色差二值化 → 多数平滑去噪 → 最大连通域 (全部像素级, 无网格块).

    背景 = 画布边缘中位色 (人不画背景); 主体 = 与背景色距离超过自适应阈值的
    最大连通区域. 相当于人眼的图形-背景分离 (figure-ground), 感受器级统计.
    """
    h, w = canvas_pixels.shape[:2]
    border = np.concatenate(
        [
            canvas_pixels[0, :].reshape(-1, 3),
            canvas_pixels[-1, :].reshape(-1, 3),
            canvas_pixels[:, 0].reshape(-1, 3),
            canvas_pixels[:, -1].reshape(-1, 3),
        ]
    )
    bg_color = np.median(border, axis=0)
    color_dist = np.sqrt(((canvas_pixels - bg_color[None, None, :]) ** 2).sum(axis=2))
    # 自适应阈值: 主体应是画布中的少数派 (单主体照片的图形-背景常识).
    # 初始阈值太松会把大半画布当主体 (实测 0.76 占比 → "啥也不是"的涂抹).
    # 从 82 分位起, 占比 >0.5 就逐步收紧, 直到主体占比合理或达到 98 分位.
    theta = max(0.10, float(np.percentile(color_dist.flatten(), 82)) * 0.5)
    mask = color_dist > theta
    for pct in (88, 92, 95, 97, 98):
        if float(mask.mean()) <= 0.5:
            break
        theta = max(theta, float(np.percentile(color_dist.flatten(), pct)) * 0.6)
        mask = color_dist > theta
    if float(mask.mean()) > 0.65 or float(mask.mean()) < 0.005:
        return np.zeros((h, w), dtype=bool)  # 图形-背景分不开 → 诚实不画
    # 3×3 多数平滑 ×2: 去孤立噪点、补小孔 (像素级形态学, 无 cell 块)
    for _ in range(2):
        padded = np.pad(mask.astype(np.uint8), 1)
        neigh = sum(
            padded[1 + dy: h + 1 + dy, 1 + dx: w + 1 + dx]
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
        )
        mask = neigh >= 5
    if not mask.any():
        return mask
    # 最大连通域 (像素级 BFS, 用行程压缩以控制成本)
    from collections import deque

    labels = np.zeros((h, w), dtype=np.int32)
    next_label = 0
    best_label, best_size = 0, 0
    for sy in range(h):
        xs = np.where(mask[sy] & (labels[sy] == 0))[0]
        for sx in xs:
            if labels[sy, sx]:
                continue
            next_label += 1
            queue = deque([(sy, int(sx))])
            labels[sy, sx] = next_label
            size = 0
            while queue:
                cy, cx = queue.popleft()
                size += 1
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not labels[ny, nx]:
                        labels[ny, nx] = next_label
                        queue.append((ny, nx))
            if size > best_size:
                best_size, best_label = size, next_label
    return labels == best_label


def _mask_outline(mask: np.ndarray, thickness: int = 2) -> np.ndarray:
    """掩码的像素级边界带 (腐蚀差), thickness 控制描边宽度 — 连续平滑轮廓线."""
    er = mask.copy()
    for _ in range(max(1, thickness)):
        e2 = er.copy()
        e2[1:, :] &= er[:-1, :]
        e2[:-1, :] &= er[1:, :]
        e2[:, 1:] &= er[:, :-1]
        e2[:, :-1] &= er[:, 1:]
        er = e2
    return mask & ~er


def extract_contour_units(
    canvas_pixels: np.ndarray,
    canvas_clarity: np.ndarray,
    *,
    max_units: int = 6,
    cell: int = 12,
) -> list[ContourUnit]:
    """从想象画布提取人类意义的轮廓单元 (像素级, 2026-07-04 v3).

    v1 用粗网格 cell 掩码 → 画出直角色块 (用户实测批评). v2 全部像素级.
    v3 (2026-07-04 R5/路径B): 删 units.sort(key=energy) 硬编排序; energy 字段语义改为
    先天显著性 (§29): 它不决定投影顺序 — 投影顺序 = 感受器发现顺序 (主体外轮廓先被
    提取出, 自然先投影), 细节按发现顺序续投. 这不是排序决策, 是物理显著序.

    旧版"energy 锁死先外后内"是**用排序键伪装出儿童绘画发展顺序**, 现在改成:
    单元的 energy 仅作为先天显著性感受器的输出 (驱动 baseline 项参与行动竞争, 不
    排序), 与白皮书 §29 "先天显著性"机制对齐.

    (1) 图形-背景分离 (二值化+平滑+最大连通域) 得到平滑主体剪影;
    (2) 单元0 = 主体外轮廓 (像素级边界带描边) + 主体色 wash — 先勾边再上色;
        (该序由感受器产出顺序决定: 主体外轮廓是分离的最显著感受野, 自然 first-in-list)
    (3) 后续单元 = 主体内部与主体均色差异大的细节连通区 (斑点/柄/纹理), 按发现顺序续投.
    """
    h, w = canvas_pixels.shape[:2]
    subject_mask = _pixel_subject_mask(canvas_pixels)
    if not subject_mask.any() or int(subject_mask.sum()) < 64:
        return []
    outline = _mask_outline(subject_mask, thickness=2)
    subject_pixels = canvas_pixels[subject_mask]
    mean_color = tuple(float(v) for v in subject_pixels.reshape(-1, 3).mean(axis=0))
    # 先天显著性 (§29): 主体外轮廓 vs 背景的像素级对比度, 乘以该区域清晰度均值.
    # 这是视觉系统对该单元"多显著"的感受器输出, 不是排序竞争的决策值.
    bg_mask = ~subject_mask
    bg_mean = (
        tuple(float(v) for v in canvas_pixels[bg_mask].reshape(-1, 3).mean(axis=0))
        if bg_mask.any() else (0.5, 0.5, 0.5)
    )
    fg_bg_contrast = float(np.sqrt(sum((c - b) ** 2 for c, b in zip(mean_color, bg_mean))))
    clarity_mean = float(canvas_clarity[subject_mask].mean()) if canvas_clarity[subject_mask].size else 0.3
    # 主体外轮廓的显著性 baseline: 强对比 × 高清晰度 → 显著性高, 但只参与 drive 不排序.
    subject_dominance = round(float(np.clip(fg_bg_contrast / 0.6, 0.0, 1.0) * (0.5 + clarity_mean * 0.5)), 4)
    ys, xs = np.where(subject_mask)
    # 感受器量: 主体单元的边界像素占比 (与背景邻接) + 色距 (自身为参考, dev=0)
    from .paradigm_process import paint_role_bucket

    subj_edge_ratio = float(outline.sum()) / max(float(subject_mask.sum()), 1.0)
    subj_color_dev = 0.0  # 主体单元是色距参考基准
    units: list[ContourUnit] = [
        ContourUnit(
            unit_id=0,
            mask=subject_mask,
            edge_mask=outline,
            mean_color=mean_color,  # type: ignore[arg-type]
            energy=subject_dominance,
            bbox=(int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())),
            edge_ratio=round(subj_edge_ratio, 4),
            color_dev=round(subj_color_dev, 4),
            role_bucket=paint_role_bucket(subj_edge_ratio, subj_color_dev),
        )
    ]
    # 内部细节: 主体内与主体均色距离大的像素 → 平滑 → 连通分组 (粗网格仅用于分组标记)
    inner = subject_mask & ~outline
    if inner.any():
        inner_dist = np.sqrt(((canvas_pixels - np.array(mean_color)[None, None, :]) ** 2).sum(axis=2))
        theta_d = max(0.12, float(np.percentile(inner_dist[inner], 90)) * 0.7)
        detail = inner & (inner_dist > theta_d)
        padded = np.pad(detail.astype(np.uint8), 1)
        neigh = sum(
            padded[1 + dy: h + 1 + dy, 1 + dx: w + 1 + dx]
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
        )
        detail = neigh >= 5
        gh, gw = max(1, h // cell), max(1, w // cell)
        seen2 = np.zeros((gh, gw), dtype=bool)
        for r in range(gh):
            for c in range(gw):
                block = detail[r * cell:(r + 1) * cell, c * cell:(c + 1) * cell]
                if not block.size or float(block.mean()) < 0.08 or seen2[r, c]:
                    continue
                queue = [(r, c)]
                seen2[r, c] = True
                comp2: list[tuple[int, int]] = []
                while queue:
                    cr, cc = queue.pop()
                    comp2.append((cr, cc))
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < gh and 0 <= nc < gw and not seen2[nr, nc]:
                            b2 = detail[nr * cell:(nr + 1) * cell, nc * cell:(nc + 1) * cell]
                            if b2.size and float(b2.mean()) >= 0.08:
                                seen2[nr, nc] = True
                                queue.append((nr, nc))
                dmask = np.zeros((h, w), dtype=bool)
                for cr, cc in comp2:
                    dmask[cr * cell:(cr + 1) * cell, cc * cell:(cc + 1) * cell] = detail[
                        cr * cell:(cr + 1) * cell, cc * cell:(cc + 1) * cell
                    ]
                if not dmask.any() or len(units) > max_units:
                    continue
                dpix = canvas_pixels[dmask]
                dys, dxs = np.where(dmask)
                # 细节单元的显著性 = 它与主体均色的局部距离 × 区域清晰度 — 不参与排序.
                local_contrast = float(np.sqrt(((dpix - np.array(mean_color)[None, :]) ** 2).sum(axis=1)).mean()) if dpix.size else 0.0
                detail_dominance = round(float(np.clip(local_contrast / 0.6, 0.0, 1.0) * (0.10 + clarity_mean * 0.20)), 4)
                # 感受器量: 该细节区与背景邻接占比 (通常极低=内部) + 与主体均色的色距.
                dmask_outline = _mask_outline(dmask, thickness=1)
                d_edge_ratio = float((dmask_outline & bg_mask).sum()) / max(float(dmask.sum()), 1.0)
                d_color_dev = float(np.clip(local_contrast, 0.0, 1.0))
                dmean = tuple(float(v) for v in dpix.reshape(-1, 3).mean(axis=0))
                units.append(
                    ContourUnit(
                        unit_id=len(units),
                        mask=dmask,
                        edge_mask=dmask,
                        mean_color=dmean,  # type: ignore[arg-type]
                        energy=detail_dominance,
                        bbox=(int(dxs.min()), int(dys.min()), int(dxs.max()), int(dys.max())),
                        edge_ratio=round(d_edge_ratio, 4),
                        color_dev=round(d_color_dev, 4),
                        role_bucket=paint_role_bucket(d_edge_ratio, d_color_dev),
                    )
                )
    # 不 sort: 投影顺序 = 感受器发现顺序 (主体外轮廓先发现先投, 细节按扫描顺序续投).
    # 删 units.sort(key=lambda u: u.energy, reverse=True) — 它把"先天显著性"伪装成排序决策.
    return units[:max_units]


def project_contour(board: APPaintBoard, unit: ContourUnit) -> None:
    """投影一个轮廓单元: 外轮廓单元=平滑描边+区域上色; 细节单元=以细节色绘制."""
    if unit.unit_id == 0:
        line_color = np.array([max(0.0, c * 0.35) for c in unit.mean_color], dtype=np.float32)
        wash_color = np.array(unit.mean_color, dtype=np.float32)
        board.pixels[unit.edge_mask] = board.pixels[unit.edge_mask] * 0.10 + line_color * 0.90
        interior = unit.mask & ~unit.edge_mask
        board.pixels[interior] = board.pixels[interior] * 0.25 + wash_color * 0.75
    else:
        color = np.array(unit.mean_color, dtype=np.float32)
        board.pixels[unit.mask] = board.pixels[unit.mask] * 0.25 + color * 0.75
    board.projected_units.append(unit.unit_id)


def render_painting_png(board: APPaintBoard, *, db_path: Path, tick: int) -> tuple[str, str]:
    out_dir = Path(db_path).parent / "phase20_7_inner_pictures"
    out_dir.mkdir(parents=True, exist_ok=True)
    arr = np.uint8(np.clip(board.pixels, 0.0, 1.0) * 255.0)
    digest = hashlib.sha256(arr.tobytes()).hexdigest()[:12]
    path = out_dir / f"painting_{digest}_{tick:04d}.png"
    Image.fromarray(arr, mode="RGB").save(path)
    return str(path), digest


def _pclip(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def run_painting_ticks(
    conn: sqlite3.Connection,
    pool: Any,
    *,
    session_id: str,
    start_tick: int,
    db_path: Path,
    canvas_pixels: np.ndarray,
    canvas_clarity: np.ndarray,
    source_imagined_hash: str,
    insert_experience_event: Any,
    insert_action_record: Any,
    max_paint_ticks: int = 10,
) -> tuple[tuple[RuntimeTickEventV2, ...], int, str]:
    """逐轮廓投影绘画子循环. 返回 (tick events, 最新 tick, 画作 PNG 路径或 '').

    每 tick 竞争: project_contour(下一个高能单元) / observe_painting / commit_painting.
    单元按感受器发现序投影 (不 sort), 显著性 < 0.08 的单元不投 ("决定要投的才投").
    投影完成后观察一次自己的画 (readback → 视觉 SA 入池), 然后 commit.

    drive baseline 来源 (§29): project_contour 的 baseline 含该单元的先天显著性
    (units[next_index].energy) 作为视觉感受器对边缘显著性的先天倾向; observe/commit
    的 baseline 是行动器层先天节奏 (画完→读→交). 它们仅作 baseline 项参与行动竞争,
    不是某行动必胜的硬编码阶梯 — 当 significance 不足时可被其它行动 drive 反超.
    """
    # §185 预算: 画板分辨率上限 480px 短边 — 想象画布可能很大 (原图分辨率),
    # 画画是投影不是复印, 适度降采样不损失轮廓意义且保证 tick 预算.
    h0, w0 = canvas_pixels.shape[:2]
    max_side = 480
    if max(h0, w0) > max_side:
        from PIL import Image as _Img

        scale = max_side / max(h0, w0)
        nw, nh = max(1, int(w0 * scale)), max(1, int(h0 * scale))
        canvas_pixels = (
            np.asarray(
                _Img.fromarray(np.uint8(np.clip(canvas_pixels, 0, 1) * 255)).resize((nw, nh), _Img.Resampling.BILINEAR),
                dtype=np.float32,
            )
            / 255.0
        )
        canvas_clarity = (
            np.asarray(
                _Img.fromarray(np.uint8(np.clip(canvas_clarity, 0, 1) * 255)).resize((nw, nh), _Img.Resampling.BILINEAR),
                dtype=np.float32,
            )
            / 255.0
        )
    units = [u for u in extract_contour_units(canvas_pixels, canvas_clarity) if u.energy >= 0.08]
    if not units:
        return (), start_tick, ""
    from .experience_log import from_json as _paint_from_json
    from .paradigm_process import (
        PAINT_PARADIGM_KEY,
        paint_step_counter_pressure,
        perceive_painting_state,
        query_paint_next_steps,
        record_paint_step,
    )

    h, w = canvas_pixels.shape[:2]
    board = APPaintBoard.blank(h, w)
    events: list[RuntimeTickEventV2] = []
    tick = int(start_tick)
    observed = False
    painting_path = ""
    projected_ids: set[int] = set()
    projected_buckets: list[str] = []
    executed_paint_steps: list[dict[str, str]] = []
    for _ in range(max_paint_ticks):
        tick += 1
        pending = [u for u in units if u.unit_id not in projected_ids]
        remaining = len(pending)
        # 感知当前绘画状态 (共享函数): 已投哪些 role 桶 / 投完没 / 观察过没.
        state = perceive_painting_state(
            projected_buckets=list(projected_buckets), remaining=remaining, observed=observed,
        )
        # 查学到的 (动作, 目标role桶) 分布 → 减反例压 → 竞争. 空库=无学习支持.
        learned = query_paint_next_steps(conn, prev_action_result=state, from_json=_paint_from_json)
        learned_map: dict[tuple[str, str], float] = {}
        for step in learned:
            counter = paint_step_counter_pressure(
                conn, prev_action_result=state, action=str(step["action"]),
                target_role=str(step["target_role"]), from_json=_paint_from_json,
            )
            learned_map[(str(step["action"]), str(step["target_role"]))] = _pclip(float(step["support"]) * (1.0 - counter))
        # 候选行动: project (每个 pending role 桶一条) + observe + commit.
        # baseline 是行动器先天节奏 (§29): 有单元没画→倾向 project (含该桶单元的
        #   先天显著性 energy); 画完→observe; 观察后→commit. baseline 小, 学到的
        #   support 稳压过它 → 学过顺序就按学的, 没学过按先天显著性铺底.
        cands: list[dict[str, Any]] = []
        pending_by_bucket: dict[str, list] = {}
        for u in pending:
            pending_by_bucket.setdefault(u.role_bucket, []).append(u)
        for bucket, us in pending_by_bucket.items():
            top = max(us, key=lambda u: u.energy)  # 桶内选先天最显著的 (不跨桶排序)
            base = 0.20 + top.energy * 0.12
            learned_s = learned_map.get(("project_unit", bucket), 0.0)
            cands.append({
                "action_type": "project_unit", "target_role": bucket,
                "drive": round(_pclip(base * 0.15 + learned_s), 4), "unit": top,
                "learned_support": round(learned_s, 4), "baseline": round(base, 4),
            })
        obs_base = 0.16 if (remaining == 0 and not observed) else 0.02
        cands.append({
            "action_type": "observe_painting", "target_role": "none",
            "drive": round(_pclip(obs_base * 0.15 + learned_map.get(("observe_painting", "none"), 0.0) + (0.34 if remaining == 0 and not observed else 0.0) * 0.15), 4),
            "learned_support": round(learned_map.get(("observe_painting", "none"), 0.0), 4), "baseline": round(obs_base, 4),
        })
        com_base = 0.14 if (remaining == 0 and observed) else 0.02
        cands.append({
            "action_type": "commit_painting", "target_role": "none",
            "drive": round(_pclip(com_base * 0.15 + learned_map.get(("commit_painting", "none"), 0.0) + (0.52 if remaining == 0 and observed else 0.0) * 0.15), 4),
            "learned_support": round(learned_map.get(("commit_painting", "none"), 0.0), 4), "baseline": round(com_base, 4),
        })
        selected = max(cands, key=lambda r: float(r["drive"]))
        selected_type = str(selected["action_type"])
        target_role = str(selected["target_role"])
        rows = tuple({
            "action_type": (c["action_type"] + ("::" + c["target_role"] if c["target_role"] != "none" else "")),
            "drive": c["drive"], "learned_support": c["learned_support"], "baseline": c["baseline"],
            "selected": c is selected,
        } for c in cands)
        executed_paint_steps.append({"state": state, "action": selected_type, "target_role": target_role})
        if selected_type == "project_unit":
            unit = selected["unit"]
            project_contour(board, unit)
            projected_ids.add(unit.unit_id)
            projected_buckets.append(target_role)
            next_index = len(projected_ids)
            # 逐像素回放: 每次投影后存画板中间态 (小 PNG, 前端按 tick 序播放)
            step_path, _step_digest = render_painting_png(board, db_path=db_path, tick=tick)
            payload = {
                "schema_id": PAINT_SCHEMA_ID,
                "unit_id": unit.unit_id,
                "unit_energy": unit.energy,
                "unit_bbox": list(unit.bbox),
                "unit_mean_color": [round(c, 3) for c in unit.mean_color],
                "unit_role_bucket": unit.role_bucket,
                "unit_edge_ratio": unit.edge_ratio,
                "unit_color_dev": unit.color_dev,
                "target_role": target_role,
                "learned_support": selected["learned_support"],
                "projected_count": len(board.projected_units),
                "source_imagined_hash": source_imagined_hash,
                "board_snapshot_path": step_path,
            }
        elif selected_type == "observe_painting":
            observed = True
            luma = float((board.pixels[..., 0] * 0.299 + board.pixels[..., 1] * 0.587 + board.pixels[..., 2] * 0.114).mean())
            pool.observe_external(
                {
                    "sa_id": f"ap_painting::{source_imagined_hash[:12]}",
                    "family": "visual",
                    "label": f"self_painting_{len(board.projected_units)}_units",
                    "channel_signature": ("visual", "self_painted"),
                    "origin": "ap_paint_board_readback",
                    "real_energy": round(0.30 + (1.0 - luma) * 0.4, 4),
                    "metadata": {"ledger_source": "external"},
                },
                tick=tick,
            )
            payload = {
                "schema_id": PAINT_SCHEMA_ID,
                "readback": True,
                "projected_count": len(board.projected_units),
                "board_mean_luma": round(luma, 4),
            }
        else:
            painting_path, digest = render_painting_png(board, db_path=db_path, tick=tick)
            payload = {
                "schema_id": PAINT_SCHEMA_ID,
                "committed": True,
                "painting_path": painting_path,
                "painting_hash": digest,
                "projected_unit_count": len(board.projected_units),
                "skipped_low_energy_units": sum(1 for u in extract_contour_units(canvas_pixels, canvas_clarity) if u.energy < 0.08),
            }
        action_record_id = insert_action_record(
            conn,
            session_id=session_id,
            tick=tick,
            action_type=selected_type,
            selected=True,
            drive=float(selected["drive"]),
            eligibility={"paint_board_active": True},
            target_refs={"source_imagined_hash": source_imagined_hash},
        )
        event_id = insert_experience_event(
            conn,
            session_id=session_id,
            tick=tick,
            event_kind=f"ap_paint_{selected_type}",
            action_record_id=action_record_id,
            payload=payload,
        )
        inner_picture: dict[str, Any] = {}
        if selected_type == "commit_painting":
            inner_picture = {
                "source": "ap_paint_board_commit",
                "path": painting_path,
                "rendered_from_state_pool_canvas": True,
                "raw_source_asset_used_for_render": False,
                "clarity_coverage": 1.0,
                "projected_unit_count": len(board.projected_units),
            }
        elif selected_type == "project_unit" and payload.get("board_snapshot_path"):
            # 中间态也走 inner_picture 通道 (带 step 标记) — 前端逐 tick 回放画板
            inner_picture = {
                "source": "ap_paint_board_step",
                "path": str(payload["board_snapshot_path"]),
                "rendered_from_state_pool_canvas": True,
                "raw_source_asset_used_for_render": False,
                "clarity_coverage": round(next_index / max(len(units), 1), 3),
                "projected_unit_count": len(board.projected_units),
            }
        events.append(
            RuntimeTickEventV2(
                tick=tick,
                session_id=session_id,
                selected_action={"action_type": selected_type, "paint_board": True, "target_role": target_role, "learned_support": selected["learned_support"]},
                action_competition=rows,
                experience_event_ids_written=(event_id,),
                action_record_ids=(action_record_id,),
                visual_inner_picture=inner_picture,
                feelings={"source": "ap_paint_board", "paint_progress": round(next_index / max(len(units), 1), 3)},
                timings_ms={"paint_tick": 0.0},
            )
        )
        if selected_type == "commit_painting":
            break
    # 练习记录 (§173.5): 成功 commit 的这次作画, 把走过的 (状态→动作+role桶) 序列
    # 以 self_practice 落共现表 — AP 越画越熟 (支持度升). 只在真 commit 后记, 避免
    # 半途放弃的乱序污染. commit 存在 = painting_path 非空.
    if painting_path and executed_paint_steps:
        for step_row in executed_paint_steps:
            tick += 1
            record_paint_step(
                conn, session_id=session_id, tick=tick,
                prev_action_result=step_row["state"], action=step_row["action"],
                target_role=step_row["target_role"], origin="self_practice",
                insert_experience_event=insert_experience_event,
            )
    return tuple(events), tick, painting_path
