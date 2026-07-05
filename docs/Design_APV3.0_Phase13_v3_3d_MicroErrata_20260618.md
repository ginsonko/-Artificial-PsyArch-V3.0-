# APV3.0 Phase 13 — v3.3d Micro Errata

日期: 2026-06-18
作者: 银子老师 / Claude
状态: **Codex 审 v3.3c 后识别 5 个实施前必修问题(其中 D1 D2 是我设计中的灾难性缺陷,与 v3.3 fixed coordinate 同源)。v3.3d 是 v3.3c 的精准补丁,根治 5 项后才能进 Phase 13.0。Codex 合同最终形态 = v3 + v3.1 + v3.2 + v3.2a + v3.2b/3.3a + v3.2c/3.3b + v3.3c + v3.3d(本稿)八稿合一。**

前作:
- [v3.3c 字焦点 + Codex 整合](Design_APV3.0_Phase13_v3_3c_CharFocusAndMicroErrata_20260618.md)
- [v3.2c/3.3b Codex Micro Errata](Design_APV3.0_Phase13_v3_2c_v3_3b_MicroErrata_20260618.md)

许可:AGPL-3.0-or-later
原架构设计:银子老师

---

## 0. v3.3d 修复总览

| 编号 | 问题 | 严重度 | 来源 |
|---|---|---|---|
| **D1** | `draft_cell::{row}_{col}::{char}` 在 percept content 泄漏绝对坐标 | **CRITICAL BLOCKER** | v3.3c §1.4 自身缺陷 |
| **D2** | COLUMN 焦点同列全高能 → 长除法 flooding | **BLOCKER** | v3.3c §1.3 数学错误 |
| **D3** | `move_char_focus_to(row, col)` 仍可能成课程坐标表 | SERIOUS | v3.3c §2.1 设计松懈 |
| **D4** | R2 对 `context_tokens` 放得太宽,字面量分支仍是硬路由 | SERIOUS | v3.3c §4.2 边界不清 |
| **D5** | held-out content equality 反查歧义(同 content 不同 episode) | SERIOUS | v3.3c §4.4 设计错误 |

**1 CRITICAL + 2 BLOCKER + 2 SERIOUS**。其中 D1 D2 都是我 v3.3c 自己造成的新坑,**与 v3.3 fixed coordinate 同源(我又一次让"绝对坐标"潜伏到设计里**)。

---

## 第 1 章 D1 根治 — Percept content 不含绝对坐标

### 1.1 我的错(诚实承认)

v3.3c §1.4 我写:

```python
percept_sa = spawn_percept_sa(
    content=f"draft_cell::{row}_{col}::{cell.char}",  # ← 灾难:绝对 row/col 进 content
    real_energy=modulated_R,
    tick=tick,
)
spawn_perceived_marker_v3_3a(
    target_sa_id=percept_sa.sa_id,
    metadata={
        "grid_relative_position_to_focus": {"dr": ..., "dc": ...},  # 相对位置
    },
)
```

我口口声声说"packet_key 不含绝对位置,系统学相对范式",**但 percept content 本身已经把绝对 (3, 5) 编码进 SA id**。

后果:
- 在 (3, 5) 看到 "7" → SA id = `draft_cell::3_5::7`,content_key 含 `(draft_cell::3_5::7, R_bucket)`
- 在 (10, 8) 看到 "7" → SA id = `draft_cell::10_8::7`,content_key 不同
- **同一字符不同位置完全不通用**,系统无法泛化

**这是 v3.3 fixed coordinate 的精确同型错误**,我又一次让绝对坐标潜伏进设计。Codex 一眼看穿。

### 1.2 v3.3d 根治:认知内容只含字符 + 相对位置

```python
# apv3test/runtime/draft_grid_percept_emit.py v3.3d

import secrets


def emit_draft_grid_percepts_v3_3d(
    state_pool,
    grid: DraftGrid,
    focus: DraftCharFocus,
    tick: int,
) -> list[PerceptSA]:
    """
    v3.3d 根治 D1:
    
    - SA id 不含绝对 row/col(用 opaque hash + 字符)
    - percept content 只含: char + relative_position_to_focus + focus_shape
    - 绝对 row/col **只进 audit/render 的 metadata**,不进 SDPL content
    """
    percepts = []
    base_R = load_constant("draft_grid.cell_percept_base_R")
    
    for (row, col), cell in grid.cells.items():
        if cell.char == " ":
            continue
        
        modulated_R = compute_cell_percept_R_with_char_focus_v3_3d(
            row, col, focus, base_R,
        )
        
        if modulated_R < load_constant("draft_grid.cell_percept_emit_threshold"):
            continue
        
        # === v3.3d: SA id opaque,不编码绝对位置 ===
        # opaque per-emission id(相同 cell 多次 emit 也不同 id)
        opaque_suffix = secrets.token_hex(8)
        percept_sa_id = f"percept::draft::{opaque_suffix}"
        
        # === content 只含字符 + 相对位置 ===
        relative_position = compute_relative_position_to_focus(row, col, focus)
        
        percept_sa = spawn_percept_sa(
            sa_id=percept_sa_id,
            content_kind="draft_cell_char",
            cognitive_content={
                # SDPL/composed_vocab 看的是这些
                "char": cell.char,
                "rel_dr": relative_position.dr_bucket,  # bucket 化,不绝对
                "rel_dc": relative_position.dc_bucket,
                "focus_shape": focus.focus_shape.value,
                "within_focus": relative_position.within_focus,
            },
            real_energy=modulated_R,
            tick=tick,
        )
        
        # === audit/render metadata(不进 cognitive)===
        percept_sa.audit_metadata = {
            "absolute_row": row,
            "absolute_col": col,
            "cell_written_at_tick": cell.written_at_tick,
            "cell_revision_count": cell.revision_count,
        }
        
        # PERCEIVED marker with substrate(沿用 v3.3a)
        spawn_perceived_marker_v3_3a(
            target_sa_id=percept_sa.sa_id,
            tick=tick,
            substrate=PerceivedSource.SELF_DRAFT_GRID,
            metadata={
                # 这里仍可放些 cognitive metadata,但绝不放绝对坐标
                "modulation_applied": modulated_R / base_R,
            },
        )
        percepts.append(percept_sa)
    
    return percepts
```

### 1.3 相对位置 bucket 量化

绝对 `(dr, dc)` 仍可能 partition 太细。v3.3d 用 bucket:

```python
def compute_relative_position_to_focus(
    cell_row: int,
    cell_col: int,
    focus: DraftCharFocus,
) -> RelativePosition:
    """v3.3d: 相对位置经 bucket,防 partition 爆炸."""
    dr = cell_row - focus.focus_row  # 可负
    dc = cell_col - focus.focus_col
    
    # Bucket: 同(0) / 紧邻(±1) / 近(±2~3) / 远(>3)
    def to_bucket(delta: int) -> str:
        if delta == 0:
            return "same"
        elif abs(delta) == 1:
            return "adjacent_" + ("up" if delta < 0 else "down")
        elif abs(delta) <= 3:
            return "near_" + ("up" if delta < 0 else "down")
        else:
            return "far_" + ("up" if delta < 0 else "down")
    
    # row delta 转 vertical bucket
    vertical = to_bucket(dr)  # same/adjacent_up/near_down/...
    # col delta 转 horizontal bucket
    def to_horizontal(delta: int) -> str:
        if delta == 0:
            return "same"
        elif abs(delta) == 1:
            return "adjacent_" + ("left" if delta < 0 else "right")
        elif abs(delta) <= 3:
            return "near_" + ("left" if delta < 0 else "right")
        else:
            return "far_" + ("left" if delta < 0 else "right")
    horizontal = to_horizontal(dc)
    
    within_focus = focus.is_within_focus(cell_row, cell_col)
    
    return RelativePosition(
        dr_bucket=vertical,
        dc_bucket=horizontal,
        within_focus=within_focus,
    )
```

### 1.4 验收测试

```python
def test_same_char_different_positions_share_content_key():
    """
    D1 验证:同字符在不同绝对位置,
    content_key 应有相同部分(经 bucket 量化).
    """
    grid = DraftGrid(rows=20, cols=20)
    grid.write_at(3, 5, "7", tick=1)
    grid.write_at(10, 8, "7", tick=1)
    
    focus_a = DraftCharFocus(focus_row=3, focus_col=5, focus_shape=FocusShape.CELL)
    focus_b = DraftCharFocus(focus_row=10, focus_col=8, focus_shape=FocusShape.CELL)
    
    percepts_a = emit_draft_grid_percepts_v3_3d(state_pool_a, grid, focus_a, tick=1)
    percepts_b = emit_draft_grid_percepts_v3_3d(state_pool_b, grid, focus_b, tick=1)
    
    # 找到 "7" 的 percept(各自焦点位置)
    p_a = next(p for p in percepts_a if p.cognitive_content["char"] == "7" 
               and p.cognitive_content["rel_dr"] == "same" 
               and p.cognitive_content["rel_dc"] == "same")
    p_b = next(p for p in percepts_b if p.cognitive_content["char"] == "7"
               and p.cognitive_content["rel_dr"] == "same"
               and p.cognitive_content["rel_dc"] == "same")
    
    # 关键:cognitive_content 相同(只差 opaque id)
    assert p_a.cognitive_content == p_b.cognitive_content
    
    # 但 audit_metadata 不同(各自绝对坐标)
    assert p_a.audit_metadata["absolute_row"] != p_b.audit_metadata["absolute_row"]


def test_sdpl_packet_key_does_not_contain_absolute_coordinates():
    """D1: packet_key 完全无绝对坐标."""
    grid = DraftGrid(rows=20, cols=20)
    grid.write_at(3, 5, "7", tick=1)
    
    focus = DraftCharFocus(focus_row=3, focus_col=5)
    percepts = emit_draft_grid_percepts_v3_3d(state_pool, grid, focus, tick=1)
    packet = make_packet(content_sas=percepts, ...)
    
    pkt_key = packet.packet_key()
    pkt_str = str(pkt_key)
    
    # 不应出现具体绝对坐标
    forbidden = ["3_5", "5_3", "row=3", "col=5", "(3, 5)"]
    for s in forbidden:
        assert s not in pkt_str, f"D1 violation: absolute coord '{s}' in packet_key"


def test_audit_renders_with_absolute_coordinates():
    """D1: audit/render 仍能用绝对坐标(它们在 audit_metadata)."""
    percepts = emit_draft_grid_percepts_v3_3d(state_pool, grid, focus, tick=1)
    
    audit_view = render_audit_view(percepts)
    # audit 可以显示具体坐标
    assert "3" in audit_view  # row
    assert "5" in audit_view  # col
```

---

## 第 2 章 D2 根治 — COLUMN/ROW 焦点各向异性衰减

### 2.1 我的错

v3.3c §1.3:

```python
if focus.focus_shape == FocusShape.COLUMN:
    relevant_distance = dc  # 只看 dc → 同列 dc=0 → 整列满能量
```

后果:在 10 行长除法网格中,COLUMN 焦点让整列 10 个 cell 都 modulation=1.0,等于没焦点。Codex 抓到。

### 2.2 v3.3d 根治:各向异性双轴衰减

```python
# runtime/cognitive/attention/draft_focus_modulation.py v3.3d

import math


def compute_cell_percept_R_with_char_focus_v3_3d(
    cell_row: int,
    cell_col: int,
    focus: DraftCharFocus,
    base_R: float,
) -> float:
    """
    v3.3d 各向异性焦点衰减:
    
    - CELL: 圆形衰减(沿用 v3.3c)
    - COLUMN: 沿轴主衰减弱(列内仍有窗口),跨轴主衰减强(跨列衰减快)
    - ROW: 对偶 COLUMN
    - RECT: 矩形 + 双轴衰减
    
    完全对应 Phase 8.7 视焦点的"中央凹高分辨率 + 周边低分辨率"机制.
    """
    dr = abs(cell_row - focus.focus_row)
    dc = abs(cell_col - focus.focus_col)
    
    # 衰减参数(yaml 化)
    span = focus.focus_span
    primary_sigma = load_constant("draft_grid.focus_primary_axis_sigma")  # 默认 3.0
    secondary_sigma = load_constant("draft_grid.focus_secondary_axis_sigma")  # 默认 1.0
    peripheral_floor = load_constant("draft_grid.focus_peripheral_floor")  # 默认 0.05
    
    if focus.focus_shape == FocusShape.CELL:
        # 各向同性圆形衰减
        distance = math.sqrt(dr**2 + dc**2)
        if distance <= span:
            modulation = 1.0
        else:
            sigma = primary_sigma  # 各向同性
            modulation = math.exp(-(distance - span)**2 / (2 * sigma**2))
    
    elif focus.focus_shape == FocusShape.COLUMN:
        # === v3.3d 修复 D2 ===
        # 主轴(同列):宽窗口,慢衰减(让列内多 cell 可见)
        # 跨轴(跨列):窄窗口,快衰减(确保 focus 在某列)
        # 这才符合"我看这一列,但还能看到附近列"的人类感受
        
        # 跨列(secondary axis)按 dc 衰减
        if dc == 0:
            cross_modulation = 1.0
        elif dc <= span:
            cross_modulation = 1.0  # span 内仍满能量
        else:
            cross_modulation = math.exp(-(dc - span)**2 / (2 * secondary_sigma**2))
        
        # 同列(primary axis)按 dr 衰减(列内仍有窗口,不是无限高能)
        if dr <= span:
            along_modulation = 1.0
        else:
            along_modulation = math.exp(-(dr - span)**2 / (2 * primary_sigma**2))
        
        # 综合
        modulation = cross_modulation * along_modulation
    
    elif focus.focus_shape == FocusShape.ROW:
        # 对偶 COLUMN: 主轴 = dc(同行延伸),跨轴 = dr(跨行衰减)
        if dr == 0:
            cross_modulation = 1.0
        elif dr <= span:
            cross_modulation = 1.0
        else:
            cross_modulation = math.exp(-(dr - span)**2 / (2 * secondary_sigma**2))
        
        if dc <= span:
            along_modulation = 1.0
        else:
            along_modulation = math.exp(-(dc - span)**2 / (2 * primary_sigma**2))
        
        modulation = cross_modulation * along_modulation
    
    elif focus.focus_shape == FocusShape.RECT:
        # 矩形:dr 和 dc 各自按 span 衰减
        if dr <= span and dc <= span:
            modulation = 1.0
        else:
            sigma = primary_sigma
            outside_dr = max(0, dr - span)
            outside_dc = max(0, dc - span)
            modulation = math.exp(-(outside_dr**2 + outside_dc**2) / (2 * sigma**2))
    
    # peripheral floor: 远但不归零(类似 Phase 8.7 peripheral vision)
    modulation = max(peripheral_floor, modulation)
    
    return base_R * modulation * focus.attention_energy
```

### 2.3 yaml 常量(扩 apv3_constants.yaml)

```yaml
# v3.3d 新增
draft_grid:
  cell_percept_base_R: 0.5                     # @experimental
  cell_percept_emit_threshold: 0.05            # @experimental
  focus_primary_axis_sigma: 3.0                # @experimental — 主轴(同列/同行)衰减
  focus_secondary_axis_sigma: 1.0              # @experimental — 跨轴(跨列/跨行)快衰减
  focus_peripheral_floor: 0.05                 # @structural — 类 Phase 8.7 peripheral vision
```

### 2.4 验收

```python
def test_column_focus_does_not_flood_entire_column():
    """D2: COLUMN 焦点不应让 10 行全列都满能量."""
    grid = DraftGrid(rows=20, cols=20)
    # 在第 5 列写 10 个数字
    for r in range(10):
        grid.write_at(r, 5, str(r), tick=1)
    
    # COLUMN 焦点在 (3, 5)
    focus = DraftCharFocus(focus_row=3, focus_col=5, focus_shape=FocusShape.COLUMN, focus_span=1)
    
    energies = []
    for r in range(10):
        R = compute_cell_percept_R_with_char_focus_v3_3d(r, 5, focus, base_R=0.5)
        energies.append(R)
    
    # 焦点行附近高,远行衰减
    # 行 0-1(span=1)满能量
    # 行 4 比行 2 衰减(因为离 focus_row=3 远)
    assert energies[3] > energies[6]  # focus_row vs 距离 3
    assert energies[6] > energies[9]  # 距离 3 vs 距离 6
    # 远端衰减 ≥ 50%
    assert energies[9] < energies[3] * 0.5


def test_column_focus_still_higher_than_adjacent_columns():
    """D2: COLUMN 焦点仍要让同列比跨列高(否则不算列焦点)."""
    grid = DraftGrid(rows=20, cols=20)
    grid.write_at(3, 5, "X", tick=1)  # 焦点列
    grid.write_at(3, 7, "X", tick=1)  # 跨 2 列
    
    focus = DraftCharFocus(focus_row=3, focus_col=5, focus_shape=FocusShape.COLUMN, focus_span=1)
    
    R_same_col = compute_cell_percept_R_with_char_focus_v3_3d(3, 5, focus, base_R=0.5)
    R_adj_col = compute_cell_percept_R_with_char_focus_v3_3d(3, 7, focus, base_R=0.5)
    
    # 同列焦点行 > 跨列焦点行
    assert R_same_col > R_adj_col


def test_row_focus_does_not_flood_entire_row():
    """D2 对偶:ROW 焦点不应让 20 列全行满能量."""
    # ... 同 column 测试结构,axis 互换
```

---

## 第 3 章 D3 根治 — move_char_focus_to 只作底层原语

### 3.1 v3.3c 风险

v3.3c §2.1 列出 `move_char_focus_to(row, col)` 作为基本 action。如果教师课程包给"做 (23+47) 时,在 tick 5 应该 `move_char_focus_to(2, 3)`",**系统仍会背绝对坐标**,即使是经 SDPL 学。

### 3.2 v3.3d 根治:多级 action 优先级

```python
# v3.3d action 层级

# === Tier 1: 高层原语(教学优先使用)===
class HighLevelFocusActions(str, Enum):
    SHIFT_FOCUS = "char_focus_shift"               # 相对移动(dr, dc)
    SCAN_ROW_FROM_FOCUS = "char_focus_scan_row_from"   # 从焦点开始扫行
    SCAN_COLUMN_FROM_FOCUS = "char_focus_scan_column_from"
    MOVE_FOCUS_TO_VISUAL_POINTER = "char_focus_move_to_pointer"  # 移到教师指针视觉
    MOVE_FOCUS_TO_SALIENT_CELL = "char_focus_move_to_salient"  # 移到最显著 cell
    
    # 形状切换(无坐标)
    SHAPE_CELL = "char_focus_shape_cell"
    SHAPE_ROW = "char_focus_shape_row"
    SHAPE_COLUMN = "char_focus_shape_column"
    SHAPE_RECT = "char_focus_shape_rect"
    
    # 范围调整(无坐标)
    EXPAND_SPAN = "char_focus_expand_span"
    CONTRACT_SPAN = "char_focus_contract_span"


# === Tier 2: 底层原语(可在非教学路径使用)===
class LowLevelFocusActions(str, Enum):
    MOVE_TO_ABSOLUTE = "char_focus_move_to_absolute"  # (row, col),底层使用


# === 教学路径只能用 Tier 1 ===
TEACHING_ALLOWED_ACTIONS = set(HighLevelFocusActions) - {
    HighLevelFocusActions.MOVE_FOCUS_TO_VISUAL_POINTER,  # 这个也涉及目标
}

# Teaching 时课程包不许出现 Tier 2 actions
def validate_curriculum_package_no_absolute_focus_moves(package):
    """D3: 课程包验证 — 不许包含 absolute focus move."""
    for content_item in package.content:
        for episode in content_item.teaching_episodes:
            for action in episode.expected_actions_or_demonstration:
                if action.kind == "char_focus_move_to_absolute":
                    raise ValueError(
                        f"D3 violation: course package {package.package_id} uses "
                        f"absolute focus move in teaching. Use SHIFT or visual_pointer."
                    )
```

### 3.3 视觉指针 grounding(教学主路径)

教师 demonstration 用 **视觉手指/光标** 指向某 cell,系统经 PERCEIVED EXTERNAL_VISUAL 看到指针位置,然后用 `MOVE_FOCUS_TO_VISUAL_POINTER` action 把字焦点移到指针对应位置。

```python
def select_focus_action_for_teaching_v3_3d(state_pool, packet):
    """
    教学路径下的 focus action 选择.
    
    优先用相对 SHIFT 和视觉指针,
    底层 MOVE_TO_ABSOLUTE 仅在自主推理/纠错时使用.
    """
    # 检查是否有教师 visual pointer percept
    pointer_percept = state_pool.find_percept_by_substrate_and_kind(
        substrate=PerceivedSource.EXTERNAL_VISUAL,
        kind="teacher_pointer",
    )
    
    if pointer_percept is not None:
        # 主用 MOVE_TO_VISUAL_POINTER(grounding 到外部指针)
        return DraftTextAction(
            kind=HighLevelFocusActions.MOVE_FOCUS_TO_VISUAL_POINTER.value,
            visual_pointer_sa_id=pointer_percept.sa_id,
        )
    
    # 无指针时,用 SHIFT 相对移动
    return DraftTextAction(
        kind=HighLevelFocusActions.SHIFT_FOCUS.value,
        row_delta=...,  # 经 SDPL 学到的相对方向
        col_delta=...,
    )
```

### 3.4 验收 + 红线

```python
def check_no_absolute_focus_move_in_curriculum_yaml():
    """D3 红线:课程包 yaml 不许 char_focus_move_to_absolute."""
    for yaml_file in Path("config/curriculum/packages/math").rglob("*.yaml"):
        content = yaml.safe_load(yaml_file.read_text())
        violations = []
        # 递归查所有 action 节
        def scan(obj):
            if isinstance(obj, dict):
                if obj.get("action") == "char_focus_move_to_absolute":
                    violations.append(obj)
                for v in obj.values():
                    scan(v)
            elif isinstance(obj, list):
                for item in obj:
                    scan(item)
        scan(content)
        
        if violations:
            raise ValueError(f"{yaml_file}: D3 violation, found {len(violations)} absolute focus moves")


def test_teacher_off_validation_no_absolute_move_usage():
    """D3: teacher-off 下,系统行动 trace 中如有 absolute_move,需有合理 grounding."""
    trace = run_teacher_off_validation_episode(problem=(23, 47), origin=(2, 5))
    
    absolute_moves = [a for a in trace.actions if a.kind == "char_focus_move_to_absolute"]
    shift_moves = [a for a in trace.actions if a.kind == "char_focus_shift"]
    pointer_moves = [a for a in trace.actions if a.kind == "char_focus_move_to_pointer"]
    
    # 主体应是 shift + pointer,不应该全是 absolute
    high_level_count = len(shift_moves) + len(pointer_moves)
    total_focus_moves = high_level_count + len(absolute_moves)
    
    # 至少 70% 是 high-level
    assert high_level_count / max(1, total_focus_moves) >= 0.7
```

---

## 第 4 章 D4 根治 — context_tokens 字段允许但字面量分支禁止

### 4.1 v3.3c 的边界不清

v3.3c §4.2 写"AP-native context_tokens 即使在 if/match 中也允许"。Codex 抓到 `if "math_context" in episode.context_tokens` 仍是硬路由。

### 4.2 正确边界

| 模式 | 允许? | 理由 |
|---|---|---|
| `similarity(context_tokens, learned_vector)` | ✅ | 统计学相似度 |
| `context_tokens` 作 SDPL packet feature | ✅ | 经能量竞争 |
| `vocab = lookup_by_context_tokens(context_tokens)` | ✅(若 lookup 经学习)| 学到的关联 |
| `if "math_context" in episode.context_tokens:` | ❌ | **字面量分支** |
| `match context_tokens: case ["math_context"]:` | ❌ | match-case 字面量 |
| `routing_table[context_tokens[0]]` | ❌ | dict 路由 |
| `getattr(handler, context_tokens[0])` | ❌ | 动态路由 |

**规则**:**字段值参与计算 OK,字面量值参与分支不 OK**。

### 4.3 红线扩展

```python
# v3.3d 扩 metadata routing detector

def check_no_context_tokens_literal_branching():
    """D4 redline: 禁字面量 context_tokens 分支."""
    AST_PATTERNS_FORBIDDEN_FOR_AP_NATIVE_TOKENS = [
        # if "literal" in context_tokens
        # if "literal" in episode.context_tokens
        # if "literal" in xx.context_tokens
    ]
    
    # AST detector
    class ContextTokensLiteralBranchDetector(ast.NodeVisitor):
        def visit_Compare(self, node):
            # 检测 In 比较
            for op, comparator in zip(node.ops, node.comparators):
                if isinstance(op, ast.In):
                    # 左边是字面量?
                    if isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
                        # 右边访问 context_tokens?
                        if self._is_context_tokens_access(comparator):
                            self.violations.append(
                                f"L{node.lineno}: literal '{node.left.value}' in context_tokens - forbidden branch"
                            )
            self.generic_visit(node)
        
        def visit_Match(self, node):
            # match context_tokens: case [literal]:
            if self._is_context_tokens_access(node.subject):
                for case in node.cases:
                    # case 含字面量?
                    if self._case_has_literal(case.pattern):
                        self.violations.append(
                            f"L{case.pattern.lineno}: match-case literal on context_tokens"
                        )
            self.generic_visit(node)
        
        def visit_Subscript(self, node):
            # routing_table[context_tokens[0]]
            if isinstance(node.value, ast.Name):
                # 看 slice 是否含 context_tokens 元素访问
                if self._is_context_tokens_element_access(node.slice):
                    self.violations.append(
                        f"L{node.lineno}: dict route via context_tokens element"
                    )
            self.generic_visit(node)
        
        def _is_context_tokens_access(self, node) -> bool:
            """检测 xxx.context_tokens / context_tokens / xx.context_tags."""
            if isinstance(node, ast.Attribute):
                if node.attr in {"context_tokens", "context_tags"}:
                    return True
            if isinstance(node, ast.Name) and node.id in {"context_tokens", "context_tags"}:
                return True
            return False
    
    violations = []
    for py_file in glob("runtime/cognitive/**/*.py", recursive=True):
        tree = ast.parse(open(py_file).read())
        detector = ContextTokensLiteralBranchDetector()
        detector.visit(tree)
        for v in detector.violations:
            violations.append(f"{py_file}:{v}")
    return violations
```

### 4.4 测试

```python
def test_redline_blocks_literal_in_context_tokens():
    """D4: if 'math_context' in episode.context_tokens 应被红线拒."""
    snippet = """
def some_path(episode):
    if "math_context" in episode.context_tokens:
        do_x()
    """
    violations = check_no_context_tokens_literal_branching_from_source(snippet)
    assert len(violations) >= 1


def test_redline_allows_similarity_use():
    """D4: similarity(context_tokens, vec) 应被允许."""
    snippet = """
def some_path(episode, learned_vec):
    sim = similarity(episode.context_tokens, learned_vec)
    return sim
    """
    violations = check_no_context_tokens_literal_branching_from_source(snippet)
    assert len(violations) == 0


def test_redline_allows_context_tokens_in_packet():
    """D4: context_tokens 作 packet feature 允许."""
    snippet = """
def build_packet(episode):
    return LearningPacket(
        feeling_sas=[...],
        slot_context=[episode.context_tokens, ...],  # OK
    )
    """
    violations = check_no_context_tokens_literal_branching_from_source(snippet)
    assert len(violations) == 0
```

---

## 第 5 章 D5 根治 — held-out evaluator 用 private_handle 不靠 content 反查

### 5.1 v3.3c 的问题

v3.3c §4.4:

```python
def get_evaluator_metadata_for_public_event(self, public_event):
    for stored_event, meta in zip(self.held_out_events, self._external_evaluator_meta):
        if events_content_equal(stored_event, public_event):  # ← 用 content 反查
            return meta
    return None
```

问题:**两个不同 episode 可能有相同 content**:
- 同一张猫图,在不同课程包中作为 held-out 都被采用
- 两次 raw event 经 normalization 后内容完全相同
- content 反查 → 歧义,可能返回错 meta

### 5.2 v3.3d 根治:private_handle 调用栈

```python
# runtime/cognitive/curriculum/held_out_pool.py v3.3d

from dataclasses import dataclass
from typing import Generic, TypeVar


@dataclass(frozen=True)
class PrivateHandle:
    """
    v3.3d: evaluator 内部 handle,
    不传给 AP,只在 evaluator 调用栈里关联 public_event ↔ metadata.
    """
    handle_id: str  # opaque
    metadata: "EvaluatorMetadata"


@dataclass(frozen=True)
class PublicEvent:
    """
    给 AP 的事件,不含 event_id,不含 evaluator metadata.
    """
    kind: str
    content: dict
    # NO event_id


class HeldOutEventPool_v3_3d:
    """v3.3d: 完全私有 handle 设计,无 content 反查."""
    
    def __init__(self):
        self._private_storage: list[tuple[PrivateHandle, PublicEvent]] = []
    
    def add_during_curriculum(
        self,
        raw_event,
        evaluator_metadata: "EvaluatorMetadata",
        k_fold_index: int,
    ):
        """添加 held-out,生成 private handle."""
        if k_fold_index % K_FOLD != 0:
            return
        
        # 验证 raw event 是 raw normalized sensor SA
        assert raw_event.is_raw_normalized_sensor_event()
        assert not raw_event.contains_vocab_label()
        assert not raw_event.contains_proposition()
        
        # 生成 private handle
        handle = PrivateHandle(
            handle_id=secrets.token_hex(16),
            metadata=evaluator_metadata,
        )
        
        # 转 public event(剥掉 id)
        public = PublicEvent(
            kind=raw_event.kind,
            content=raw_event.content,
        )
        
        self._private_storage.append((handle, public))
    
    def sample_evaluation_batch(self, n: int):
        """
        v3.3d: 返回 (private_handle, public_event) pair.
        
        Evaluator 持有 handle,public_event 送 AP,
        AP 永远看不到 handle.
        """
        return random.sample(self._private_storage, min(n, len(self._private_storage)))


# Evaluator 使用方式
def evaluate_vocab_via_held_out_v3_3d(vocab_candidate, held_out_pool):
    """
    Evaluator 拿到 (handle, public) 后:
    1. 把 public_event 送 AP 跑
    2. 拿 AP response
    3. 用 handle.metadata 判定正确性
    
    AP 永远只看 public_event,handle 是 evaluator 调用栈私有.
    """
    pairs = held_out_pool.sample_evaluation_batch(n=8)
    
    correct = 0
    for handle, public_event in pairs:
        # 把 public 送 AP
        response = run_ap_with_event(public_event)
        
        # 评估(handle 是 evaluator 调用栈内变量,不传 AP)
        if handle.metadata.matches(response):
            correct += 1
    
    return correct / len(pairs)
```

### 5.3 验收

```python
def test_handle_does_not_leak_to_ap():
    """D5: handle 完全私有,AP 看不到."""
    pool = HeldOutEventPool_v3_3d()
    pool.add_during_curriculum(mock_raw_event(0), mock_meta(0), k_fold_index=0)
    
    pairs = pool.sample_evaluation_batch(n=1)
    handle, public = pairs[0]
    
    # AP 跑只看 public
    state_pool = StatePool()
    state_pool.observe_external(public)
    
    state_str = str(state_pool.snapshot())
    
    # handle.handle_id 不应在 AP state
    assert handle.handle_id not in state_str


def test_no_content_equality_lookup():
    """D5: 不需要 content equality 反查 metadata."""
    pool = HeldOutEventPool_v3_3d()
    
    # 添加两个 content 完全相同的 event(不同 episode)
    same_content = {"kind": "cat_image", "data": [1, 2, 3]}
    pool.add_during_curriculum(
        RawEvent(content=same_content),
        EvaluatorMetadata(target="cat_for_episode_A"),
        k_fold_index=0,
    )
    pool.add_during_curriculum(
        RawEvent(content=same_content),
        EvaluatorMetadata(target="cat_for_episode_B"),
        k_fold_index=5,
    )
    
    # sample 应返回明确的 (handle, public) pair,无歧义
    pairs = pool.sample_evaluation_batch(n=2)
    handle_ids = {h.handle_id for h, p in pairs}
    
    # 两个 handle 不同,即使 public content 相同
    assert len(handle_ids) == 2


def test_evaluator_uses_handle_in_call_stack_only():
    """D5: evaluator 用 handle 不通过外部映射."""
    pool = HeldOutEventPool_v3_3d()
    pool.add_during_curriculum(mock_event, mock_meta, k_fold_index=0)
    
    pairs = pool.sample_evaluation_batch(n=1)
    handle, public = pairs[0]
    
    # 关键:这里 handle 是局部变量,从 pool.sample 返回
    # evaluator 不需要再从 public 反查 handle
    response = run_ap_with_event(public)
    is_correct = handle.metadata.matches(response)  # 直接用调用栈里的 handle
    # 没有 pool.get_metadata_for_content(public) 这种反查
```

---

## 第 6 章 v3.3d 整合后的完整 Phase 13.5b.0 gate 清单

```
=== v3.2a 6 项 ===
F1 — privacy canary scan
F2 — pseudonymous HMAC
F3 — trust gate held-out
F4 — multi-teacher awaiting
F5 — metadata AST scan
F6 — held-out raw sensor SA

=== v3.2b 5 项 ===
E1 — JSON canonicalization
E2 — CORRECTION + status enum
E3 — no bool fields
E4 — opaque event_id
E5 — AST 4 new patterns

=== v3.2c/3.3b 5 项 ===
R1 — status not in learning paths
R2 — context_tokens not flagged
R3 — reject non-str items
R4 — event_id not in AP state
R8 — gate count by actual list

=== v3.3a 3 项(数学 substrate)===
E6 — 范式不变量教学,无 fixed coordinate yaml
E7 — 事实涌现,无 column_sum 算术
E8 — substrate 维度进 packet_key

=== v3.2c/3.3b 3 项(数学 substrate)===
R5 — origin/spacing/digit_width 不入 AP state
R6 — fact SA id opaque
R7 — substrate backoff + Q 稀疏度

=== v3.3c 7 项(字焦点)===
C1 — DraftCharFocus EntitySA
C2 — 字焦点 8 类 actions
C3 — Cell percept R 焦点调制
C4 — read_at_focus + 自动 scan 双路径
C5 — 字焦点状态进 packet_key(shape 不含绝对位置)
C6 — 字焦点 SDPL 学习路径
C7 — 同问题不同 origin 焦点移动相对一致

=== v3.3d 5 项(本稿)===
D1 — percept content 不含绝对坐标(SA id opaque + 相对位置 bucket)
D2 — COLUMN/ROW 焦点各向异性衰减(防 flooding)
D3 — move_to 只作底层原语,教学优先 SHIFT/visual_pointer
D4 — context_tokens 字段允许,字面量分支禁止
D5 — held-out private_handle 调用栈,不靠 content 反查

=== v3.3c 防假阳性追加(银子老师建议)===
A1 — 空移动序列不能过(无 move 不算解题)
A2 — 必须访问目标相对位置(focus 必须到过列内两个数字)
A3 — 固定坐标 ablation 必须失败(教学时所有 23+47 在 origin (2,5) → 测试 origin (0,0) 应正确)
```

**总计 39 项 gate**。Phase 13.0 落 F1-F6 + E1-E5 + R1-R4/R8(15 项)。Phase 13.5b.0 落 E6-E8 + R5-R7 + C1-C7 + D1-D5 + A1-A3(20 项)。

按 R8 原则,**报告以实际跑过的清单为准,不写硬数字**。

---

## 第 7 章 给 Codex 的实施指令(v3.3d)

1. **八稿配合**:v3 + v3.1 + v3.2 + v3.2a + v3.2b/3.3a + v3.2c/3.3b + v3.3c + v3.3d
2. **D1 Critical**:percept SA id 必须 opaque,绝对坐标只进 audit_metadata
3. **D2 Blocker**:COLUMN/ROW 焦点必须双轴衰减(primary + secondary sigma)
4. **D3**:课程包 yaml 不许 `char_focus_move_to_absolute` action
5. **D4**:扩 metadata AST scanner 加 In comparison + match-case + subscript 字面量检测
6. **D5**:HeldOutPool 重构 (private_handle, public_event) 调用栈设计
7. **任何对 v3.3d 的偏离先停下问 Claude/银子老师**

---

## 第 8 章 给银子老师 + Codex 对抗审阅者的指引

### 8.1 银子老师审

请审:

1. **D1 修复方式**(opaque SA id + relative bucket + audit_metadata 分层)是否符合预期?
2. **D2 双轴衰减**(primary 沿轴 / secondary 跨轴)是否符合"专注列但仍知道附近列"的感受?
3. **D3 视觉指针 grounding** 路径是否符合"教师手指着" → "系统字焦点跟随"的人类教学方式?
4. **D4 context_tokens 边界**(字段允许,字面量分支禁止)你接受吗?
5. **D5 private_handle 调用栈** 是否符合"evaluator 内部 / AP 外部"边界?

### 8.2 Codex 审

请重点验:

1. **D1 bucket 量化** 是否真能保证泛化?bucket 是否过粗(只 4 档:same/adjacent/near/far)?会不会信息量太少?
2. **D2 双轴 sigma** primary=3.0 / secondary=1.0 比值是否合理?有没有实测数据?
3. **D3 高/底层 action 分离** 是否覆盖所有路径?有没有遗漏的"准坐标 action"?
4. **D4 AST 检测** 是否覆盖所有字面量分支变体?如 `if x in {"a", "b"}:` 集合包含?
5. **D5 调用栈** 是否真能防 metadata 泄漏?有没有 evaluator 误把 handle 序列化到 AP state 的风险?

---

## 第 9 章 总结

v3.3d 修了 5 项严重问题,其中 D1 和 D2 是我 v3.3c **自己造成的灾难**:

- **D1**:我嘴上说"不含绝对坐标",但 percept content `draft_cell::{row}_{col}::{char}` **已经把绝对坐标编码进 SA id**。这是和 v3.3 fixed coordinate **同型的错误**,我又一次让"绝对坐标"潜伏到设计里。
- **D2**:COLUMN 焦点同列全高能,等于没焦点。

承认这些**比掩饰更重要**。Codex 抓出来,我感谢。

剩下 3 项也是真问题:
- **D3**:`move_char_focus_to(row, col)` 仍可能成课程坐标表
- **D4**:`context_tokens` 字面量分支仍是硬路由
- **D5**:held-out content equality 有歧义

v3.3d 全部根治。

**v3.3d 完成后,Codex 可以进 Phase 13.0(15 项 gate)**,Phase 13.5b.0(24 项 gate)再做字焦点完整验证。

---

— 银子老师 / Claude
— 2026-06-18

待 Codex 对抗审阅 v3.3d → 进 Phase 13.0 实施 → Phase 13.1 → Phase 13.5b.0 字焦点 substrate proof → 进数学课程。
