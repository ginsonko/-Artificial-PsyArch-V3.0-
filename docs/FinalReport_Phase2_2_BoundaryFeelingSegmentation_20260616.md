# APV3.0test Phase2.2 边界感受 SA 与跨 tick 切分报告

日期: 2026-06-16

## 1. 设计

本阶段继续 APV3.0-test 的完整数学模型落地方向, 不回到 APV2.1 修补。

Phase2.1 已补上锚相对 DP 对齐, 但它默认输入已经是可比较的序列。要让自由中文开放对话底座从真实连续运行流中学习, 必须先解决:

- 跨 tick 的 SA bundle 如何组成一个可学习单元。
- 同 tick 多模态共现如何保留为一个 bundle。
- 什么时候应该切开一个 episode, 什么时候应该让工作记忆继续保持连续。
- 不能依赖外部 turn flag、文本关键词或 harness 标记。

因此本阶段新增 `BoundaryFeelingSegmenter`:

- 输入: `FocusTick(tick, sa_bundle, quantity_closure, step_closure, pressure_release, rhythm_reset)`。
- 输出: `BoundaryFeelingSA` 与 `BoundarySegment`。
- 边界感受来源:
  - `continuity_drop`
  - `quantity_closure`
  - `step_closure`
  - `pressure_release`
  - `rhythm_reset`
- 输出的 `BoundaryFeelingSA` 是可审计的一等 SA-like 事件。

关键边界:

- 不读取文本内容。
- 不按具体词、模态名、领域名路由。
- 不使用外部 turn flag。
- 不把边界模块写成策略层, 只负责从连续 tick 流中切出可学习 unit。

## 2. 审查完善

本阶段审查时发现一个重要问题:

如果把“相邻 tick 的 label 完全不重合”直接视为强边界, 中文逐字流和跨模态流会被每 tick 切碎。例如:

```text
text::三 text::顾
text::茅 text::庐
```

这两个 tick 的 label 不重合, 但它们应属于同一个学习单元。否则跨 tick successor/paradigm learning 会被破坏。

因此做了两项修正:

1. 在当前最小实现中, `continuity_drop` 只作为弱证据, 默认权重低于边界阈限。真正切分主要由更可靠的边界感受赢竞争, 例如 step closure、数量闭合、压力释放、节奏重置。
2. 拆分“边界位置”:
   - `quantity_closure` / `step_closure` / `pressure_release`: 边界在当前 tick 之后。
   - `rhythm_reset` / `continuity_drop`: 边界在当前 tick 之前。

这个修正很关键: step closure 表示当前步骤闭合, 不应该把 cue 与 reply 在当前 tick 前切开。

## 3. 通过落地

新增文件:

- `APV3.0test/apv3test/runtime/boundary.py`
- `APV3.0test/tests/test_phase2_2_boundary_segmentation.py`

更新文件:

- `APV3.0test/apv3test/config/paradigm_config.py`
- `APV3.0test/apv3test/runtime/__init__.py`

新增 API:

- `FocusTick`
- `BoundaryFeelingSA`
- `BoundarySegment`
- `BoundaryFeelingSegmenter`

已实现能力:

- 跨 tick SA bundle 分段。
- 同 tick bundle 保留为同一单元。
- 边界感受来源可审计。
- 支持文本、视觉、听觉、行动、感受等任意 SA 标签混合。
- 切分后的 segment 可以继续喂给 `ParadigmDiscoveryEngine` 和 Phase2.1 DP 对齐。

## 4. 严谨验收测试

已运行:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
45 passed in 1.88s
```

已运行编译检查:

```powershell
$files = Get-ChildItem -Path APV3.0test\apv3test\config,APV3.0test\apv3test\runtime -Filter *.py | ForEach-Object { $_.FullName }; python -m py_compile @files
```

结果: 通过。

已运行禁用通道扫描:

```powershell
rg -n "keyword|answer_table|student_side_llm|branch_alignment|math_process_tokens|regex|full_sentence_macro" APV3.0test\apv3test APV3.0test\tests
```

结果: 无命中。

新增测试覆盖:

- `test_boundary_feeling_segments_cross_tick_units_without_turn_flag`
- `test_boundary_supports_mixed_modality_first_class_sa`
- `test_boundary_is_independent_of_label_text_when_signals_match`
- `test_segmented_units_can_feed_paradigm_discovery`

## 5. 最终汇总

本阶段可以确认:

- APV3.0test 已有“跨 tick 范式学习”的最小入口。
- 连续 tick 流不会因为 label 不重合而被每 tick 切碎。
- 同 tick 多模态 bundle 可以作为一个整体保留。
- 切分后的 unit 能继续进入范式发现与 DP 对齐。

仍不能宣称:

- 完整自由中文开放对话底座完成。
- 完整 APV3.0 能量系统已接线。
- 完整跨模态感知原型 token 已实现。
- 快系统 habit action / habit thought 已完成。

下一步建议:

1. Phase2.3: 关系重叠 coherence 与列质量评估, 让 slot/shared/fixed 的判断不只依赖占用率。
2. Phase2.4: Viterbi 角色联合解码, 防止 per-column 独立分类抖动。
3. Phase2.5: 跨模态感知原型 token 最小门, 为“黄色苹果”类泛化恢复真正的一等 SA 输入。
4. Phase3: 快系统 habit action / habit thought 的最小行动后果记忆闭环。
5. Phase4: 小型自由中文开放对话 runtime, 把边界、DP、范式发现、草稿行动、持久化学习串起来。
