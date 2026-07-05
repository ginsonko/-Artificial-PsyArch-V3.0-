# APV3.0test Phase2.4 Viterbi 角色联合解码报告

日期: 2026-06-16

## 1. 设计

本阶段继续 APV3.0-test 主线, 目标是补上范式通道中的“角色联合解码”。

Phase2.1 已有锚相对 DP 对齐, Phase2.2 已有边界感受切分, Phase2.3 已有关系重叠 coherence 与列质量评估。但如果每一列都独立判断 `fixed_anchor / slot / shared_fragment`, 长序列、重复结构、多模态混合场景中可能出现角色抖动。

拟人原则:

- 人类理解结构时, 不会完全孤立地判断每个位置是什么角色。
- 人会利用前后连续性、节奏、重复、收束感来形成一段稳定的结构感。
- 但人也不会无视清楚的重复证据; 强列证据应优先, 上下文只做弱耦合。

因此本阶段新增 `RoleViterbiDecoder`:

- emission: 每列自身证据, 如占用率、distinct token 数、relation_coherence。
- transition: 相邻角色弱耦合, 如 fixed 连续、fixed→slot、slot→shared。
- 输出: 全局最优角色序列。

重要边界:

- Viterbi 不读取中文词义。
- Viterbi 不按模态过滤。
- Viterbi 不生成回复, 不写奖惩, 不改 Bn/Cn 主链。
- Viterbi 只是范式列角色解释层, 不是策略层。

## 2. 审查完善

本阶段审查中发现并修正两轮问题。

### 问题一: 过度平滑压坏强列证据

初版 Viterbi 过度偏向 slot 连续, 导致:

- `茅庐 / 臣于草庐之中` 中的 `庐` 被误判为 slot。
- `vision::red / text::红色 / audio::red_word -> object::apple` 中的 `object::apple` 被误判为 slot。

修正:

- 全占用单一 token 的列获得更强 fixed/shared 证据。
- slot 只在多样、低占用或关系槽证据明显时赢。

### 问题二: shared_fragment 与 fixed_anchor 的结构边界

第二版又把长 slot 后的共同列一律拉成 fixed_anchor, 或把单槽后的最终目标拉成 shared_fragment。

修正:

- 如果共同列出现在较长 slot 块后, 更像重收敛 shared_fragment。
- 如果共同列是单槽后的最终稳定目标, 更像 fixed_anchor。
- 这仍然只看结构路径和列位置, 不看具体词或模态。

这个修正符合拟人原则:

- 结构中段的共同收束像“共享片段”。
- 句末或目标位的稳定对象像“固定锚”。

## 3. 通过落地

新增文件:

- `APV3.0test/apv3test/runtime/role_decode.py`
- `APV3.0test/tests/test_phase2_4_role_viterbi.py`

更新文件:

- `APV3.0test/apv3test/config/paradigm_config.py`
- `APV3.0test/apv3test/runtime/alignment.py`
- `APV3.0test/apv3test/runtime/__init__.py`

新增 API:

- `RoleDecodeResult`
- `RoleViterbiDecoder`

`AnchorRelativeAligner` 现在流程为:

```text
DP 对齐 -> 初始列特征 -> relation_coherence -> RoleViterbiDecoder -> 最终 columns
```

## 4. 严谨验收测试

已运行:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
53 passed in 1.20s
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

探针结果:

```text
fixed ('fixed_anchor', 'fixed_anchor')
我/我 fixed_anchor
在/在 fixed_anchor

reconverge ('slot', 'slot', 'slot', 'shared_fragment', 'slot', 'slot')
庐/庐 shared_fragment
```

新增测试覆盖:

- `test_viterbi_keeps_fixed_successor_phrase_stable`
- `test_viterbi_prefers_shared_fragment_after_slot_block`
- `test_viterbi_is_modality_agnostic_for_parallel_roles`
- `test_viterbi_decoder_outputs_one_role_per_column`
- `test_discovery_uses_joint_role_sequence_for_slot_types`

## 5. 最终汇总

本阶段可以确认:

- APV3.0test 已具备最小角色联合解码。
- 固定短语不会被误拆成 shared/slot。
- 长 slot 后的共同收束能被解释成 shared_fragment。
- 多模态 SA 仍走同一角色解码机制, 没有模态特例。
- Viterbi 平滑只做弱耦合, 不压倒明确列证据。

仍不能宣称:

- 完整跨模态感知原型 token 已完成。
- 完整 habit action / habit thought 已完成。
- 完整自由中文开放对话 runtime 已完成。

下一步建议:

1. Phase2.5: 跨模态感知原型 token 最小门, 支持黄色苹果类泛化。
2. Phase3: habit action / habit thought 最小闭环, 形成快系统熟练复刻。
3. Phase4: 小型自由中文开放对话 runtime, 串起边界、DP、coherence、Viterbi、范式发现、草稿行动、持久化学习。
