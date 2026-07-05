# APV3.0test Phase5.0 增量式范式统计池报告

日期: 2026-06-16

## 1. 设计

Phase5.0 的目标是把 Phase2 的“批量观察后处理范式发现”推进到最小在线形态:

```text
单条 observation -> dirty bucket -> 局部统计更新 -> ParadigmSA PoolEntry -> SQLite restore parity
```

本轮吸收了最新评审中的三条边界:

1. **相似 context 不能走关键词近似。**
   - 角色转移 bias 的相似 context 只允许走 promoted learned vector。
   - 未 promoted 的 token 不参与跨 context 相似度泛化。
2. **惩罚衰减复用行动后果同类机制。**
   - 范式暴露门的 punishment pressure 使用 `APV3HabitConfig.support_half_life` 和 `recency_half_life_ticks`。
   - 不另起一套惩罚常数。
3. **统计池不能让范式脱离状态池。**
   - `paradigm_observations` / `paradigm_stats` 保存细节统计。
   - `paradigms` 同步保存 `ParadigmSA` 运行条目。
   - `state_field_items` 同步保存范式的状态池入口, 使范式仍可进入能量场。

教学等价边界:

- 自然教学和 LLM 标准教学可以有不同 `source_kind` / provenance。
- 进入 runtime 竞争的 `ParadigmSA` 必须等价。
- LLM 不得写入 `llm_policy`、答案表、关键词路由或自然教学无法产生的特殊字段。

## 2. 审查完善

### 2.1 为什么不直接重写 Phase2

Phase2 的 DP/Viterbi/Coherence 已经通过多个门, 当前问题不是数学算子本身不可用, 而是调用形态仍像批处理。Phase5.0 选择保留这些算子, 但把调用范围限制在 dirty bucket:

```text
新观察只影响所属 cue/case bucket
不全局重算所有范式
后台全量重算只能作为审计或压缩, 不进入 tick 主链
```

### 2.2 为什么 ParadigmSA 仍要进状态池

如果只把范式放进独立统计 store, 范式就会脱离 AP 能量动力学。Phase5.0 因此把统计细节与运行对象分开:

- `paradigm_stats`: 统计细节。
- `paradigms`: 运行态 `ParadigmSA`。
- `state_field_items`: 状态池入口。

这样范式可以被注意力、能量、惩罚、疲劳和后续快/慢系统共同调度。

### 2.3 教学等价修正

测试中发现 `ParadigmSA.anchor_meta` 如果保存 `last_observation_id`, 自然教学和 LLM 教学会因为 observation id 不同而 runtime 条目不等价。

修正:

- observation id 保留在观察池/统计池。
- `ParadigmSA.anchor_meta` 只保留稳定运行引用:
  - bucket
  - stats_ref

## 3. 通过落地

新增/修改文件:

- `APV3.0test/apv3test/runtime/incremental_paradigm.py`
- `APV3.0test/apv3test/runtime/role_decode.py`
- `APV3.0test/apv3test/runtime/alignment.py`
- `APV3.0test/apv3test/runtime/paradigm_discovery.py`
- `APV3.0test/apv3test/runtime/sqlite_runtime_store.py`
- `APV3.0test/apv3test/runtime/__init__.py`
- `APV3.0test/apv3test/config/paradigm_config.py`
- `APV3.0test/tests/test_phase5_0_incremental_paradigm.py`

核心能力:

- `IncrementalParadigmObservation`
- `IncrementalParadigmLearner`
- `RoleTransitionStats`
- `promoted_context_similarity`
- Viterbi `transition_bias` 注入入口
- SQLite projection:
  - `paradigm_observations`
  - `paradigm_stats`
  - `role_transition_stats`

## 4. 严谨验收测试

Phase5.0 目标测试:

```powershell
python -m pytest APV3.0test\tests\test_phase5_0_incremental_paradigm.py APV3.0test\tests\test_phase2_4_role_viterbi.py APV3.0test\tests\test_sqlite_store_contract.py -q
```

结果:

```text
15 passed in 0.82s
```

全量测试:

```powershell
python -m pytest APV3.0test\tests -q
```

结果:

```text
89 passed in 2.17s
```

禁用通道扫描:

```powershell
rg -n --glob "*.py" "keyword|answer_table|student_side_llm|branch_alignment|math_process_tokens|regex|full_sentence_macro|llm_policy|if vision|if text|黄色苹果" APV3.0test\apv3test
```

结果:

```text
APV3.0test\apv3test\runtime\draft_action.py:126:        if text:
```

审查: 这是草稿 commit 时的 buffer 非空检查, 不是文本模态特权分支。

残留硬地板/旧位置语法扫描:

```powershell
rg -n "max\([^\n]*0\.1|all_slot_confidence_floor|def _emission\(.*prev_role|def _emission\(.*index|last_index|variable_seen" APV3.0test\apv3test APV3.0test\tests
```

结果: 无命中。

测试覆盖:

- 单条 observation 进入 dirty bucket。
- support 不足时不生成范式。
- support 足够时生成 `ParadigmSA` 和 `state_field_items`。
- 增量 bucket 结果与批处理 discovery 对齐。
- role transition bias 只对 promoted learned vector 相似 context 泛化。
- 未 promoted token 不参与 context 泛化。
- 近期强惩罚阻断范式暴露。
- 惩罚随 tick 衰减后可重新暴露。
- 自然教学与 LLM 标准教学写入等价 runtime evidence。
- Phase5 新统计随 SQLite 保存恢复。

## 5. 最终汇总

Phase5.0 已完成:

- APV3.0test 有了最小增量式范式统计池。
- 范式发现不再只能通过全局批处理调用, 可以逐条 observation 更新 dirty bucket。
- `ParadigmSA` 仍然是运行态/状态池对象, 没有被统计 store 隔离出去。
- Viterbi transition 已经有后天 learned bias 入口。
- learned transition bias 的 context 泛化受 promoted learned vector 约束。
- 范式惩罚暴露门复用行动后果同类衰减参数。
- 自然教学与 LLM 标准教学等价性有了最小 probe。

仍不能宣称:

- 完整 APV3.0 中文开放自由对话底座完成。
- 完整跨模态自由泛化完成。
- 完整 tick 主循环已经接入所有 Phase5 统计。
- RoleTransitionStats 已经覆盖所有上下文和行动后果。
- LLM 标准教学协议全阶段已经落地。

下一步建议:

Phase5.1 应把 `IncrementalParadigmLearner` 接入最小 tick runtime:

1. 外界输入 / 感受器 / 行动结果形成 observation。
2. commit 或 feedback 后才提高 support。
3. idle tick 做 dirty bucket 低优先级整理。
4. `RoleTransitionStats.bias_map()` 接入实时范式解码。
5. 用小型自然教学 episode 和 LLM 标准教学 episode 复现同一技能, 比较 runtime 行为。
