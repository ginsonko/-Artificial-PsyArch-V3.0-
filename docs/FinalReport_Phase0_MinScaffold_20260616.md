# APV3.0test Phase0 最小试验场最终报告

日期: 2026-06-16

## 1. 设计

本轮目标不是继续修旧自由对话底座的表象问题, 而是在 `APV3.0test` 中建立一个平行、干净、可验证的最小地基:

- Bn 仍然表示“当前场像过去哪些经验”。
- Cn 仍然沿显式 successor edge 读取“这个 B 之后通常发生什么”。
- 持久化不是新算法, 只是把 AP-native 运行本体落到磁盘后等价恢复。
- `learned vector`、`successor_virtuals`、白箱审计只能是辅助证据, 不能成为策略层。
- 白箱审计与运行本体分库; audit 可删, runtime 不得依赖 audit。
- 所有新观察量默认 observe-only, 不改变旧行为。

本轮冻结了两份契约:

- `APV3.0test/docs/interface_contracts.md`
- `APV3.0test/docs/persistence_contract.md`

## 2. 审查完善

对 v2.1 范式通道设计与 APV3.0 能量本体设计进行了对抗性审查, 结论冷保存于:

- `APV3.0test/docs/AdversarialReview_and_FinePlan_20260616.md`

关键审查结论:

- `L′` 必须拆成 `state_debt` 与 `action_free_energy`, 避免 EV 符号歧义。
- `lambda_fast` 应为加性 logit 观测量, 不采用乘积门。
- `tau_focus` 与 `recall_breadth` 是两个旋钮: 惊时焦点收紧, 解释阶段候选召回可扩展。
- `PredictionRuler` 不能保留旧实现中的 `or 1.0` 和硬地板语义。
- `ActionOutcomeMemory` 是唯一行动后果写入器; 范式-行动绑定只能只读聚合。
- 范式通道 observe/recall/score 阶段只读 `OnlineEmbeddingStore`; self-emission 不能抬 support。

## 3. 通过落地

已落地的最小代码:

- `APV3.0test/apv3test/config/energy_config.py`
- `APV3.0test/apv3test/config/persistence_config.py`
- `APV3.0test/apv3test/runtime/energy_observer.py`
- `APV3.0test/apv3test/runtime/prediction_ruler.py`
- `APV3.0test/apv3test/runtime/runtime_state_codec.py`
- `APV3.0test/apv3test/runtime/sqlite_runtime_store.py`
- `APV3.0test/apv3test/runtime/sqlite_audit_store.py`

新增的 SQLite 分库包装:

- `SQLiteRuntimeStore`: 只保存 AP-native runtime ontology state 的压缩 envelope。
- `SQLiteAuditStore`: 只保存可删的白箱观察事件。

本轮修复了两个 Windows/SQLite 生命周期问题:

- SQLite connection context 只自动提交/回滚, 不自动关闭; 因此 audit 文件无法删除。已改为 `contextlib.closing(...)`。
- 改成显式关闭后, 需要显式 `commit()`; 否则测试进程内看不到落盘行。已补 `commit()`。

## 4. 严谨验收测试

已运行:

```powershell
python -m pytest APV3.0test/tests -q
```

结果:

```text
12 passed in 0.34s
```

已运行:

```powershell
$files = Get-ChildItem -Path APV3.0test\apv3test\config,APV3.0test\apv3test\runtime -Filter *.py | ForEach-Object { $_.FullName }; python -m py_compile @files
```

结果: 通过。

已运行禁用通道扫描:

```powershell
rg -n "keyword|answer_table|student_side_llm|branch_alignment|math_process_tokens|learned_vector_candidate_weight|_label_overlap_rank_decay|regex|full_sentence_macro" APV3.0test\apv3test APV3.0test\tests
```

结果: 代码与测试目录无命中。

当前测试覆盖:

- 能量观察量拆分与符号方向。
- `lambda_fast` 加性 logit。
- `tau_focus` 惊/歧义方向。
- `PredictionRuler` 空 tick 衰减与 live external ruler。
- runtime state 压缩、sha256、往返恢复。
- runtime 不依赖 audit。
- SQLite runtime/audit 分库契约。
- 删除 audit db 后 runtime 仍可恢复。

## 5. 最终汇总

本轮已经完成 APV3.0test 的 Phase0 最小地基:

- 理论边界已冷保存。
- 最小包可 import。
- 能量 observer 与 prediction ruler 有单元测试。
- runtime ontology state 可全真压缩保存和恢复。
- runtime db 与 audit db 已有最小 SQLite 分库实现。
- audit 可删不影响 runtime 的契约已被测试锁住。

边界声明:

- 这还不是自由中文对话底座完成。
- 还没有接入旧 APV2.1 runtime 主链。
- 还没有证明旧技能包可在持久化态复现。
- 还没有做 Fresh300。
- 当前成果是为下一阶段防止“数据库越修越乱”打下的最小、可测、可回滚地基。

## 6. 下一步

建议下一轮按以下顺序继续:

1. Phase0.1: 配置收口。把旧实现中的魔数迁入具名 config, 初值保持旧值, 不改变行为。
2. Phase0.2: 单一 scorer golden-lock。把 runtime scorer 与 audit scorer 合并成单一纯函数, 用 preset 表达差异。
3. Phase0.3+: 真实 runtime ontology schema。把 `OnlineEmbeddingStore`、transitions、`ActionOutcomeMemory`、`ParadigmSA`、`PerceptPrototype` 分表保存, 而不是只保存整包 state envelope。
4. Phase1.0: 内存态 vs 持久化态 parity probe。比较 Bn top-k、Cn 后继、learned vectors、transitions、action outcome、draft token、commit 清空。
5. Phase2+: 范式通道最小三阶段。先做 echo imitation、successor prediction、multi-reply aggregation, 再做 slot/grammar/style。
6. 只有 parity 与小样本对话稳定后, 才进入旧技能复训和 Fresh300。

