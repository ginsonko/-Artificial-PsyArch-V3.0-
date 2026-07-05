# APV3.0test Phase2.5 跨模态感知原型 token 最小门报告

日期: 2026-06-16

## 1. 设计

本阶段继续 APV3.0-test 主线, 目标是补上“任意模态 SA 获得稳定可聚合 token”的最小门。

此前 Phase2.1-2.4 已经完成:

- 边界感受切分连续 tick 流。
- 锚相对 DP 对齐。
- 关系重叠 coherence。
- Viterbi 角色联合解码。

但如果非文本 SA 每次都是实例/位置键, 例如 `vision_obj::3_3`, 那么统计永远无法跨帧聚合, 范式通道没有稳定底物。因此本阶段实现 `PerceptPrototypeStore`:

- 输入: 任意感知型 SA 的数值特征、认知压、连续性锚点、模态 trace。
- 输出: 稳定 `percept::prototype::...` token。
- 同一感知簇反复出现时复用同一个 token。
- 明显不同感知簇不合并。
- 原型数量有上限, 按 support / last_tick 保留更有用的原型。

拟人原则:

- 人不是记住每一帧的位置编号, 而是把跨位置、跨瞬间的同一对象稳定成“同一个东西”。
- 但人也不会把所有感知都混成一个对象; 原型需要不过度合并。
- 跨模态学习必须先有稳定的一等 SA token, 再谈范式组合与泛化。

重要边界:

- PerceptPrototype 只是跨模态前置条件, 不等于跨模态泛化成功。
- 不按视觉/听觉/文本做硬过滤, 只看通用特征向量与连续性锚点。
- 不生成回复, 不写策略, 不替代范式通道。

## 2. 审查完善

对设计稿核对:

- `Design_持久化中文对话底座_范式通道重构_v2_20260615.md` §3.9 明确: 非文本 SA 必须先经感知原型层获得稳定 percept token。
- `Design_APV3.0能量本体数学模型_20260615.md` §13.6 明确: PerceptPrototype 是跨模态前置条件, 不是跨模态成功本身。

四子门边界:

1. 位置不变性: 同一物体不同位置应落到同一/相近 percept token。
2. 连续性锚点: 跨帧同物经 continuity anchor 拉在一起。
3. 支持度: percept token 需要积累 support。
4. 稳定 token: 喂给范式通道的是稳定 percept token, 不是位置/槽字符串。

本阶段完成的是最小码本门:

- 位置/表面变化下稳定 token。
- 连续性锚点参与匹配。
- 支持度累积。
- token 持久化。

仍未完成:

- 完整视觉/听觉感受器。
- 完整跨模态范式槽填充。
- 黄色苹果 AP-native 复刻。

## 3. 通过落地

新增文件:

- `APV3.0test/apv3test/runtime/percept_prototype.py`
- `APV3.0test/tests/test_phase2_5_percept_prototype.py`

更新文件:

- `APV3.0test/apv3test/config/paradigm_config.py`
- `APV3.0test/apv3test/runtime/__init__.py`

已有接口复用:

- `LearnedPerceptPrototype`
- `LearningEpisodeWriter`
- `SQLiteRuntimeStore.percept_prototypes`

新增 API:

- `PerceptObservation`
- `PerceptPrototype`
- `PerceptPrototypeResult`
- `PerceptPrototypeStore`

本阶段没有新增数据库类型, 而是通过已有 AP-native runtime ontology 保存:

```text
state["percept_prototypes"] -> SQLiteRuntimeStore.percept_prototypes
```

## 4. 严谨验收测试

已运行:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
58 passed in 1.21s
```

已运行编译检查:

```powershell
$files = Get-ChildItem -Path APV3.0test\apv3test\config,APV3.0test\apv3test\runtime -Filter *.py | ForEach-Object { $_.FullName }; python -m py_compile @files
```

结果: 通过。

已运行源码禁用通道扫描:

```powershell
rg -n --glob "*.py" "keyword|answer_table|student_side_llm|branch_alignment|math_process_tokens|regex|full_sentence_macro" APV3.0test\apv3test APV3.0test\tests
```

结果: 无命中。

探针结果:

```text
percept::prototype::proto:0001 percept::prototype::proto:0001 True
percept::prototype::proto:0002 True
2 [('vision',), ('audio',)]
```

含义:

- 同一对象不同帧/位置复用同一 token。
- 明显不同感知生成新 token。
- 原型码本保留模态 trace, 但不靠模态过滤决定能否匹配。

新增测试覆盖:

- `test_same_percept_reuses_stable_token_across_surface_changes`
- `test_distinct_percepts_do_not_overmerge`
- `test_prototype_limit_is_bounded_by_support_and_recency`
- `test_percept_prototypes_persist_through_learning_writer_and_sqlite`
- `test_percept_prototype_is_prerequisite_not_cross_modal_claim`

## 5. 最终汇总

本阶段可以确认:

- APV3.0test 已具备最小感知原型 token 码本。
- 非文本/跨模态 SA 可以获得稳定 `percept::prototype::*` token。
- 原型可经 `LearningEpisodeWriter` 写入 AP-native runtime state, 并通过 SQLite 保存恢复。
- 原型数量有界。
- 本阶段没有引入关键词路由、答案表、模态特例或策略层。

仍不能宣称:

- 完整跨模态泛化已完成。
- 黄色苹果 AP-native 复刻已完成。
- 完整自由中文开放对话 runtime 已完成。

下一步建议:

1. Phase2.6: 将 percept token 接入范式槽填充候选, 做黄色苹果最小 AP-native 复刻。
2. Phase3: habit action / habit thought 最小闭环, 形成快系统熟练复刻。
3. Phase4: 小型自由中文开放对话 runtime, 串起边界、DP、coherence、Viterbi、percept token、草稿行动、持久化学习。
