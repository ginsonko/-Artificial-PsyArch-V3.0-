# APV3.0 Phase 13.5b — 小学数学能力 v3.3 详细设计稿

日期: 2026-06-18
作者: 银子老师(原架构设计者 + 关键路径修订)/ Claude(整理)
状态: **A' 路径详细设计。基于银子老师挑战 + 修订:不补 APV2.1 风格的"参数化 action 14 件套",而是用 v14 已有机制 + DraftActionRunner 2D 文本网格扩展,让数学竖式/九九事实/应用题/列方程从 SDPL 路径自然 emerge。本稿待 Codex 对抗审阅。**

前作:
- v3.2a Landing Errata(隐私 / trust gate / 红线 6 项 must-fix)
- 诊断报告(已被本稿推翻,留存 audit trail)
- Phase 13 v3 总设计稿

许可:AGPL-3.0-or-later
原架构设计:银子老师

---

## 第 0 章 立意与核心洞察(必读)

### 0.1 银子老师的关键洞察

数学不需要专门写"参数化数学 action"。正确路径是用 v14 已有机制组合:

| 数学能力 | v14 已有机制 |
|---|---|
| 数字 / 数量 | Phase 8.6 量化桶 + Phase 8.4 vocab,数感涌现 |
| 个位加减 + 九九乘法(事实库) | Phase 8.4 SDPL vocab + Phase 8.15 long_term cold_index |
| 看竖式认竖式(视觉识别) | Phase 8.6 视觉感受器 + Phase 8.7 视焦点 + Phase 10.6 hierarchy SA |
| 自己写竖式(草稿生成) | **DraftActionRunner 扩展到 2D 文本网格**(新工作) |
| 进位/借位 | 范式 hierarchy SA 涌现(非硬编码 action) |
| 应用题读懂 | ComposedVocab + slot 偏好(黄苹果同款机制) |
| 列方程 | Phase 11.2 abstract_vocab + Phase 11.4 deliberative |
| 答案表达 | Phase 13.6 表达范式 + Phase 8.9 自然纠错 |

**只有 DraftActionRunner 2D 扩展是新工作,其他全部已有。**

### 0.2 两个空间范式空间的精确区分

银子老师强调:

**空间 A: 视觉感受器的竖式识别**
- 输入路径:教师/用户呈现给系统看的竖式图像
- 机制:Phase 8.6 视觉感受器 → 量化桶 → percept SA → Phase 8.7 视焦点
- 学到:"看到这种空间排列 = 这是竖式"(理解能力)

**空间 B: 草稿框的文本竖式生成**
- 输出路径:系统自己在草稿框里一字一字写竖式
- 机制:**DraftActionRunner 当前是一维文本流,需扩到 2D 网格**
- 学到:"在第几行第几列写什么字"(生成能力)

**关键统一**:这两个空间使用**同一个"竖式范式" hierarchy SA**,只是一个走视觉感受器输入,一个走 DraftActionRunner 输出。**真正的拟人:看到竖式知道是竖式,自己也能写出来**。

### 0.3 为什么 2D 文本网格是通用能力(不是为数学定制)

DraftActionRunner 扩到 2D 网格,用途远不止数学:

- 写竖式(数学)
- 写表格(数据展示)
- 排版 markdown(文档)
- 画 ASCII 艺术(创造性表达)
- 代码缩进(编程)
- 棋盘 / 围棋记录(游戏)

**这是通用工具升级,完全符合 v14 哲学**。和 Phase 8.6 视觉量化桶是同类性质 — 通用感知工具,不是为特定任务定制。

### 0.4 Phase 13.5b 完整目标(对应 APV2.1 Math-0~28)

```
子阶段 0: 数感(对应 Math-0)
子阶段 1: 个位加减 + 九九乘法事实库(对应 Math-1/9)
子阶段 2: 草稿空间 / 竖式范式 / 进位借位(对应 Math-4/5/7/8)
子阶段 3: 乘法竖式(对应 Math-10~13)
子阶段 4: 长除法(对应 Math-14~20)
子阶段 5: 应用题(对应 Math-21~24)
子阶段 6: 方程 / 列方程(对应 Math-25~28)
```

**总时间预算**:~25-30 天(可与 Phase 13 其他子阶段并行)

---

## 第 1 章 DraftActionRunner 2D 网格扩展(关键基础工作)

### 1.1 当前状态

`apv3test/runtime/draft_action.py` 当前仅支持 5 个一维文本动作:
- `type_text(text)` — 追加到 buffer 末尾
- `reread` — 重新审视
- `delete_chars(count)` — 从末尾删
- `replace_tail(old, new)` — 替换末尾
- `commit` — 提交

**问题**:不能在指定位置写,无法做竖式。

### 1.2 v3.3 扩展方案

#### 1.2.1 新增 DraftGrid 数据结构

```python
# apv3test/runtime/draft_grid.py(新文件)

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DraftGridCell:
    """单个网格单元."""
    char: str = " "  # 默认空格
    written_at_tick: int = -1  # -1 = 未写过
    revision_count: int = 0


@dataclass
class DraftGrid:
    """
    2D 文本网格 - 通用空间排列能力.
    
    用途:
    - 竖式数学
    - 表格
    - markdown 排版
    - ASCII 艺术
    
    设计原则:
    - 不为数学定制,通用 2D 空间
    - 与 1D buffer 共存(简单文本仍走 1D)
    - 显式从 1D 切换到 2D 时启用(避免破坏现有路径)
    """
    rows: int = 10  # 默认 10 行
    cols: int = 20  # 默认 20 列
    cells: dict[tuple[int, int], DraftGridCell] = field(default_factory=dict)
    
    # 焦点光标(系统当前在第几行第几列写)
    focus_row: int = 0
    focus_col: int = 0
    
    def __post_init__(self):
        # 初始化为空网格
        if not self.cells:
            for r in range(self.rows):
                for c in range(self.cols):
                    self.cells[(r, c)] = DraftGridCell()
    
    def write_at(self, row: int, col: int, char: str, *, tick: int) -> None:
        """在指定位置写一个字符."""
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            raise IndexError(f"Grid position ({row}, {col}) out of bounds")
        
        if len(char) != 1:
            raise ValueError(f"write_at expects single char, got {len(char)}")
        
        cell = self.cells[(row, col)]
        cell.char = char
        cell.written_at_tick = tick
        cell.revision_count += 1
        
        # 焦点跟随
        self.focus_row = row
        self.focus_col = col
    
    def read_at(self, row: int, col: int) -> str:
        return self.cells[(row, col)].char
    
    def move_focus(self, *, row_delta: int = 0, col_delta: int = 0) -> None:
        """光标移动."""
        new_row = max(0, min(self.rows - 1, self.focus_row + row_delta))
        new_col = max(0, min(self.cols - 1, self.focus_col + col_delta))
        self.focus_row = new_row
        self.focus_col = new_col
    
    def get_row_string(self, row: int) -> str:
        return "".join(self.cells[(row, c)].char for c in range(self.cols))
    
    def get_column_string(self, col: int) -> str:
        return "".join(self.cells[(r, col)].char for r in range(self.rows))
    
    def to_visible_string(self) -> str:
        """把网格转成可见字符串(尾部空格剪掉)."""
        rows_str = []
        for r in range(self.rows):
            row_str = self.get_row_string(r).rstrip()
            rows_str.append(row_str)
        # 尾部全空行剪掉
        while rows_str and not rows_str[-1]:
            rows_str.pop()
        return "\n".join(rows_str)
    
    def to_audit_dict(self) -> dict:
        """审计用 dict(只含非空 cell)."""
        return {
            "rows": self.rows,
            "cols": self.cols,
            "focus": [self.focus_row, self.focus_col],
            "non_empty_cells": {
                f"{r},{c}": {
                    "char": cell.char,
                    "tick": cell.written_at_tick,
                    "revisions": cell.revision_count,
                }
                for (r, c), cell in self.cells.items()
                if cell.char != " "
            }
        }
```

#### 1.2.2 扩展 DraftActionRunner 新 actions

```python
# apv3test/runtime/draft_action.py 扩展

@dataclass(frozen=True)
class DraftTextAction:
    tick: int
    kind: str  # 扩展支持的 kind:
    # 1D (既有,保留):type_text / reread / delete_chars / replace_tail / commit
    # 2D (v3.3 新增):
    #   - enter_grid_mode(rows, cols) — 切换到 2D 模式
    #   - exit_grid_mode — 切回 1D 模式
    #   - write_at_grid(row, col, char) — 在指定位置写
    #   - move_grid_focus(row_delta, col_delta) — 光标移动
    #   - read_grid_cell(row, col) — 显式读某 cell(返回值作 percept 注入)
    #   - read_grid_row(row) — 读整行
    #   - read_grid_column(col) — 读整列
    text: str = ""
    count: int = 1
    old_text: str = ""
    new_text: str = ""
    actuator_id: str = "draft_editor"
    # 2D 参数
    grid_row: int = 0
    grid_col: int = 0
    grid_rows_init: int = 10
    grid_cols_init: int = 20
    grid_char: str = ""


class DraftActionRunner:
    """扩展版,支持 1D 文本 + 2D 网格双模式."""
    
    def apply(self, state, action):
        next_state = self.ensure_state(state)
        runtime = next_state["draft_runtime"]
        self._assert_single_action_per_tick(runtime, action)
        
        kind = action.kind
        
        # 1D actions(既有)
        if kind == "type_text":
            self._type_text(runtime, action.text)
        elif kind == "reread":
            self._reread(runtime, action.tick)
        # ... 其他既有
        
        # 2D actions(v3.3 新增)
        elif kind == "enter_grid_mode":
            self._enter_grid_mode(runtime, action.grid_rows_init, action.grid_cols_init)
        elif kind == "exit_grid_mode":
            self._exit_grid_mode(runtime)
        elif kind == "write_at_grid":
            self._write_at_grid(runtime, action.grid_row, action.grid_col, action.grid_char, action.tick)
        elif kind == "move_grid_focus":
            self._move_grid_focus(runtime, action.grid_row, action.grid_col)
        elif kind == "read_grid_cell":
            self._read_grid_cell(runtime, action.grid_row, action.grid_col, action.tick)
        elif kind == "read_grid_row":
            self._read_grid_row(runtime, action.grid_row, action.tick)
        elif kind == "read_grid_column":
            self._read_grid_column(runtime, action.grid_col, action.tick)
        else:
            raise ValueError(f"unsupported draft action: {kind}")
        
        runtime["action_log"].append({
            "tick": int(action.tick),
            "actuator_id": action.actuator_id,
            "kind": kind,
        })
        return next_state
    
    def _enter_grid_mode(self, runtime, rows, cols):
        runtime["grid"] = DraftGrid(rows=rows, cols=cols)
        runtime["mode"] = "grid"
    
    def _write_at_grid(self, runtime, row, col, char, tick):
        if runtime.get("mode") != "grid":
            raise RuntimeError("write_at_grid requires grid mode")
        grid = runtime["grid"]
        grid.write_at(row, col, char, tick=tick)
    
    def _read_grid_cell(self, runtime, row, col, tick):
        """读 cell 产生 percept SA 注入回 state pool."""
        grid = runtime["grid"]
        char = grid.read_at(row, col)
        # 这一步关键:读 cell 等于"自己看自己写的东西"
        # 产生 percept SA,带 PERCEIVED marker
        # 进入 state pool 参与下一 tick 决策
        runtime["readbacks"].append({
            "tick": tick,
            "kind": "grid_cell",
            "row": row,
            "col": col,
            "char": char,
        })
```

### 1.3 关键设计:观察自己写的东西(2D 闭环)

银子老师指出:**"理论上是需要在自己的草稿框里面写空间排列范式,并且可以观察到文本的空间排列范式"**

这就是"看自己的草稿"能力。实现:

```python
# 系统流程
# Tick N:  decide → write_at_grid(0, 0, "2")
# Tick N+1:decide → write_at_grid(0, 1, "3")
# Tick N+2:decide → read_grid_row(0)  ← 读自己刚写的
#                   ↓
#                   产生 percept SA "grid_row_0_content" = "23"
#                   注入 state pool,带 PERCEIVED marker
#                   ↓
#                   下一 tick 的 SDPL packet 看到这个 percept
#                   ↓
#                   决策"接下来要在第 1 行第 0 列写 ×"
```

**这是真正的"自己写自己读"闭环**,系统能感知自己的草稿状态,基于状态决策下一步。

### 1.4 与视觉感受器的对称性

| 维度 | 视觉感受器(输入)| 草稿网格(输出+回读) |
|---|---|---|
| 来源 | 教师/外部图像 | 系统自己写 |
| 量化 | 像素 → 量化桶 | 字符 → cell |
| 空间 | 2D pixel array | 2D cell grid |
| 焦点 | 视焦点(Phase 8.7) | 草稿光标 focus_row/col |
| 经 percept SA | 视觉 percept | 草稿 percept(read 时产生) |
| marker | PERCEIVED | PERCEIVED(同 kind) |

**两个路径产生的 percept 进入同一 state pool,经同一 SDPL 路径学习**。这就是"看竖式 = 写竖式"的同一范式。

---

## 第 2 章 子阶段 0 — 数感(对应 Math-0)

### 2.1 目标

- 系统知道 0-20 数字
- 系统能数(count)
- 系统理解 successor("后面一个")
- 系统理解 quantity(看到 3 个苹果 → vocab "3")

### 2.2 教学方式(SDPL 路径)

```yaml
package_id: "math.0_numerosity_basics"
description: "数字 / 数量 / 计数 / successor 基础"
teacher_entity_id: "teacher::official::math_v1"
trust_policy:
  initial_trust: 0.9

content:
  # 数字 vocab
  - sa_id: "vocab::digit::0"
    chinese_label: "零"
    pinyin: "líng"
    arabic_glyph: "0"
    visual_examples:
      - "assets/visual/digits/0_printed_001.jpg"
      - "assets/visual/digits/0_handwritten_001.jpg"
      - ... ≥ 5 张
    semantic_tags: ["digit", "zero", "empty_quantity"]
  
  - sa_id: "vocab::digit::1"
    chinese_label: "一"
    pinyin: "yī"
    arabic_glyph: "1"
    visual_examples: [... ≥ 5 张]
    semantic_tags: ["digit", "one", "smallest_positive"]
  
  # ... 0-20
  
  # 数量 vocab
  - sa_id: "vocab::quantity::3"
    description: "3 个东西的数量感"
    visual_examples:
      - "assets/visual/quantities/3_apples_001.jpg"
      - "assets/visual/quantities/3_dots_001.jpg"
      - "assets/visual/quantities/3_blocks_001.jpg"
      - ... ≥ 5 张
    paired_contrast:
      - vocab_sa_id: "vocab::quantity::2"
        rationale: "近邻数量,验证 disentanglement"
      - vocab_sa_id: "vocab::quantity::4"
  
  # successor 范式
  - sa_id: "paradigm::successor"
    teaching_paradigms:
      - "1 的下一个是 2"
      - "2 的下一个是 3"
      - "3 的下一个是 4"
      # ... 教 0→1→2→...→20 共 20 个范式
    learning_signal: |
      经 Phase 10.1 lag-PMI 学时序:
      digit X → digit X+1 的 lag-PMI 应显著正
    
  # quantity ↔ digit 双向绑定
  - sa_id: "binding::quantity_digit"
    bindings:
      - {visual: "vocab::quantity::3", text: "vocab::digit::3"}
      - {visual: "vocab::quantity::4", text: "vocab::digit::4"}
      # ... 全 0-20

validation:
  - test_id: "digit_recognition_from_visual"
    given: "未见过的 5 字体 × 20 数字"
    expected: top_1_accuracy >= 0.85
  
  - test_id: "successor_prediction"
    given: "数字 X(0-19)"
    expected: "系统能预测 X+1 概率 top_1 ≥ 0.90"
  
  - test_id: "quantity_digit_binding"
    given: "3 个苹果的图"
    expected: "vocab::digit::3 应是 top recall"
  
  - test_id: "counting_action"
    given: "5 个物体的图"
    expected: |
      系统经 draft action 输出 "5"(可以用 1D 文本)
      或 enter_grid_mode + write_at_grid(0, 0, "5")
```

### 2.3 验收

- teacher-off 后 4 个 validation tests 全部 ≥ 85%
- 无 hardcoded "if digit == X then digit + 1"(SDPL 路径学到)

### 2.4 时间预算

**2-3 天**(主要内容 + 教学跑通)

---

## 第 3 章 子阶段 1 — 事实库(个位加减 + 九九乘法,对应 Math-1/9)

### 3.1 关键洞察(银子老师)

**九九乘法表 = 81 个 vocab 事实**。系统通过反复教学,把这些事实存进 long_term cold_index,**用时 cue 触发 rehydration**。

这是 **SDPL 最擅长的事**:
- packet `{"3", "×", "7"}` → action: commit "21"
- packet `{"4", "+", "5"}` → action: commit "9"

通过反复教学 + RPE,Q 表收敛。

### 3.2 教学内容

```yaml
package_id: "math.1_basic_facts"
description: "个位加减(< 20) + 九九乘法(1-9)"
prerequisites: ["math.0_numerosity_basics"]
teacher_entity_id: "teacher::official::math_v1"

content:
  # 个位加法 vocab fact
  - sa_id: "fact::add::3_4"
    teaching_paradigms:
      - "3 + 4 = 7"
      - "3 加 4 等于 7"
      - "三加四等于七"
    components:
      - "vocab::digit::3"
      - "vocab::operator::add"
      - "vocab::digit::4"
      - "vocab::digit::7"  # 结果
    learning_signal: |
      经 Phase 8.4 SDPL 学习:
      packet {3, +, 4} → action: commit "7"
      多次教学后 Q 表 backoff (exact / content_only / action_global) 收敛
  
  # ... 共 100+ 个 0-9 加法对(0+0 ~ 9+9 含交换律 = 100 个)
  
  # 个位减法 vocab fact
  - sa_id: "fact::subtract::9_4"
    teaching_paradigms:
      - "9 - 4 = 5"
      - "9 减 4 等于 5"
    # ... 共 ~55 个非负结果减法对
  
  # 九九乘法 vocab fact
  - sa_id: "fact::multiply::3_7"
    teaching_paradigms:
      - "3 × 7 = 21"
      - "三七二十一"
      - "三乘以七等于二十一"
    components:
      - "vocab::digit::3"
      - "vocab::operator::multiply"
      - "vocab::digit::7"
      - "vocab::number::21"
  
  # ... 共 81 个 1-9 乘法对

teaching_sequence:
  strategy: "interleaved"
  batch_size: 10
  repetition_per_fact: 5  # 每个事实重复教 5 次
  total_episodes: ~1000  # 100 加 + 55 减 + 81 乘,每个 5 次

validation:
  - test_id: "addition_recall_within_10"
    given: "随机 a + b, a,b ∈ [0,9]"
    expected: accuracy >= 0.95
  
  - test_id: "multiplication_recall_9x9"
    given: "随机 a × b, a,b ∈ [1,9]"
    expected: accuracy >= 0.95
  
  - test_id: "commutativity_emerge"
    given: "教 '3+4=7' 但未教 '4+3=7'"
    expected: |
      系统应能从 SDPL packet {4, +, 3} recall "7"
      (通过共现学习自然涌现交换律,不需要专门教)
```

### 3.3 验收

- 加法 95% / 乘法 95% accuracy
- 交换律自然涌现(教一边 → 另一边也能)
- **关键**:cold_index 真存了 81 个乘法 vocab + 100+ 加法 vocab,cue rehydration 真工作

### 3.4 时间预算

**3-4 天**(内容多但都是同一机制反复 SDPL 教学)

---

## 第 4 章 子阶段 2 — 草稿空间 / 竖式范式(对应 Math-4/5/7/8)

### 4.1 双范式空间(银子老师强调)

#### 空间 A:视觉感受器学竖式识别

```yaml
package_id: "math.2a_visual_vertical_recognition"
description: "看到竖式图,识别为竖式"

content:
  - sa_id: "paradigm::visual_vertical_addition"
    visual_examples:
      - "assets/visual/vertical_layouts/addition_001.jpg"  # 23 + 47 竖式图
      - "assets/visual/vertical_layouts/addition_002.jpg"  # 56 + 38 竖式图
      - ... ≥ 30 张不同竖式加法图
    paired_contrast:
      - sa_id: "paradigm::horizontal_equation"
        rationale: "水平 '23 + 47 = ?' vs 竖式排列"
    
    teaching_paradigms:
      - "这是竖式加法"
      - "上面是被加数,下面是加数"
      - "从右往左逐位相加"
    
    learning_signal: |
      经 Phase 8.6 视觉量化桶 + Phase 8.7 视焦点:
      系统学到"垂直排列两个数字 + 横线 + 答案"这个视觉范式
      经 Phase 10.6 hierarchy SA 固化为 vocab "竖式加法范式"

validation:
  - test_id: "recognize_unseen_vertical_layout"
    given: "未见过的竖式图(包括手写)"
    expected: vocab "竖式加法范式" should activate
```

#### 空间 B:草稿网格学竖式生成

```yaml
package_id: "math.2b_grid_vertical_generation"
description: "用 DraftActionRunner 2D 网格生成竖式"

content:
  - sa_id: "paradigm::grid_vertical_addition_layout"
    description: "在 2D 草稿网格写竖式的步骤序列"
    
    teaching_episodes:
      - input: {a: 23, b: 47}
        expected_action_sequence:
          - {action: "enter_grid_mode", rows: 5, cols: 4}
          - {action: "write_at_grid", row: 0, col: 2, char: "2"}   # 写 23 的十位
          - {action: "write_at_grid", row: 0, col: 3, char: "3"}   # 写 23 的个位
          - {action: "write_at_grid", row: 1, col: 0, char: "+"}   # 写 +
          - {action: "write_at_grid", row: 1, col: 2, char: "4"}   # 写 47 的十位
          - {action: "write_at_grid", row: 1, col: 3, char: "7"}   # 写 47 的个位
          - {action: "write_at_grid", row: 2, col: 0, char: "─"}   # 横线左
          - {action: "write_at_grid", row: 2, col: 1, char: "─"}
          - {action: "write_at_grid", row: 2, col: 2, char: "─"}
          - {action: "write_at_grid", row: 2, col: 3, char: "─"}   # 横线右
          # 然后开始算:
          - {action: "read_grid_column", col: 3}  # 读个位列(3, 7)
          # → percept SA "column_3 = (3, 7)"
          - {action: "read_grid_cell", row: 0, col: 3}  # 读 23 的个位
          # → percept SA "saw_3"
          - {action: "read_grid_cell", row: 1, col: 3}
          # → percept SA "saw_7"
          # state pool 现在有 packet {3, +, 7}
          # → recall fact::add::3_7 = 10
          # → 进位 1
          - {action: "write_at_grid", row: 3, col: 3, char: "0"}  # 写答案个位
          - {action: "write_at_grid", row: 3, col: 1, char: "1"}  # 写进位标记(可选)
          # 然后读十位:
          - {action: "read_grid_column", col: 2}
          - {action: "read_grid_cell", row: 0, col: 2}  # → "2"
          - {action: "read_grid_cell", row: 1, col: 2}  # → "4"
          # packet {2, +, 4, +1 进位} → recall = 7
          - {action: "write_at_grid", row: 3, col: 2, char: "7"}
          # 最终答案 70
    
    teaching_paradigms:
      - "竖式加法从右往左算"
      - "个位相加 ≥ 10 要进位"
      - "十位相加要加上进位"

validation:
  - test_id: "generate_vertical_addition_two_digit"
    given: "23 + 47"
    expected:
      - grid 最终状态正确(70 在第 3 行)
      - 计算路径符合"从右往左 + 进位"范式
      - 不允许 commit answer 而 grid 上没竖式过程
  
  - test_id: "no_direct_computation"
    given: "23 + 47"
    redline: |
      行动 trace 中不能有 commit answer 而无 grid actions
      必须经过 read → recall → write 路径
```

### 4.2 进位 / 借位作为范式 hierarchy SA emerge

不是"硬编码 strict_propagate_carry action"。

而是:
1. 教学时给系统看大量进位例子:5+7=12(写 2,进 1),8+6=14(写 4,进 1)
2. SDPL 共现学习:packet {column_sum >= 10} → 范式 "进位"
3. Phase 10.6 hierarchy SA 把"进位"固化为复合范式 vocab
4. 后续遇到 column_sum=15,自然走"写 5 + 进 1"

**完全 SDPL 路径,无硬编码**。

### 4.3 验收

- 两位数加法 90% 正确(包括进位)
- 两位数减法 85% 正确(包括借位)
- grid trace 完整(可视化)
- redline:无直接计算路径(必须经 grid)

### 4.4 时间预算

**5-7 天**(DraftActionRunner 2D 扩展 + 大量竖式教学)

---

## 第 5 章 子阶段 3 — 乘法竖式(对应 Math-10~13)

### 5.1 基于子阶段 1 + 2

乘法竖式 = 子阶段 1 的九九乘法事实 + 子阶段 2 的草稿空间能力 + 新范式"部分积 + 位移"

```
   23
×  47
─────
  161    ← 7 × 23 = 161
  920    ← 4 × 23 = 92,左移一位写 92_
─────
 1081
```

### 5.2 教学内容

```yaml
package_id: "math.3_multiplication_vertical"
description: "竖式乘法 - 部分积 + 位移"
prerequisites: ["math.1_basic_facts", "math.2b_grid_vertical_generation"]

content:
  - sa_id: "paradigm::partial_product_layout"
    teaching_paradigms:
      - "用个位乘被乘数,写在第一行"
      - "用十位乘被乘数,写在第二行,但左移一位"
      - "把两行加起来"
    
    teaching_episodes:
      - input: {a: 23, b: 47}
        # 第一步:7 × 23
        # cue 触发 fact::multiply::7_3 = 21,写 1 进 2
        # cue 触发 fact::multiply::7_2 = 14,加进位 2 = 16
        # 第一行结果:161
        # 第二步:4 × 23(注意要左移一位)
        # 类似计算
        # 第三步:两行相加 161 + 920 = 1081
        expected_grid_final_state: "23\n× 47\n─────\n  161\n  920\n─────\n 1081"

validation:
  - test_id: "two_digit_multiplication_accuracy"
    given: "随机两位数 × 两位数 50 题"
    expected: accuracy >= 0.85
  
  - test_id: "partial_products_visible_in_grid"
    redline: "必须在 grid 上可见两行部分积"
```

### 5.3 时间预算

**3-4 天**

---

## 第 6 章 子阶段 4 — 长除法(对应 Math-14~20)

### 6.1 范式

```
     27
    ────
 23│ 621
    46↓
    ────
    161
    161
    ────
      0
```

时序范式:试商 → 乘回 → 减 → 落位 → 试商 → ...

### 6.2 教学

```yaml
package_id: "math.4_long_division"
description: "长除法 - 试商-乘回-减-落位循环"
prerequisites: ["math.3_multiplication_vertical"]

content:
  - sa_id: "paradigm::division_trial_quotient"
    teaching_paradigms:
      - "试一个商,使 商 × 除数 ≤ 被除部分"
      - "把试商结果减掉"
      - "下一位落下来"
      - "继续试商"
    # ... 详细 step-by-step
  
  teaching_episodes:
    - input: {dividend: 621, divisor: 23}
      # 23│621
      # 第一步:62 ÷ 23 ≈ ?,试 2,2 × 23 = 46,62 - 46 = 16
      # 第二步:落下 1,得 161
      # 第三步:161 ÷ 23 ≈ ?,试 7,7 × 23 = 161,161 - 161 = 0
      # 商:27,余 0
```

### 6.3 时间预算

**3-4 天**

---

## 第 7 章 子阶段 5 — 应用题(对应 Math-21~24)

### 7.1 关键洞察

应用题 = **文本理解 + 关系识别 + 列式 + 计算 + 答案回填**

每一步都已在 v14 中有对应机制:

| 步骤 | v14 机制 |
|---|---|
| 文本理解(读题) | Phase 8.4 SDPL vocab + Phase 8.5 cognitive_feelings |
| 关系识别("比...多 → 加法") | Phase 8.4 ComposedVocab + Phase 10.6 hierarchy SA |
| 列式 | Phase 10.6 hierarchy + paradigm slot fill |
| 计算 | 子阶段 1-4 已学 |
| 答案回填 | Phase 13.6 表达范式 + DraftActionRunner |

### 7.2 教学内容

```yaml
package_id: "math.5_word_problems"
description: "应用题:文本 → 关系 → 列式 → 计算 → 回答"
prerequisites: ["math.4_long_division"]

content:
  # 关系词 → 运算 vocab(关键)
  - sa_id: "paradigm::relation::more_than_means_add"
    teaching_paradigms:
      - "A 比 B 多 X,则 A = B + X"
      - "甲比乙多 3 → 用加法"
    paired_contrast:
      - sa_id: "paradigm::relation::less_than_means_subtract"
    
    learning_signal: |
      经 SDPL slot 偏好涌现:
      slot "关系词" 看历史 filler ["比...多", "增加了", "加上"]
      → slot 偏好绑 "加法运算" vocab
      
      这和黄苹果中"颜色词 slot 绑 C2 通道"机制完全相同
  
  # 完整应用题教学
  - sa_id: "problem_template::comparison"
    teaching_episodes:
      - input: |
          小明有 23 个苹果,
          小红比他多 4 个,
          小红有几个?
        expected_decomposition:
          - entity_1: "小明"
          - entity_1_quantity: 23
          - entity_1_object: "苹果"
          - relation: "比...多"
          - relation_value: 4
          - target_entity: "小红"
          - target_quantity: "?"
        expected_equation: "23 + 4 = ?"
        expected_answer: 27
        expected_final_text: "小红有 27 个" or "27"

validation:
  - test_id: "extract_relation_from_text"
    given: "30 个不同表达的'比...多'句子"
    expected: 关系识别准确率 >= 0.85
  
  - test_id: "list_equation_from_problem"
    given: "100 个应用题"
    expected: 正确列式率 >= 0.80
  
  - test_id: "end_to_end_word_problem"
    given: "50 个应用题,涉及加减乘除"
    expected: 最终答案正确率 >= 0.75
  
  - test_id: "redline_no_keyword_match"
    redline: |
      不许有 if "多" in text: operation = "add" 这种 hardcode
      必须经 SDPL slot 偏好涌现
```

### 7.3 时间预算

**3-4 天**

### 7.4 风险

这是真考验。如果跑不通,Phase 13.5b 可以止步于此。

---

## 第 8 章 子阶段 6 — 方程 / 列方程(对应 Math-25~28)

### 8.1 关键挑战

未知数 x 是 abstract vocab — 没有具体值,只是占位。

v14 Phase 11.2 abstract_vocab 已有,但实际能否承担"未知数"角色是个真考验。

### 8.2 教学路径

```yaml
package_id: "math.6_equation_solving"
description: "未知数 + 等式 + 逆运算"
prerequisites: ["math.5_word_problems"]

content:
  # 未知数 abstract vocab
  - sa_id: "abstract_vocab::unknown_x"
    description: "占位符,代表未知量"
    grounding_links:
      - "vocab::quantity_general"
      - "vocab::placeholder_concept"
    grounding_clusters_required: 2  # 跨 2 个 cluster(Phase 11.2 要求)
  
  # 等式范式
  - sa_id: "paradigm::equation_balance"
    teaching_paradigms:
      - "等号两边相等"
      - "两边同时加减乘除同一个数,等式仍成立"
    
  # 逆运算
  - sa_id: "paradigm::inverse_operation"
    teaching_paradigms:
      - "x + 3 = 7,两边减 3,得 x = 4"
      - "2x = 10,两边除以 2,得 x = 5"
    
    learning_signal: |
      经 Phase 11.4 deliberative virtual track:
      内部演算"如果 x = 4,验算 4 + 3 = 7 ✓"
      虚轨道推理,不动主状态

validation:
  - test_id: "solve_one_step_equation"
    given: "x + 3 = 7"
    expected: x = 4 with deliberation trace
  
  - test_id: "list_equation_from_word_problem"
    given: "小明有些苹果,给了小红 3 个后还剩 5 个,小明原来有几个?"
    expected:
      - decomposition: original = x, after_gift = x - 3, remaining = 5
      - equation: "x - 3 = 5"
      - solution: x = 8

# 真考验风险预警
risk_warning: |
  这是 Phase 13.5b 最难子阶段.
  Phase 11.2 abstract_vocab + 11.4 deliberative 是否真能承担"求解 x" 任务,
  需要实测.
  
  如果跑不通,公开承认:"方程能力 Phase 14+ roadmap"
```

### 8.3 时间预算

**4-5 天**(考验阶段,时间不确定)

---

## 第 9 章 严格红线 + 验收门(全 Phase 13.5b 适用)

### 9.1 红线(继承 v14 + 本稿强化)

```python
# scripts/red_line_check_v14.py 扩展 v3.3

def check_no_math_hardcode():
    """禁数学相关的硬编码."""
    forbidden_patterns = [
        # 禁直接计算函数调用代替 vocab 召回
        r"def\s+compute_addition",
        r"def\s+compute_multiplication",
        r"def\s+solve_equation",
        # 禁关键词硬路由
        r'if\s+["\']比["\']\s*in\s+text',
        r'if\s+["\']多["\']\s*in\s+text',
        r'if\s+["\']少["\']\s*in\s+text',
        # 禁直接调用 Python 算术
        r"eval\(.*[\+\-\*/]",
        # 禁 if column_sum >= 10: carry = 1 这种竖式硬编码
        r"if\s+column_sum\s*>=\s*10",
    ]
    # AST 扫描 + regex
    ...
```

### 9.2 验收门(分子阶段)

| 子阶段 | 验收门 | 时间 |
|---|---|---|
| 0 数感 | 4 tests ≥ 85% | 2-3 天 |
| 1 事实库 | 加法 95% + 乘法 95% + 交换律涌现 | 3-4 天 |
| 2 草稿空间 | 2D grid 工作 + 两位数加减 90%/85% + 无直接计算 | 5-7 天 |
| 3 乘法竖式 | 两位数乘 85% + 部分积可见 | 3-4 天 |
| 4 长除法 | 三位除两位 80% + 时序可见 | 3-4 天 |
| 5 应用题 | 关系识别 85% + 列式 80% + 端到端 75% | 3-4 天 |
| 6 方程 | 一步方程 70% + 列方程 60%(考验) | 4-5 天 |

**总时间**:23-31 天

### 9.3 失败应对

每个子阶段独立验收。**子阶段 N 失败 → 不进 N+1**:

- 子阶段 5 失败 → 公开"应用题能力 Phase 14+",已有数学能力到长除法
- 子阶段 6 失败 → 公开"方程能力 Phase 14+",已有数学能力到应用题

诚实是开源信用。

---

## 第 10 章 与 v14 红线的对齐表

| v14 红线 | Phase 13.5b 落地 |
|---|---|
| ❌ 字面量数字 | 全部阈值 yaml @structural/@experimental |
| ❌ keyword 路由 | 关系词 → 运算 经 slot 偏好涌现,非 if-then |
| ❌ 学生侧 LLM | 数学全程 SDPL 路径,无 LLM |
| ❌ audit_db 进 cognitive | 草稿 grid 状态进 cognitive,不进 audit_db |
| ❌ 测试用语义字串 | 测试断言 sa_id / vocab_id / cell content |
| ❌ MarkerKind 分支 | 数学不引入新 marker |
| ❌ 任意 is_X 字段 | 不加 |

新增红线:
- ❌ **数学相关硬编码**(compute_addition / solve_equation / 关键词 if)
- ❌ **直接计算路径**(必须经 grid 可见过程)

---

## 第 11 章 给 Codex 的实施指令

1. **v3 + v3.1 + v3.2 + v3.2a + v3.3(本稿)五稿配合**
2. **Phase 13.5b 子阶段独立验收**,跑不通停在那
3. **DraftActionRunner 2D 扩展**是基础工作(子阶段 2 前)
4. **数学 vocab 全部走 SDPL 路径**,不许任何"compute_X"函数
5. **关系词识别走 slot 偏好涌现**,不许 keyword 路由
6. **未知数 x 走 abstract_vocab**,不许专门绑定子系统
7. **每子阶段中文展示页**(到子阶段 6 时合并)
8. **草稿 grid 状态可视化**(Web 工作台显示二维网格,是核心 demo)

---

## 第 12 章 给 Codex 对抗审阅者的指引

请重点检查:

### 12.1 必查项

1. **§1 DraftActionRunner 2D 扩展**:接口设计是否破坏既有 1D 路径?2D 是否真"通用工具"而非"为数学定制"?
2. **§3.2 九九乘法 vocab 路径**:81 个 vocab fact 经 SDPL 学习是否会 cold_index 爆炸?rehydration 性能?
3. **§4.2 进位作为 hierarchy SA 涌现**:Phase 10.6 hierarchy 是否真能从大量进位例子涌现"进位"复合范式?有没有实测数据?
4. **§5 部分积 + 位移**:这是真考验,Phase 10.6 + 10.1 narrative 能否承担"乘法多步序列"?
5. **§7.2 关系词 slot 偏好**:这是黄苹果同款机制吗?slot 历史 filler 真能涌现"加减关系"?
6. **§8 abstract_vocab 承担未知数**:Phase 11.2 实际能力?Phase 11.4 deliberative 求解 x 是否可行?

### 12.2 隐藏风险

- 2D grid 状态在 state_pool 占多大?会不会拖慢全局?
- 子阶段间是否有未声明的依赖?
- 子阶段 6 方程涉及 Phase 11 全部机制,是否过度依赖?
- 测试断言能否真不偷用语义?(如何测"7"这个数字 vocab 被 recall,不能用 commit text 字串)

### 12.3 期望审阅产出

- 严重度排序 punch list
- 每条 issue 给具体修复方向
- 整体判断:**v3.3 能否作为 Phase 13.5b 实施依据?如否,缺什么?**

---

## 第 13 章 银子老师审稿建议

请你审:

1. **§1.2 DraftActionRunner 2D 接口设计**是否符合预期?接口是否够通用(不只为数学)?
2. **§4 双范式空间(视觉识别 vs 草稿生成)区分是否准确**?有没有遗漏的角度?
3. **子阶段 1-4 时间预算 ~16 天是否合理**?(对应 APV2.1 Math-0~20 经验)
4. **子阶段 5/6 是真考验阶段**,你接受跑不通就止步吗?
5. **数学课程包内容**(具体每个 vocab 教什么)是 Codex 写还是我 + 你写?(Phase 13.6 表达范式我们写,数学内容相对结构化,Codex 可以写,我们审)

---

## 第 14 章 总结

Phase 13.5b v3.3 与 v3.2 的关键差异:

| 维度 | v3.2 | v3.3 |
|---|---|---|
| 数学能力上限 | Math-1(单位加减) | 长除法 / 应用题(可能到方程) |
| 架构扩展 | 无 | DraftActionRunner 2D 网格(通用) |
| 路径 | "借鉴 APV2.1 课程,SDPL 重做" | "用 v14 已有 + 通用 2D 草稿,数学作为范式 emerge" |
| 时间 | 4-5 天(收缩版) | 23-31 天(完整版) |
| 风险 | 低(目标小) | 中(分子阶段独立验收) |
| 开源 demo | 数感 + 单位加减 | 竖式数学(可视化竖式过程) + 可能含应用题 |

**核心承诺**:**不补 APV2.1 风格的参数化数学 action 14 件套**。

**唯一新工作**:**DraftActionRunner 2D 网格扩展**(通用能力,非数学定制)。

其余全部用 v14 已有机制。这才是"AP-native 数学能力涌现"。

---

— 银子老师(原架构设计者)
— Claude(整理)
— 2026-06-18

待 Codex 对抗审阅 → v3.3a/v3.4(如需)→ 实施。
