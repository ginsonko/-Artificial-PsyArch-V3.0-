# APV3.0test Phase2.6 percept token 接入范式槽填充报告

日期: 2026-06-16

## 1. 设计

本阶段继续 APV3.0-test 主线, 目标是把 Phase2.5 的 `percept::prototype::*` 稳定 token 接入范式槽填充候选, 做最小“黄色苹果”AP-native 复刻。

这里的“复刻”不是输出中文整句 `黄色苹果`, 而是证明:

- 感知原型 token 可以作为一等 SA 进入范式槽。
- 范式槽填充从当前焦点/候选池/successor_virtuals 中选 token。
- 输出是带 `text_visible_draft_token/v1` 游标 metadata 的逐 token 草稿候选。
- 不使用目标串、不使用答案表、不使用关键词路由、不一 tick 倾倒整句。

拟人原则:

- 人在看到一个新对象组合时, 会用当前注意中的对象/属性来填已有结构槽。
- 当前工作记忆的顺序会影响组合顺序。
- 同一候选不会无缘无故填满多个不同槽, 会有同一草稿内的疲劳/去重。

重要边界:

- 这是最小 AP-native 复刻, 不是完整自由对话 runtime。
- 输出仍是 percept token 序列, 后续还要接自然语言表层化与行动器逐 tick 执行。
- Phase3 仍需专门做快系统 habit action / habit thought, 解决“不加思索”的熟练行动。

## 2. 审查完善

对设计稿核对:

- §3.6 要求 slot 填充候选全模态, 不按 modality 过滤。
- §3.6 successor_virtuals 红线要求:
  - 只来自显式 transition / FocusSuccessorBias / active ParadigmSA slot_type 近邻。
  - 只作候选进入 scorer, 不绕过竞争。
  - 有 trace, 有界。
- §3.6 B9 要求草稿面即游标, 不能一 tick 倾倒整句。

本阶段发现并修正两个问题:

1. 同分候选使用字典序会破坏当前工作记忆顺序。
   - 修正: 同分时按候选池/焦点顺序。
   - 这不是内容规则, 而是工作记忆顺序感。

2. 全 slot 冷启动范式没有固定锚, conf 可能被质量乘积压到 0。
   - 修正: 对“全 slot 且已有 support”的冷启动范式给极小 `all_slot_confidence_floor`。
   - 这不是任务规则, 只是让新发现的全槽结构有最低竞争资格。

## 3. 通过落地

新增文件:

- `APV3.0test/apv3test/runtime/paradigm_fill.py`
- `APV3.0test/tests/test_phase2_6_percept_slot_fill.py`

更新文件:

- `APV3.0test/apv3test/config/paradigm_config.py`
- `APV3.0test/apv3test/runtime/paradigm_discovery.py`
- `APV3.0test/apv3test/runtime/__init__.py`

新增 API:

- `FillCandidate`
- `DraftCandidate`
- `ParadigmSlotFiller`

核心链路:

```text
PerceptPrototypeStore -> percept token
ParadigmDiscoveryEngine -> color/object slot paradigm
ParadigmSlotFiller -> draft candidates with cursor metadata
```

## 4. 严谨验收测试

已运行:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
62 passed in 1.36s
```

已运行编译检查:

```powershell
$files = Get-ChildItem -Path APV3.0test\apv3test\config,APV3.0test\apv3test\runtime -Filter *.py | ForEach-Object { $_.FullName }; python -m py_compile @files
```

结果: 通过。

runtime 源码禁用通道扫描:

```powershell
rg -n --glob "*.py" "keyword|answer_table|student_side_llm|branch_alignment|math_process_tokens|regex|full_sentence_macro|黄色苹果" APV3.0test\apv3test
```

结果: 无命中。

探针结果:

```text
conf 0.031606 roles ['slot', 'slot']
drafts [('percept::yellow', 'slot', ''), ('percept::apple', 'slot', 'percept::yellow')]
joined percept::yellowpercept::apple
```

含义:

- 输出来自 percept token, 不是目标中文串。
- 第二个草稿 token 带 `previous_prefix='percept::yellow'`, 保持草稿游标语义。
- 范式是两槽结构, 不是整句宏。

新增测试覆盖:

- `test_percept_tokens_fill_color_object_slots_without_target_phrase`
- `test_successor_virtuals_can_supply_missing_slot_candidate_without_bypassing_competition`
- `test_percept_slot_fill_uses_persisted_prototype_tokens_after_restore`
- `test_slot_fill_does_not_create_full_sentence_macro_or_reward_self_emission`

## 5. 最终汇总

本阶段可以确认:

- APV3.0test 已能把 percept token 接入范式槽填充候选。
- 最小黄色苹果链路已是 AP-native 结构: 当前 percept token + 范式槽 + 草稿游标。
- 没有答案表、关键词路线、整句宏、模态过滤。
- successor_virtuals 只是候选来源之一, 没有绕过竞争。

仍不能宣称:

- 完整自然语言表层化已完成。
- 完整自由中文开放对话 runtime 已完成。
- 快系统 habit action / habit thought 已完成。

后续硬目标:

1. Phase3: habit action / habit thought 最小闭环。
   - 目标: 奖惩与行动后果记忆让熟练行动/想法“不加思索”地快速复刻。
   - 需要验证快系统在低认知压、高把握、高奖励支持时能快速胜出。
   - 也要处理同一 tick 多行动协调问题, 不能破坏“同一行动器同 tick 只能一个动作”的约束。
2. Phase4: 小型自由中文开放对话 runtime。
   - 串起边界、DP、coherence、Viterbi、percept token、slot fill、草稿行动、持久化学习。
