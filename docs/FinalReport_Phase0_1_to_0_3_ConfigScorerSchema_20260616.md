# APV3.0test Phase0.1-0.3 配置收口、单一 scorer 与 runtime schema 报告

日期: 2026-06-16

## 1. 设计

本轮继续沿用 Phase0 的边界: 不直接改旧自由对话主链, 不引入新策略硬编码, 只在 `APV3.0test` 平行试验场中建立可验证地基。

本轮目标分三层:

1. Phase0.1 配置收口: 把旧实现中已经审计出的 scorer/recall 权重变成具名配置, 初值用于 legacy golden-lock, 不让隐式常数继续藏在函数体里。
2. Phase0.2 单一 scorer: 用一个纯函数表达 runtime/audit/APV3 native 三种 preset, 避免 forked scorer 继续漂移。
3. Phase0.3 runtime ontology schema: 在全真压缩 state envelope 之外, 额外建立可查询的 AP 运行本体 projection 表, 为后续 Bn/Cn/范式/行动后果 parity probe 做准备。

核心原则:

- legacy preset 只服务行为锁定和迁移审计, 不是 APV3.0 最终策略。
- APV3 native preset 中 `learned_vector` 只能 trace-only, 不能反过来定义策略。
- disabled feature 不是隐式 `0` 魔数, 而是 preset 里可审计的特征策略。
- runtime ontology projection 来自同一个 authoritative state, 不制造第二套事实来源。

## 2. 审查完善

本轮复核的旧线风险点:

- `memory/store/memory_store.py` 中 `learned_vector_candidate_weight=4.5`。
- `memory/store/memory_store.py` 中 `_label_overlap_rank_decay=0.72`。
- `memory/store/memory_store.py` 中 forked `_score_snapshot_exact`。
- `core/action/text_actuator.py` 中 `_branch_alignment`。
- `core/action/planner.py` 中 `math_process_tokens` 和字面答案串 boost。

处理策略:

- 不把这些逻辑搬进 APV3.0 新核心。
- scorer 权重只作为具名 legacy compatibility defaults, 用于 Phase0.2 golden-lock。
- APV3 native scorer 禁止 learned-vector 强入和; learned-vector 可以出现在 breakdown 里作为 trace。
- planner/text_actuator 的数学和分支硬编码仍列为后续主链清理对象, 本轮不碰旧主链。

## 3. 通过落地

新增/更新文件:

- `APV3.0test/apv3test/config/scorer_config.py`
- `APV3.0test/apv3test/runtime/recall_scorer.py`
- `APV3.0test/tests/test_recall_scorer_golden_lock.py`
- `APV3.0test/apv3test/runtime/sqlite_runtime_store.py`
- `APV3.0test/tests/test_sqlite_store_contract.py`

新增配置:

- `APV3ScoreWeights`: scorer 权重具名化。
- `APV3ScorerPreset`: 显式表达 feature enable/disable 和 learned-vector trace-only。
- `APV3_NATIVE_PRESET`: APV3 默认策略, learned-vector trace-only。
- `LEGACY_RUNTIME_PRESET`: 旧 runtime 行为兼容 preset。
- `LEGACY_AUDIT_PRESET`: 旧 audit exact 行为兼容 preset。

新增 scorer:

- `score_recall_candidate(features, config, preset)`: 单一纯函数 scorer。
- 输出 `ScoreBreakdown`: 包含总分、每项贡献、trace-only 项。

新增 runtime ontology projection 表:

- `online_embedding_tokens`
- `explicit_transitions`
- `paradigm_sa`
- `action_outcomes`
- `percept_prototypes`

新增 runtime store 查询:

- `ontology_counts(state_id)`
- `load_ontology_projection(state_id)`

## 4. 严谨验收测试

已运行:

```powershell
python -m pytest APV3.0test/tests -q
```

结果:

```text
16 passed in 0.81s
```

已运行:

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

- legacy runtime preset 的具名权重求和。
- legacy audit preset 的显式 feature policy。
- APV3 native preset 中 learned-vector trace-only, 即使值极大也不能改变总分。
- runtime state 全真往返仍成立。
- runtime projection 表可恢复 OnlineEmbedding、transition、ParadigmSA、ActionOutcome、PerceptPrototype。
- 删除 audit db 后 runtime 仍可读。

## 5. 最终汇总

本轮完成了 Phase0.1-0.3 的最小闭环:

- 配置收口: scorer 相关权重从隐式常数变成具名 config。
- scorer 统一: runtime/audit/APV3 native 差异由 preset 表达, 不再需要 forked scorer。
- 持久化 schema: runtime db 不再只有整包 envelope, 已有可查询的 AP runtime ontology projection。
- 验收: 16/16 测试通过, 编译通过, 禁用通道扫描无命中。

边界声明:

- 这仍然不是自由中文对话底座完成。
- 当前 projection 是 state 派生表, 还不是高性能 ANN/Bn 检索实现。
- 还没有把旧 APV2.1 主链接到 APV3.0test scorer/store。
- 还没有做内存态 vs 持久化态 parity probe。
- 还没有进行旧技能复训或 Fresh300。

## 6. 下一步

下一轮建议进入 Phase1.0 parity probe 的最小版本:

1. 构造一批最小 state fixtures: 你好->我在、三顾->茅庐、简单数学范式、黄色苹果、打断恢复压力。
2. 在内存态跑 Bn/Cn/ActionOutcome/ParadigmSA projection。
3. 保存到 SQLite runtime ontology db。
4. 重新加载后跑同一批 probe。
5. 比较:
   - Bn top-k 特征分解。
   - Cn 显式后继边。
   - learned vectors / transitions。
   - action outcome drive bias。
   - ParadigmSA recall/fill 候选。
6. parity 过关后, 再考虑把旧主链的 scorer/store 调用点逐步切到 APV3.0test 的单一 scorer 和 runtime store。

