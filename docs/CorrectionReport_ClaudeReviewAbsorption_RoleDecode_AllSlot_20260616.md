# APV3.0test Claude 评估吸收纠偏报告

日期: 2026-06-16

## 1. 设计理解

本轮用户提供了外部评估意见。评估指出三个问题:

1. `role_decode.py` 的 `_emission()` 里出现 `prev_role / index / last_index` 等位置/前序结构判据, 可能把“自发范式发现”退化成形状模板。
2. `all_slot_confidence_floor` 给全槽冷启动范式最低 conf, 可能让证据不足的范式过早参与竞争。
3. Phase2.6 黄色苹果测试预填了 `focus_tokens/candidate_pool`, 只能证明下游槽填充, 不能证明完整感知到 focus 链路。

本轮吸收原则:

- 吸收 1: emission 必须只读列统计, 不读前序角色和位置。
- 吸收 2: 移除 all-slot conf 地板; 证据不足的全槽范式不暴露。
- 部分吸收 3: 保留“percept token 可进槽”的下游证明, 但改成带结构锚的关系证据; 不宣称完整跨模态泛化或感知到 focus 链路完成。

## 2. 审查完善

代码审查坐实的问题:

- `RoleViterbiDecoder._emission()` 旧实现确实读取了 `prev_role`, `index`, `last_index`。
- `AnchorRelativeAligner._classify_columns()` 旧实现有 `variable_seen`, 会提前给 fixed/shared 赋形状倾向。
- `ParadigmDiscoveryEngine._confidence()` 旧实现对 all-slot 范式使用 `all_slot_confidence_floor`。

纠偏后的规则:

- `_emission(column, role)` 只使用列级统计: occupancy、distinct token 情况、relation_coherence、relation_pair_count。
- Viterbi transition 仍可使用 `prev_role` 做弱平滑, 但 transition 不直接读取位置 index。
- aligner 初始列统一为 `slot` 占位, 角色由 Viterbi 统一解码。
- conf 不再有 all-slot 地板。全槽范式若无关系重叠证据, `conf=0`, `ParadigmSlotFiller` 不暴露草稿。
- 感知槽正例改为 `field::color / field::object` 结构锚 + percept token 槽, 让槽填充来自真实关系证据。

## 3. 通过落地

更新文件:

- `APV3.0test/apv3test/runtime/role_decode.py`
- `APV3.0test/apv3test/runtime/alignment.py`
- `APV3.0test/apv3test/runtime/paradigm_discovery.py`
- `APV3.0test/apv3test/runtime/paradigm_fill.py`
- `APV3.0test/apv3test/config/paradigm_config.py`
- `APV3.0test/tests/test_phase2_1_anchor_relative_dp.py`
- `APV3.0test/tests/test_phase2_4_role_viterbi.py`
- `APV3.0test/tests/test_phase2_6_percept_slot_fill.py`
- `APV3.0test/tests/test_phase4_0_minimal_dialogue_runtime.py`
- `APV3.0test/tests/test_phase4_1_small_skill_reproduction.py`

关键改动:

- 删除 `_emission()` 中的 `prev_role/index/last_index` 入参。
- 删除 `variable_seen` 预分类。
- 删除 `all_slot_confidence_floor` 配置和使用点。
- `ParadigmSlotFiller.fill()` 在 `paradigm.conf <= 0` 时返回空候选。
- 新增测试: all-slot cold-start 缺少关系证据时不暴露。
- 感知槽正例改为结构锚教学, 不再靠冷启动地板。

## 4. 严谨验收测试

相关测试:

```powershell
python -m pytest APV3.0test\tests\test_phase2_1_anchor_relative_dp.py APV3.0test\tests\test_phase2_4_role_viterbi.py APV3.0test\tests\test_phase2_6_percept_slot_fill.py APV3.0test\tests\test_phase4_0_minimal_dialogue_runtime.py APV3.0test\tests\test_phase4_1_small_skill_reproduction.py -q
```

结果:

```text
23 passed
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
83 passed in 1.67s
```

禁用通道扫描:

```powershell
rg -n --glob "*.py" "keyword|answer_table|student_side_llm|branch_alignment|math_process_tokens|regex|full_sentence_macro|黄色苹果" APV3.0test\apv3test
```

结果: 无命中。

形状先验扫描:

```powershell
rg -n "all_slot_confidence_floor|def _emission\(.*prev_role|def _emission\(.*index|last_index|variable_seen" APV3.0test\apv3test APV3.0test\tests
```

结果: 无命中。

临时脚手架词扫描:

```powershell
rg -n "TODO|FIXME|hardcode|shortcut|route|magic" APV3.0test\apv3test\runtime\role_decode.py APV3.0test\apv3test\runtime\alignment.py APV3.0test\apv3test\runtime\paradigm_discovery.py APV3.0test\apv3test\runtime\paradigm_fill.py APV3.0test\tests\test_phase2_6_percept_slot_fill.py
```

结果: 无命中。

## 5. 最终汇总

本轮纠偏后可以确认:

- `role_decode` 不再把位置/前序结构写入 emission。
- all-slot 冷启动不再靠 conf 地板过门。
- 感知槽正例需要结构锚和关系证据, 更符合“教学证据足够才暴露范式”。
- 全量测试从 82 增加到 83, 且所有扫描干净。
- Claude 评估中的核心有效批评已经吸收。

仍不能宣称:

- 完整感知到 focus 链路已完成。
- 完整跨模态泛化已完成。
- 完整自由中文开放对话底座已完成。

下一步建议:

Phase4.2 继续扩展中文对话微技能和数学过程范式时, 必须沿用本轮纠偏后的门:

- 不给冷启动范式地板。
- 不用位置规则塑造角色。
- 感知槽必须有上游 focus / prototype / 关系证据。
- 失败时优先增加教学证据或修上游统计, 不回退到形状模板。
