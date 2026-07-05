# APV3.0test Phase2.3 关系重叠 coherence 与列质量评估报告

日期: 2026-06-16

## 1. 设计

本阶段继续 APV3.0-test 主线, 目标是补上范式通道设计中的 `coh_p`。

Phase2.1 已实现锚相对 DP 对齐, Phase2.2 已实现边界感受 SA 与跨 tick 切分。但此时列角色和范式置信度仍主要依赖占用率、support 与默认 slot quality。这个还不够, 因为:

- 位置相同不等于同一个范式槽。
- 高频出现不等于高质量范式。
- 自由中文开放对话底座需要知道“这些替换项是否在经验里扮演相似关系角色”。
- 任意模态 SA 混合学习时, 不能靠文本类别名或人工模态过滤判断槽质量。

因此本阶段新增只读关系重叠评估:

- 从已观察序列中构造每个 SA/token 的关系签名。
- 关系签名包括:
  - 左邻 `prev`
  - 右邻 `next`
  - 同单元共现 `co`
- 同一对齐列内不同 token 的关系签名越重叠, `relation_coherence` 越高。
- `relation_coherence` 进入 slot_quality, 从而参与 `conf = evidence * anchor_quality * slot_quality`。

重要边界:

- `RelationCoherenceScorer` 只读观察序列, 不写 embedding, 不写 transition, 不写 support。
- coherence 是列质量评估, 不是行动策略。
- 不按中文词、关键词、领域标签或模态名路由。

## 2. 审查完善

与设计稿核对:

- 对应 `Design_持久化中文对话底座_范式通道重构_v2_20260615.md` §3.2 / §3.3 / B8:
  - 用关系重叠替代旧 spread_p。
  - slot_quality 来自 `coh_p`。
  - 高频垃圾范式不能只靠 support 饱和变强。
- 对应 APV3.0 能量模型边界:
  - 本阶段没有新增策略通道。
  - 没有让 learned-vector 或索引层反过来定义主链。
  - 仍然保持 Bn/Cn 与行动竞争之后再谈 runtime。

本阶段没有和 Phase2.1/2.2 冲突:

- Phase2.2 负责把连续 tick 流切成 unit。
- Phase2.1 负责把 unit 序列对齐成列。
- Phase2.3 负责读出列内替换项是否有共同关系邻域。

三者是流水线关系, 不是互相替代。

## 3. 通过落地

新增文件:

- `APV3.0test/apv3test/runtime/coherence.py`
- `APV3.0test/tests/test_phase2_3_relation_coherence.py`

更新文件:

- `APV3.0test/apv3test/config/paradigm_config.py`
- `APV3.0test/apv3test/runtime/alignment.py`
- `APV3.0test/apv3test/runtime/paradigm_discovery.py`
- `APV3.0test/apv3test/runtime/__init__.py`

新增 API:

- `RelationSignature`
- `ColumnCoherence`
- `RelationCoherenceScorer`

`AlignmentColumn` 新增字段:

- `relation_coherence`
- `relation_pair_count`
- `relation_signature_tokens`

`ParadigmDiscoveryEngine` 的 confidence 更新为:

```text
conf = evidence^gamma_e * anchor_quality^gamma_a * slot_quality^gamma_s
```

其中:

- `evidence`: support 的有界趋近。
- `anchor_quality`: fixed/shared anchor 的占用质量。
- `slot_quality`: slot columns 的平均 `relation_coherence`。

## 4. 严谨验收测试

已运行:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
48 passed in 1.89s
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
good_conf 0.632121 good_col0_coh 1.0
bad_conf 0.0 bad_col0_coh 0.0
```

含义:

- 好槽位: `color::* -> object::apple` 共享右邻/共现关系, coherence 高。
- 坏槽位: `color::red / sound::loud / touch::soft` 的关系邻域分散, coherence 低, conf 被拖低。

新增测试覆盖:

- `test_relation_coherence_scores_slot_by_shared_neighbors`
- `test_low_relation_overlap_drags_discovered_paradigm_confidence_down`
- `test_relation_coherence_is_modality_agnostic_for_first_class_sa`

## 5. 最终汇总

本阶段可以确认:

- APV3.0test 范式通道已具备最小列质量评估。
- slot 不再只靠位置/次数成立, 而要看关系邻域是否重叠。
- 关系评估对任意 SA 标签成立, 支持文本、视觉、听觉、行动、感受等一等公民 SA 混合。
- 高频垃圾范式会因为 slot_quality 低而被压低。

仍不能宣称:

- 完整 Viterbi 角色联合解码完成。
- 完整跨模态感知原型 token 完成。
- 完整快系统 habit action / habit thought 完成。
- 完整自由中文开放对话 runtime 完成。

下一步建议:

1. Phase2.4: Viterbi 角色联合解码, 防止 per-column 独立分类抖动。
2. Phase2.5: 跨模态感知原型 token 最小门, 支持黄色苹果类泛化。
3. Phase3: habit action / habit thought 最小闭环, 形成快系统熟练复刻。
4. Phase4: 小型自由中文开放对话 runtime, 串起边界、DP、coherence、范式发现、草稿行动、持久化学习。
