# APV3.0test Phase2.1 锚相对 DP 对齐报告

日期: 2026-06-16

## 1. 设计

本阶段继续 APV3.0-test 路线, 不回到 APV2.1 修补。

Phase2.0 已经证明有最小范式自发现雏形, 但它仍主要依赖最长前缀/后缀和中段 slot 的简化抽取。这个方法无法严格支持设计稿中要求的:

- 变长序列跨 gap 后重新收敛到同一列。
- 列不是 raw position, 而是锚相对对齐后的结构位置。
- 低占用列自然成为 slot 信号。
- 共享片段必须来自多条观测共同支持, 不能把单侧插入误判成共享锚。

因此本阶段新增一个有界 Needleman-Wunsch 风格的锚相对 DP 对齐算子:

- 输入: 多条 SA/token 序列。
- 输出: 对齐列 `AlignmentColumn`。
- 每列携带: `values`, `occupancy`, `distinct_tokens`, `role`, `anchor_label`。
- 角色先做最小三类: `fixed_anchor`, `slot`, `shared_fragment`。

重要边界:

- 对齐器只是结构观察算子, 不选择回复, 不写奖惩, 不移动向量, 不改变行动策略。
- 它服务于范式通道的“列配准”, 不是新的 policy 层。
- DP 的权重全部进入 `APV3ParadigmDiscoveryConfig`, 作为后续 AdaptiveTuner 可接管的具名参数, 不藏隐式常数。

## 2. 审查完善

对设计稿核对:

- 对应 `Design_持久化中文对话底座_范式通道重构_v2_20260615.md` §3.2 的“锚相对有界全局对齐”。
- 对应 §3.3 的“按列方差/占用率决定固定锚、槽、共享片段”。
- 对应 §12 的“有界预算”, 当前实现先限制 `alignment_max_len` 与 `alignment_max_window`, 后续再补倒排候选池, 避免全桶两两 DP。

本阶段发现并修正一个语义风险:

- 初版分类会把变量区后的单侧 gap 列标成 `shared_fragment`。
- 这违反“共享片段必须由多个观测共同支持”。
- 已修正为: 只有至少两个观测同时出现同一 token 的列, 才能是 `shared_fragment`; 单侧插入/删除列归为 `slot`。

## 3. 通过落地

新增文件:

- `APV3.0test/apv3test/runtime/alignment.py`
- `APV3.0test/tests/test_phase2_1_anchor_relative_dp.py`

更新文件:

- `APV3.0test/apv3test/config/paradigm_config.py`
- `APV3.0test/apv3test/runtime/paradigm_discovery.py`
- `APV3.0test/apv3test/runtime/__init__.py`
- `APV3.0test/tests/test_phase2_0_paradigm_discovery_preflight.py`

落地结果:

- `ParadigmDiscoveryEngine` 现在优先通过 `AnchorRelativeAligner` 生成 columns。
- `fixed_prefix`, `shared_suffix`, `slot_spans` 从对齐列派生。
- `LearningEpisode` 仍只写 AP-native 学习证据, 不把 DP 中间态当作策略写入。

探针示例:

```text
茅庐
臣于草庐之中
```

对齐结果的关键列:

```text
庐 / 庐 -> shared_fragment
臣、于、茅/草、之、中 -> slot
```

这说明“庐”是跨 gap 后重新收敛的共享片段, 其它单侧或不一致内容保持为 slot。

## 4. 严谨验收测试

已运行:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
41 passed in 1.52s
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

- `test_anchor_relative_dp_aligns_reconvergent_tail_across_gap`
- `test_anchor_relative_dp_keeps_repeated_character_interference_bounded`
- `test_discovery_uses_dp_columns_instead_of_plain_suffix_greedy`

## 5. 最终汇总

本阶段可以确认:

- APV3.0test 已从 Phase2.0 的贪心前后缀雏形, 推进到 Phase2.1 的锚相对 DP 对齐雏形。
- 现在它能用同一机制处理固定后继、变长 slot、跨 gap 重收敛共享片段。
- 重复字干扰已有最小回归门, 防止 DP 在中文重复字符上大量错列。

仍不能宣称:

- 完整 APV3.0 数学模型已完成。
- 完整 v2.1 范式通道已完成。
- 自由中文开放对话底座已可承载全部旧 GL 技能。

下一步建议:

1. Phase2.2: 边界感受 SA 与跨 tick 切分。
2. Phase2.3: 关系重叠 coherence 与更完整的列质量评估。
3. Phase2.4: Viterbi 角色联合解码, 防止 per-column 独立分类抖动。
4. Phase2.5: 跨模态感知原型 token 最小门。
5. 这些通过后, 再做旧 GL 成功技能 3-5 个小批复现。
