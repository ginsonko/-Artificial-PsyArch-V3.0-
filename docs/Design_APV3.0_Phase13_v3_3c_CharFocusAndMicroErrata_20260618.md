# APV3.0 Phase 13 — v3.3c 字焦点设计 + Codex Micro Errata 整合

日期: 2026-06-18
作者: 银子老师(关键洞察:字焦点)/ Claude(整合)
状态: **银子老师指出 v3.3 缺一个核心能力:草稿空间的"字焦点"(对偶视焦点)。这是 Phase 13.5b 真正关键的基础设施,我之前漏了。同时整合 Codex 的 v3.2c/v3.3b micro errata 8 项 R1-R8。本稿是 v3.3 的关键扩展 + 实施前最后一份合并合同。**

前作链:
- v3 / v3.1 / v3.2 / v3.2a / v3.2b/3.3a Merged Errata / v3.2c/3.3b Codex Micro Errata
- **v3.3c(本稿)**:字焦点新设计 + Codex 8 项整合

许可:AGPL-3.0-or-later
原架构设计:银子老师

---

## 第 0 章 v3.3c 修复 + 新增总览

### 0.1 银子老师关键洞察(v3.3c 核心)

> "如果想实现竖式,考虑到和人类一样的过程,是否我们还缺一个对草稿框回读时,类似移动视焦点,'移动字焦点'的能力?也就是可以聚焦到某个草稿框的文本空间位置的某个文本,回读时对应文本的能量更高,这样才能确保它'关注这一行的数字和第二行和它一列的数字的和'的效果?类似视焦点的设计,移动这个字焦点也是做成一种行动,可以尽可能对应视焦点的移动的设计。"

**我的诚实承认**:v3.3 漏了这个关键能力。

`read_grid_cell(row, col)` 直接读指定 cell,**但没有"为什么读这个"的认知载体**。系统没办法选择"现在该关注哪个 cell",导致没法做竖式列对齐计算。

**字焦点是视焦点在草稿空间的精确对偶**,数学上同构,实现上复用 EntitySA::focus 既有机制。

### 0.2 整合 Codex v3.2c/3.3b 8 项 micro errata

| 编号 | Codex R | 内容 |
|---|---|---|
| **R1** | CORRECTION.metadata.status 不当 hidden marker kind | SDPL/attention/Q/composed_vocab 路径不许读 status,只在 audit/curriculum_revalidation 可读 |
| **R2** | metadata 红线不误杀 AP-native context_tokens/context_tags | 区分 forbidden(style_tag/context_tag/design_note)vs allowed(context_tokens/context_tags 经统计学到) |
| **R3** | pseudonymous ID 不允许静默 str() 非字符串项 | 序列元素必须 str,非 str → TypeError;存储至少 32 hex |
| **R4** | held-out event_id 不进 AP state | event_id 仅 evaluator/store handle,AP 收到的 sensor SA 不含 event_id |
| **R5** | DraftGrid origin/spacing/digit_width 只在 evaluator 外部 | AP state 不许有 chosen_origin/origin_row/origin_col/spacing/digit_width 字段 |
| **R6** | 数学 fact SA id 必须 opaque | runtime 不许 parse `fact::add::3_7=10` 字串;label-bijection 测试 |
| **R7** | substrate 进 packet_key 后保留 backoff + 稀疏度监控 | exact 含 substrate,但 backoff 仍含 content-only 层;Q-key 数量监控 |
| **R8** | Phase 13.0 gate 数量按实际清单 | 不写"14 项"硬数字,报告列实际跑了哪些 gate |

### 0.3 v3.3c 新增(字焦点)

| 编号 | 内容 |
|---|---|
| **C1** | DraftCharFocus EntitySA(复用 focus family,不新增 SA type) |
| **C2** | 4 类字焦点 action(MOVE_TO / SHIFT / SCAN_ROW / SCAN_COLUMN + 形状/范围扩展) |
| **C3** | Cell percept R 能量调制(字焦点 attention modulation,完全对偶 Phase 8.7) |
| **C4** | read_at_focus 显式行动 + 自动 scan 双路径 |
| **C5** | 焦点状态进 packet_key(经 row/col bucket 量化) |
| **C6** | 字焦点移动经 SDPL + ActionParameterMemory 学习,无硬编码竖式步骤 |
| **C7** | 验收:同问题不同 origin,焦点移动模式应相对一致(范式不变量) |

---

## 第 1 章 C1-C3:DraftCharFocus 实体设计

### 1.1 视焦点 vs 字焦点对偶表

| 维度 | Phase 8.7 视焦点 | v3.3c 字焦点 |
|---|---|---|
| 作用空间 | 2D pixel array(视觉感受器) | 2D cell grid(DraftGrid) |
| 一等 SA | `focus::vision::*` (EntitySA) | `focus::draft_grid::*` (EntitySA,复用 family) |
| 焦点位置 | `(focus_x, focus_y, radius)` | `(focus_row, focus_col, span)` |
| 焦点形状 | radius 圆形(可扩) | cell/row/column/rect |
| 能量调制 | 焦点附近 percept R 高 | 焦点附近 cell percept R 高 |
| 移动 action | `move_gaze_to(x, y)` / saccade | `move_char_focus_to(row, col)` |
| 学习路径 | SDPL + Phase 9.X ActionParameterMemory | 同款 |
| 复用机制 | Phase 8.7 既有 | 复用 Phase 8.7 数学,新 grid 适配层 |

**数学上完全同构**。

### 1.2 DraftCharFocus EntitySA

```python
# runtime/cognitive/attention/draft_char_focus.py(新文件)

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
from runtime.cognitive.state_pool.state_item import StateItem


class FocusShape(str, Enum):
    """字焦点形状(对应视焦点 region kinds)."""
    CELL = "cell"        # 单 cell 焦点(类视焦点 radius=1)
    ROW = "row"          # 整行(类视焦点 horizontal slit)
    COLUMN = "column"    # 整列(竖式必备)
    RECT = "rect"        # 矩形区域


@dataclass
class DraftCharFocus(StateItem):
    """
    字焦点 EntitySA.
    
    复用 v14 既有 focus family(family="focus"),不新增 SA type.
    完全对偶 Phase 8.7 视焦点设计.
    """
    sa_id: str = "focus::draft_grid"
    family: str = "focus"
    label: str = "draft_grid_focus"
    
    # 焦点位置(对应视焦点 x, y)
    focus_row: int = 0
    focus_col: int = 0
    
    # 焦点范围(对应视焦点 radius)
    focus_span: int = 1  # 单位:cell 数
    
    # 焦点形状(对应视焦点 region shape)
    focus_shape: FocusShape = FocusShape.CELL
    
    # 既有 StateItem 字段(R/V/P/A/F + ledger)继承
    # ...
    
    def is_within_focus(self, row: int, col: int) -> bool:
        """判断 cell (row, col) 是否在焦点范围内."""
        dr = abs(row - self.focus_row)
        dc = abs(col - self.focus_col)
        
        if self.focus_shape == FocusShape.CELL:
            return max(dr, dc) <= self.focus_span
        elif self.focus_shape == FocusShape.ROW:
            return dr == 0  # 同行
        elif self.focus_shape == FocusShape.COLUMN:
            return dc == 0  # 同列
        elif self.focus_shape == FocusShape.RECT:
            return dr <= self.focus_span and dc <= self.focus_span
        return False
```

### 1.3 能量调制函数(C3)

```python
# runtime/cognitive/attention/draft_focus_modulation.py(新文件)

import math


def compute_cell_percept_R_with_char_focus(
    cell_row: int,
    cell_col: int,
    focus: DraftCharFocus,
    base_R: float,
) -> float:
    """
    v3.3c: cell percept R 受字焦点能量调制.
    
    完全对应 Phase 8.7 视焦点 attention modulation:
    - 焦点中心 R = base_R * 1.0(满能量)
    - span 范围内 R = base_R * 1.0
    - span 外按距离高斯衰减
    - 极远距离 R ≈ base_R * 0.05(几乎不可见,但仍存在)
    """
    # 按形状算距离
    dr = abs(cell_row - focus.focus_row)
    dc = abs(cell_col - focus.focus_col)
    
    if focus.focus_shape == FocusShape.COLUMN:
        # 同列距离=0,跨列衰减
        relevant_distance = dc
    elif focus.focus_shape == FocusShape.ROW:
        relevant_distance = dr
    elif focus.focus_shape == FocusShape.CELL:
        relevant_distance = math.sqrt(dr**2 + dc**2)
    elif focus.focus_shape == FocusShape.RECT:
        relevant_distance = max(dr, dc)
    
    # 焦点中心 + span 范围内,full modulation
    if relevant_distance <= focus.focus_span:
        modulation = 1.0
    else:
        # 高斯衰减(类似 Phase 8.7)
        sigma = max(1.0, focus.focus_span * 2.0)  # 衰减半径
        decay_distance = relevant_distance - focus.focus_span
        modulation = math.exp(-(decay_distance**2) / (2 * sigma**2))
        
        # 不归零(类似 Phase 8.7 peripheral vision)
        modulation = max(0.05, modulation)
    
    # 焦点本身能量也调制(focus.attention_energy 反映"系统多关注 grid")
    return base_R * modulation * focus.attention_energy
```

### 1.4 每 tick 自动 scan(产生 percept)

```python
# apv3test/runtime/draft_grid_percept_emit.py(新文件)

def emit_draft_grid_percepts(
    state_pool,
    grid: DraftGrid,
    focus: DraftCharFocus,
    tick: int,
) -> list[PerceptSA]:
    """
    每 tick 自动扫 grid 产生 percept SA,字焦点调制能量.
    
    完全对应 Phase 8.6/8.7:视觉每 tick 产生 percept,视焦点决定能量分配.
    """
    percepts = []
    base_R = load_constant("draft_grid.cell_percept_base_R")
    
    for (row, col), cell in grid.cells.items():
        if cell.char == " ":
            continue  # 空 cell 不产生 percept
        
        # 焦点调制
        modulated_R = compute_cell_percept_R_with_char_focus(row, col, focus, base_R)
        
        # 焦点附近能量太低不产生(降算力)
        if modulated_R < load_constant("draft_grid.cell_percept_emit_threshold"):
            continue
        
        # spawn percept SA(标 SELF_DRAFT_GRID substrate)
        percept_sa = spawn_percept_sa(
            content=f"draft_cell::{row}_{col}::{cell.char}",
            real_energy=modulated_R,
            tick=tick,
        )
        # spawn PERCEIVED marker with substrate
        spawn_perceived_marker_v3_3a(
            target_sa_id=percept_sa.sa_id,
            tick=tick,
            substrate=PerceivedSource.SELF_DRAFT_GRID,
            metadata={
                "grid_relative_position_to_focus": {
                    "dr": row - focus.focus_row,
                    "dc": col - focus.focus_col,
                },
                "focus_shape": focus.focus_shape.value,
                "focus_span": focus.focus_span,
            },
        )
        percepts.append(percept_sa)
    
    return percepts
```

### 1.5 关键设计:percept 携带"相对焦点位置"

注意 `metadata["grid_relative_position_to_focus"]` — 这是 percept 携带的"我相对焦点在哪"。

**这让系统学到"相对空间范式",不是"绝对坐标"**。

举例:
- 焦点在 (3, 5),个位 cell (3, 5) 字符 "7"
- → percept "draft_cell::3_5::7" + metadata `{dr: 0, dc: 0, focus_shape: "column"}`
- 焦点在 (10, 8),个位 cell (10, 8) 字符 "7"
- → percept "draft_cell::10_8::7" + metadata `{dr: 0, dc: 0, focus_shape: "column"}`

**两个 percept 的相对位置 metadata 相同**(都是 `dr:0, dc:0`),系统学到的是**相对模式**。

---

## 第 2 章 C2 + C4 + C6:字焦点 actions(SDPL 学习路径)

### 2.1 字焦点 action 清单

```python
# apv3test/runtime/draft_action.py 扩展 v3.3c

@dataclass(frozen=True)
class DraftTextAction:
    """既有 5 个 1D + 7 个 2D + v3.3c 新增 8 个字焦点 actions."""
    # 1D(继承)
    # 2D 既有(v3.3 §1)
    # v3.3c 新增字焦点 actions:
    # - move_char_focus_to(row, col) — 跳转到指定位置
    # - char_focus_shift(row_delta, col_delta) — 相对移动
    # - char_focus_scan_row — 沿行从左到右扫
    # - char_focus_scan_column — 沿列从上到下扫
    # - char_focus_expand_span / contract_span — 范围调整
    # - char_focus_set_shape_cell/row/column/rect — 形状切换
    # - read_at_focus — 显式读焦点(强教学时用)
```

### 2.2 字焦点学习路径(SDPL emerge)

```
教学场景示例:
教师 demonstration: "看,3+7,要先看个位"
教师 visual percept: 教师手指向草稿上某列(2D 视觉感受 percept)
↓
SDPL packet:
  content: {vocab::"个位", vocab::"竖式列对齐", percept::教师手指视觉}
  source: PERCEIVED(EXTERNAL_VISUAL)
↓
SDPL learn:
  packet → action: move_char_focus_to(指向位置)
↓
RPE:
  系统尝试 move_char_focus_to(对应位置)
  → 看到列内两个数字 percept R 高(因焦点调制)
  → 召回 fact::add → 算出结果
  → commit 正确 → 正反馈
↓
长期固化:
  vocab "竖式列计算时" → 高 Q 移到列焦点
  完全 SDPL 学习,无硬编码
```

### 2.3 与 Phase 8.7 saccade 同源

视焦点 saccade 的学习:
- 视觉感受到外周高显著区
- attention selector 触发 `move_gaze_to(x, y)` action
- 经 ActionParameterMemory 学到"高显著区 → 移焦点"

字焦点同款:
- 草稿 percept(经字焦点调制)中外周区有未读 cell
- attention selector 触发 `char_focus_shift` action
- 经 ActionParameterMemory 学到"竖式列计算时 → 焦点沿列移动"

**完全复用 v14 既有学习机制**,无新公式。

### 2.4 行动选择经 SDPL packet 路径

```python
def select_char_focus_action_v3_3c(state_pool, packet) -> Optional[DraftTextAction]:
    """v3.3c: 字焦点 action 经标准 SDPL packet 路径竞争."""
    candidate_actions = [
        DraftTextAction(kind="char_focus_shift", row_delta=0, col_delta=-1, tick=...),
        DraftTextAction(kind="char_focus_shift", row_delta=1, col_delta=0, tick=...),
        DraftTextAction(kind="move_char_focus_to", grid_row=current_row, grid_col=last_col, tick=...),
        DraftTextAction(kind="char_focus_set_shape_column", tick=...),
        DraftTextAction(kind="read_at_focus", tick=...),
        # ...
    ]
    
    for action in candidate_actions:
        # Q 表 backoff 查 packet → action 的 Q 值
        action.expected_R_change = q_table_with_backoff.query(
            packet=packet,
            action=opaque_action_id_for(action),
        )
    
    # 标准 attention selector
    winner = attention_selector.select(candidate_actions)
    return winner
```

---

## 第 3 章 C5 + C7:字焦点状态进 packet_key + 验收

### 3.1 packet_key 新增字焦点维度

```python
# runtime/cognitive/sdpl/packet.py v3.3c

def compute_packet_key_v3_3c(packet: LearningPacket) -> tuple:
    """v3.3c: packet_key 含字焦点状态(经 bucket 量化)."""
    content_key = frozenset(...)
    source_key = frozenset(...)  # 含 substrate(v3.3a §E8)
    feeling_key = frozenset(...)
    
    # v3.3c 新增:字焦点状态(经 bucket)
    char_focus_sa = state_pool.get("focus::draft_grid")
    if char_focus_sa:
        focus_key = (
            R_bucket(char_focus_sa.real_energy),
            char_focus_sa.focus_shape.value,
            # 注意:不含绝对 row/col!只含 shape + R bucket
            # 这是为了"焦点活跃"是范式特征,绝对位置不是
            # (绝对位置已通过 cell percept 的 metadata.relative_position 表达)
        )
    else:
        focus_key = ("no_focus",)
    
    return (content_key, source_key, focus_key, feeling_key)
```

**关键**:packet_key 含焦点 **shape** 但不含 **绝对位置**。绝对位置走 percept 的 relative metadata,确保学到相对模式。

### 3.2 Q-key 稀疏度监控(响应 Codex R7)

字焦点引入新 packet 维度,Q-key 数量会增长。必须监控:

```python
def monitor_q_table_size(q_table) -> dict:
    """Codex R7: Q-key 数量不能爆炸."""
    return {
        "exact_keys": len(q_table.exact_q),
        "content_source_keys": len(q_table.content_source_q),
        "source_feeling_keys": len(q_table.source_feeling_q),
        "content_only_keys": len(q_table.content_q),
        "action_global_keys": len(q_table.action_global_q),
        "total_keys": sum(len(q) for q in [
            q_table.exact_q, q_table.content_source_q,
            q_table.source_feeling_q, q_table.content_q,
            q_table.action_global_q
        ]),
        # 报警阈值
        "warning_threshold": load_constant("sdpl.q_table.max_active_packets"),
    }


def test_q_table_does_not_explode_with_char_focus():
    """Phase 13.5b.0 必跑."""
    # 模拟 100 道两位数竖式加法,长跑
    for problem in synthetic_problems_100():
        run_full_vertical_addition(problem)
    
    stats = monitor_q_table_size(q_table)
    # 总 key 数应 < max_active_packets(5000)
    assert stats["total_keys"] < load_constant("sdpl.q_table.max_active_packets")
```

### 3.3 范式不变量验收(C7)

**关键验收**:同问题不同 origin 焦点移动模式应**相对一致**。

```python
def test_char_focus_movement_pattern_invariant_across_origins():
    """
    Phase 13.5b.0 必跑:
    同问题(23+47)在不同 origin 教学和测试,
    系统的字焦点移动相对模式应一致(都从右往左扫列).
    """
    # 教学:大量随机 origin 的 23+47 例子
    train_with_random_origins(problem=(23, 47), n=50)
    
    # 测试 1:origin=(0, 0)
    result_1 = solve_problem(problem=(23, 47), origin=(0, 0))
    focus_movements_1 = result_1.char_focus_action_trace
    # 转成相对移动序列
    relative_moves_1 = compute_relative_focus_moves(focus_movements_1)
    
    # 测试 2:origin=(5, 8)
    result_2 = solve_problem(problem=(23, 47), origin=(5, 8))
    relative_moves_2 = compute_relative_focus_moves(result_2.char_focus_action_trace)
    
    # 相对移动应高度相似(允许少许不同)
    similarity = sequence_similarity(relative_moves_1, relative_moves_2)
    assert similarity >= 0.85, f"Focus 移动模式不一致:{similarity}"
    
    # 两个测试答案都对
    assert result_1.committed_answer == result_2.committed_answer == "70"
```

---

## 第 4 章 整合 Codex R1-R8(v3.2c/3.3b)

### 4.1 R1 — CORRECTION.metadata.status 不当 hidden marker kind

```python
# scripts/red_line_check_v14.py 扩展 v3.3c

def check_correction_status_not_used_in_learning_paths():
    """
    R1 redline: SDPL/attention/Q/composed_vocab 路径
    不许 marker.metadata.get("status") 或 marker.metadata["status"].
    
    白名单:curriculum/revalidation, audit, reports.
    """
    target_dirs = ["runtime/cognitive/sdpl", "runtime/cognitive/attention",
                   "runtime/cognitive/composed_vocab", "runtime/cognitive/state_pool"]
    
    whitelist_files = ["audit", "render", "trace_format", "curriculum/revalidation"]
    
    forbidden_patterns = [
        r'marker\.metadata\.get\(\s*["\']status["\']',
        r'marker\.metadata\[\s*["\']status["\']\]',
        r'metadata\.get\(\s*["\']status["\']',  # 用别名也禁
    ]
    
    violations = []
    for target_dir in target_dirs:
        for py_file in Path(target_dir).rglob("*.py"):
            if any(w in str(py_file) for w in whitelist_files):
                continue
            content = py_file.read_text()
            for pat in forbidden_patterns:
                if re.search(pat, content):
                    violations.append(f"{py_file}: {pat}")
    return violations
```

测试 R1:
```python
def test_pending_revalidation_and_ordinary_correction_same_marker_kind():
    """R1: 两种状态都是 CORRECTION marker kind."""
    m1 = spawn_correction_marker_for_pending_revalidation(...)
    m2 = spawn_correction_marker_for_system_rejection(...)
    assert m1.kind == m2.kind == MarkerKind.CORRECTION


def test_marker_kind_count_unchanged():
    """R1: marker kind 数仍为 v14 既有数."""
    from config.family_to_type_mapping import MARKER_KINDS_DOCUMENTED
    assert len(MARKER_KINDS_DOCUMENTED) == 17  # 不增不减


def test_packet_key_does_not_include_status():
    """R1: packet_key 不含 status."""
    correction_marker_pending = spawn_correction_marker_for_pending_revalidation(...)
    correction_marker_system = spawn_correction_marker_for_system_rejection(...)
    
    packet_pending = make_packet(source_markers=[correction_marker_pending], ...)
    packet_system = make_packet(source_markers=[correction_marker_system], ...)
    
    # 两个 packet 的 source key 部分应相同(因为 marker kind 相同)
    assert packet_pending.source_key() == packet_system.source_key()
```

### 4.2 R2 — metadata 红线不误杀 AP-native context_tokens / context_tags

```python
# v3.3c 区分清单
FORBIDDEN_DESIGN_METADATA_FIELDS = {
    "style_tag",
    "context_tag",
    "design_note",
}

# AP-native 既有 evidence(允许,经统计学到)
ALLOWED_AP_NATIVE_EVIDENCE_FIELDS = {
    "context_tokens",     # 既有 Phase X 学到的
    "context_tags",       # 既有学习证据
    "LearningEpisode.context_tags",
    "action_outcome.context_tags",
}


def check_metadata_routing_v3_3c(py_file_content: str) -> list:
    """v3.3c: 只禁 forbidden 字段,不误伤 allowed AP-native 字段."""
    violations = []
    
    # 扫所有 FORBIDDEN 字段在 routing 上下文
    for field in FORBIDDEN_DESIGN_METADATA_FIELDS:
        # if x == "style_tag" / dict[style_tag] / .get("style_tag") / getattr(obj, "style_tag")
        # 同 v3.2b 的 4 种模式 + 两步路由
        ...
    
    # AP-native context_tokens / context_tags 即使在 if/match 中也允许
    # 因为它们是经学习的 evidence,不是设计时硬编码的 tag
    return violations
```

测试 R2:
```python
def test_redline_does_not_flag_apnative_context_tokens():
    """R2: context_tokens 经统计学到,不应被误判."""
    snippet = """
    if "math_context" in episode.context_tokens:
        adjust_action_outcome_evidence(...)
    """
    violations = check_metadata_routing_v3_3c(snippet)
    assert len(violations) == 0
```

### 4.3 R3 — pseudonymous ID 拒绝非字符串项

```python
# apv3test/util/pseudonymous_id.py v3.3c

def _canonicalize_input_v3_3c(
    text_or_seq: Union[str, Sequence[str]],
) -> str:
    """v3.3c: 严格拒绝非字符串项."""
    if isinstance(text_or_seq, str):
        normalized = {
            "schema": _CANONICAL_SCHEMA_VERSION,
            "kind": "scalar",
            "value": text_or_seq,
        }
    elif isinstance(text_or_seq, (tuple, list)):
        # R3: 严格检查每个元素必须 str
        for i, v in enumerate(text_or_seq):
            if not isinstance(v, str):
                raise TypeError(
                    f"Sequence item at index {i} must be str, got {type(v).__name__}: {v!r}"
                )
        normalized = {
            "schema": _CANONICAL_SCHEMA_VERSION,
            "kind": "sequence",
            "values": list(text_or_seq),  # 不再 str() 强转
        }
    else:
        raise TypeError(...)
    
    return json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


# 存储扩到 32 hex(R3)
def compute_pseudonymous_identifier_v3_3c(
    text_or_seq,
    state_dir: Path = Path("state"),
    storage_length: int = 32,  # R3: 默认 32 hex 而非 16
) -> str:
    canonical = _canonicalize_input_v3_3c(text_or_seq)
    salt = get_or_create_install_salt(state_dir)
    h = hmac.new(salt, canonical.encode("utf-8"), hashlib.sha256)
    return h.hexdigest()[:storage_length]


def compute_pseudonymous_display(identifier: str, display_length: int = 16) -> str:
    """UI 显示用,但 identity 仍是完整 32 hex."""
    return identifier[:display_length]
```

测试 R3:
```python
def test_pseudonymous_id_rejects_non_string_items():
    with pytest.raises(TypeError):
        compute_pseudonymous_identifier_v3_3c([1])
    with pytest.raises(TypeError):
        compute_pseudonymous_identifier_v3_3c([None])
    with pytest.raises(TypeError):
        compute_pseudonymous_identifier_v3_3c([{"x": "y"}])


def test_storage_id_length_32_hex():
    id = compute_pseudonymous_identifier_v3_3c("test")
    assert len(id) == 32
```

### 4.4 R4 — held-out event_id 不进 AP state

```python
# runtime/cognitive/curriculum/held_out_pool.py v3.3c

class HeldOutEventPool_v3_3c:
    def sample_probe_events_for_evaluation_v3_3c(self, n: int) -> list[NormalizedSAEventPublic]:
        """
        R4: 返回给 AP 的 event 不含 event_id.
        AP 收到的是 raw sensor content,event_id 只在 evaluator 外部 map.
        """
        full_events = random.sample(self.held_out_events, min(n, len(self.held_out_events)))
        # 返回 public view,剥掉 event_id
        public_events = [
            NormalizedSAEventPublic(
                kind=e.kind,
                content=e.content,
                # NO event_id!
            )
            for e in full_events
        ]
        # 内部仍保留 event_id → evaluator metadata 映射(evaluator 用)
        return public_events
    
    def get_evaluator_metadata_for_public_event(self, public_event) -> EvaluatorMetadata:
        """evaluator 用 raw event content 反查 metadata,不通过 event_id."""
        # 通过 content hash 匹配
        for stored_event, meta in zip(self.held_out_events, self._external_evaluator_meta):
            if events_content_equal(stored_event, public_event):
                return meta
        return None
```

测试 R4:
```python
def test_ap_state_does_not_contain_held_out_event_id():
    pool = HeldOutEventPool_v3_3c()
    for i in range(10):
        pool.add_during_curriculum(mock_raw_event(i), mock_meta(i), k_fold_index=i)
    
    public_events = pool.sample_probe_events_for_evaluation_v3_3c(n=5)
    state_pool = StatePool()
    for ev in public_events:
        state_pool.observe_external(ev)
    
    state_str = str(state_pool.snapshot())
    
    # 检查 AP state 不含任何 32-hex event_id
    import re
    hex_ids_in_state = re.findall(r'\b[0-9a-f]{32}\b', state_str)
    assert len(hex_ids_in_state) == 0, f"Event ids leaked into AP state: {hex_ids_in_state}"


def test_evaluation_still_works_via_external_map():
    """R4 不破坏 evaluator."""
    pool = HeldOutEventPool_v3_3c()
    pool.add_during_curriculum(mock_event_target_cat(), mock_meta(target="cat"), k_fold_index=0)
    
    public = pool.sample_probe_events_for_evaluation_v3_3c(n=1)[0]
    
    # evaluator 仍能查 meta
    meta = pool.get_evaluator_metadata_for_public_event(public)
    assert meta.target == "cat"
```

### 4.5 R5 — DraftGrid 随机化变量只在 evaluator 外部

```python
# v3.3c 强化(已隐含,但需明文)

class CurriculumEvaluatorMetadata_v3_3c:
    """
    R5: chosen_origin / spacing / digit_width 是 evaluator 私有,
    永不进 AP state.
    """
    # evaluator-private
    chosen_origin_row: int  # NOT in AP state
    chosen_origin_col: int  # NOT in AP state
    chosen_spacing: int     # NOT in AP state
    digit_width_a: int      # NOT in AP state
    digit_width_b: int      # NOT in AP state
    # ...


# AP state 只能看到的字段
class APStateSchema_DraftGrid:
    """AP 实际能看到的 grid 状态字段."""
    rows: int
    cols: int
    cells: dict  # 仅 char + tick + revisions
    char_focus: DraftCharFocus  # 字焦点状态
    # 严禁含:origin / spacing / digit_width
```

测试 R5:
```python
def test_teacher_off_validation_ap_state_no_curriculum_vars():
    """R5: teacher-off 时 AP state 不含 evaluator 私有字段."""
    run_teacher_off_validation_episode(problem=(23, 47), origin=(2, 5))
    
    ap_state_str = str(get_ap_state_snapshot())
    
    forbidden_fields = ["chosen_origin", "origin_row", "origin_col",
                        "chosen_spacing", "digit_width"]
    for field in forbidden_fields:
        assert field not in ap_state_str, f"R5 violation: {field} in AP state"
```

### 4.6 R6 — 数学 fact SA id 必须 opaque

```python
# runtime/cognitive/curriculum/math_fact_registry.py v3.3c

def generate_opaque_fact_id() -> str:
    """R6: fact SA id 不含可解析语义."""
    return f"fact::{secrets.token_hex(16)}"  # 完全随机


# 课程包仍可写 readable label 用于教学/文档
class MathFactPackage:
    sa_id: str  # opaque,如 "fact::a3f5e9c2d1b08e4f..."
    readable_label: str  # "3+7=10",仅用于人类可读
    # opaque id 不含 "3" "7" "10" 信息


def check_no_runtime_parsing_of_fact_id():
    """R6 redline: runtime 不许 parse fact id 字串."""
    forbidden_patterns = [
        r'fact::add::',
        r'fact::multiply::',
        r'fact::subtract::',
        r'fact::\w+::\d',  # 任何含运算符或数字的 fact id parsing
    ]
    for py_file in Path("runtime/cognitive").rglob("*.py"):
        content = py_file.read_text()
        for pat in forbidden_patterns:
            if re.search(pat, content):
                # 是否在 audit/docs 路径?豁免
                if not is_audit_or_docs(py_file):
                    raise ValueError(f"{py_file}: fact id parsed via {pat}")
```

测试 R6:
```python
def test_label_bijection_renames_facts_behavior_unchanged():
    """R6: 把所有 fact id 改名,行为不变."""
    # 记录原行为
    original_q = solve_problem(problem=(23, 47))
    
    # 重命名所有 fact id
    rename_all_fact_ids_with_random_mapping()
    
    # 行为应一致
    new_q = solve_problem(problem=(23, 47))
    assert original_q.committed_answer == new_q.committed_answer
```

### 4.7 R7 — substrate + 字焦点 backoff

```python
# v3.3c 整合 packet_key
# exact key:content + substrate + focus_shape + feeling
# content+source:content + substrate(不含 focus)
# source+feeling:substrate + feeling(不含 content)
# content_only:仅 content(允许跨 substrate 转移)← R7 关键
# action_global:仅 action

# 关键:content_only 层让"教师教的 23"经验也能轻微帮助"自己写的 23"
# 但不强,因为更精确的 exact 层是分离的
```

测试 R7:
```python
def test_substrate_isolation_but_content_backoff_works():
    """R7: substrate 隔离,但 content backoff 仍可发生."""
    # 教学 external_visual 学到"23 → 某 action"
    teach_with_external_visual(content="23", action="wait", reward=1.0)
    
    # 测试 self_draft 看到 23
    self_pkt = make_packet_with_substrate("23", PerceivedSource.SELF_DRAFT_GRID)
    q = q_table.query(self_pkt, "wait")
    
    # exact 层 q = 0(没数据)
    # content_only 层 q > 0(经 content backoff)
    # 综合 q 在 [0, 0.5)
    assert 0 < q < 0.5  # 有少量正向 transfer,但不强


def test_punishing_self_draft_does_not_erase_external_visual():
    """R7: 惩罚自草稿不毁外感学习."""
    teach_with_external_visual(content="火", action="逃", reward=1.0)
    
    # 后续惩罚自草稿
    self_pkt = make_packet_with_substrate("火", PerceivedSource.SELF_DRAFT_GRID)
    q_table.update(self_pkt, "逃", outcome=-1.0)
    
    # external_visual 的 Q 不受影响
    external_pkt = make_packet_with_substrate("火", PerceivedSource.EXTERNAL_VISUAL)
    q_external = q_table.query(external_pkt, "逃")
    assert q_external > 0.5
```

### 4.8 R8 — gate 数量按实际清单

不再写"14 项 must-fix"硬数字。Phase 13.0 完成报告必须**列出实际执行的 gate 清单**:

```markdown
# FinalReport_Phase13_0.md(模板 v3.3c)

## Gates Executed

| Gate ID | Description | Status |
|---|---|---|
| F1 | privacy canary scan | ✅ PASS |
| F2 | pseudonymous HMAC | ✅ PASS |
| F3 | trust gate held-out | ✅ PASS |
| F4 | multi-teacher awaiting | ✅ PASS |
| F5 | metadata AST scan | ✅ PASS |
| F6 | held-out raw sensor SA | ✅ PASS |
| E1 | JSON canonicalization | ✅ PASS |
| E2 | CORRECTION + status enum | ✅ PASS |
| E3 | no bool fields | ✅ PASS |
| E4 | opaque event_id | ✅ PASS |
| E5 | AST 4 new patterns | ✅ PASS |
| R1 | status not in learning paths | ✅ PASS |
| R2 | context_tokens not flagged | ✅ PASS |
| R3 | reject non-str items | ✅ PASS |
| R4 | event_id not in AP state | ✅ PASS |

Total: 15 gates executed, 15 PASS.
```

报告以**实际列表**为准,而非文案中说"14 项"。

---

## 第 5 章 v3.3c 实施清单更新

### 5.1 Phase 13.0 gates(实际清单)

```
F1 / F2 / F3 / F4 / F5 / F6  (v3.2a 6 项)
E1 / E2 / E3 / E4 / E5  (v3.2b 5 项)
R1 / R2 / R3 / R4 / R8  (v3.2c 5 项,R5/R6/R7 在 13.5b.0)
```

### 5.2 Phase 13.5b.0 gates(数学 substrate)

```
E6 — 范式不变量教学,无 fixed coordinate yaml
E7 — 事实涌现,无 column_sum 算术
E8 — substrate 维度进 packet_key
R5 — origin/spacing/digit_width 不入 AP state
R6 — fact SA id opaque
R7 — substrate backoff + Q 稀疏度监控
C1 — DraftCharFocus EntitySA 实现
C2 — 8 个字焦点 actions 实现
C3 — Cell percept R 焦点调制
C4 — read_at_focus + 自动 scan 双路径
C5 — 字焦点状态进 packet_key(shape 不含绝对位置)
C6 — 字焦点 SDPL 学习路径验证
C7 — 同问题不同 origin 焦点移动相对一致(范式不变量)
```

### 5.3 Phase 13.5b.1+(数学正式课程)

按 v3.3 §2-§8,**所有教学路径必须经过字焦点**(无 read_grid_cell 直接调用绕过焦点)。

---

## 第 6 章 v3.3c 总结

### 6.1 v3.3 → v3.3c 关键升级

| 维度 | v3.3 | v3.3c |
|---|---|---|
| 草稿读机制 | `read_grid_cell(row, col)` 直接读 | **必须经字焦点**:`move_char_focus_to` + `read_at_focus` 或自动 scan |
| 焦点能量 | 无 | 焦点附近 percept R 高,远处衰减(对偶视焦点)|
| 范式学习 | 担心系统不知道"算哪两个" | 字焦点 + 列形状焦点,系统能"专注列内两个数字" |
| 行动竞争 | 静态 | 字焦点 8 类 actions 参与 SDPL 竞争 |
| packet_key | 含 content/source/feeling | 加焦点 shape(不加绝对位置) |
| 学习路径 | 不明 | SDPL emerge:相对移动模式 |

### 6.2 银子老师洞察的工程价值

**字焦点不只解决竖式数学**,它是**所有空间排列范式的通用基础**:
- 数学竖式(列对齐计算)
- 表格读写(行/列扫描)
- markdown 排版(段落焦点)
- 棋类游戏(棋格焦点)
- 代码导航(行号焦点)

**和视焦点一样,字焦点是 v14 缺失的通用能力**,补完后所有 2D 文本任务都受益。

### 6.3 数学复现可行性重新评估

加入字焦点后:
- 数感、九九事实库:**绿**(不需字焦点)
- 两位数竖式:**绿**(字焦点列形状 + fact 召回 + 视觉范式)
- 乘法竖式:**绿-黄**(字焦点 + 部分积 + 位移)
- 长除法:**黄**(字焦点 + 多步时序)
- 应用题:**黄**(文本理解走 1D,关系识别需大量教学)
- 列方程:**黄-红**(abstract_vocab + deliberative 真考验)

**字焦点把两位数竖式从"红"变成"绿"**。这是核心解锁。

---

## 第 7 章 给 Codex 的实施指令(v3.3c)

1. **七稿配合**:v3 + v3.1 + v3.2 + v3.2a + v3.2b/3.3a + v3.2c/3.3b + v3.3c(本稿)
2. **Phase 13.5b.0 必须先做字焦点(C1-C7),再做其他数学子阶段**
3. **DraftCharFocus 复用 EntitySA::focus family**,不新增 SA type
4. **能量调制函数复用 Phase 8.7 数学**,新 grid 适配层
5. **字焦点 actions 经 SDPL 路径学习**,无硬编码竖式步骤
6. **packet_key 含字焦点 shape,不含绝对位置**
7. **read_grid_cell 直接调用必须经字焦点路径**(redline 扫直接调用绕过焦点)
8. **R1-R8 全部落实**,Phase 13.0 报告列实际 gate 清单
9. **任何对 v3.3c 的偏离先停下问 Claude/银子老师**

---

## 第 8 章 给 Codex 对抗审阅者的指引

请重点审:

1. **C1 DraftCharFocus** 复用 EntitySA::focus family 是否真无歧义?Phase 8.7 视焦点是否真同结构可复用?
2. **C3 能量调制函数** 用 Phase 8.7 数学,是否真直接 carry over?有无遗漏的 grid 离散化问题?
3. **C5 packet_key 含 shape 不含位置** 是否真能保证相对范式学习?会不会丢失关键信息?
4. **R7 Q-key 稀疏度** 加入 substrate + focus shape 后,长跑会否爆?monitor 阈值合理吗?
5. **R6 fact id opaque** 是否真能 label-bijection 测试?如果系统从教学时学到了"3+7=10",换 id 后能继续吗?
6. **C7 范式不变量验收** sequence_similarity ≥ 0.85 阈值是否合理?如何避免假阳性?

---

## 第 9 章 银子老师审稿建议

请审:

1. **字焦点设计是否符合预期**?有没有遗漏的"焦点行为"(如缩放/双焦点等)?
2. **能量调制(高斯衰减)是否符合"周围仍可见"的人类感受**?系数是否需要调?
3. **packet_key 不含绝对位置但 percept metadata 含相对位置** — 这个边界你接受吗?
4. **字焦点是 EntitySA**(可持久),还是 MarkerSA(瞬态)?我选 EntitySA,你认同吗?
5. **Phase 13.5b.0 必须做完整字焦点验证**(C1-C7 全 PASS),才能进数学子阶段。同意吗?

---

— 银子老师 / Claude
— 2026-06-18

下一步:Codex 对抗审阅 v3.3c → 实施 Phase 13.0(F1-F6 + E1-E5 + R1-R4/R8)→ Phase 13.5b.0(E6-E8 + R5-R7 + C1-C7 字焦点)→ 进数学课程包。
