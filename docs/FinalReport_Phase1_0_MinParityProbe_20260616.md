# APV3.0test Phase1.0 最小内存态 vs SQLite 恢复态 parity probe 报告

日期: 2026-06-16

## 1. 设计

本轮目标是建立第一道持久化等价性门:

> 同一份 AP runtime ontology state 在内存态运行 probe, 保存到 SQLite 后重新恢复, 再运行同一组 probe, 关键结果必须一致。

本轮不做完整 ANN/Bn 检索, 不接旧自由对话主链, 不跑 Fresh300。它只验证:

- Bn 候选评分结果在内存态和恢复态一致。
- Cn 显式后继边在内存态和恢复态一致。
- `OnlineEmbeddingStore` token/vector/support 不丢失。
- `ParadigmSA` 候选不丢失。
- `ActionOutcomeMemory` 行动后果倾向不丢失。
- `PerceptPrototype` 感知原型不丢失。
- SQLite projection 表本身可读取, 不是只靠压缩 blob 往返。

最小 fixtures 覆盖五类能力:

- 问候: `你好 -> 我在`
- 成语后继: `三顾 -> 茅庐`
- 简单数学范式: `simple_math_template -> write_step_then_compute`
- 黄色苹果泛化: `yellow+apple -> compose_color_object`
- 打断恢复压力: `task_interrupted -> hold_pressure_then_resume`

## 2. 审查完善

审查结论:

- 当前 `SQLiteRuntimeStore` 已保存全真压缩 state envelope, 可以保证不失真恢复。
- Phase0.3 新增的 projection 表已经覆盖 `online_embedding_tokens`、`explicit_transitions`、`paradigm_sa`、`action_outcomes`、`percept_prototypes`。
- Phase1.0 仍缺少一个纯函数 probe 层, 用来在内存态和恢复态上运行同一批 case 并比较结果。
- 本轮不应该引入旧主链中的策略硬编码, 也不应该把 audit db 纳入 runtime 依赖。

因此新增 `parity_probe.py` 时遵守:

- 只读 state。
- 只使用 `score_recall_candidate` 单一 scorer。
- 默认使用 `APV3_NATIVE_PRESET`, learned-vector 仍为 trace-only。
- Cn 只沿 `transitions` 中的显式后继边读取。
- 不读取 audit db。

## 3. 通过落地

新增/更新文件:

- `APV3.0test/apv3test/runtime/parity_probe.py`
- `APV3.0test/apv3test/runtime/__init__.py`
- `APV3.0test/tests/test_phase1_parity_probe.py`

新增 API:

- `ParityProbeCase`
- `ProbeResult`
- `run_parity_probe(state, cases)`
- `assert_probe_parity(left, right)`

新增测试:

- `test_phase1_probe_matches_expected_anchors_in_memory_state`
- `test_phase1_memory_state_matches_sqlite_rehydrated_state`
- `test_phase1_projection_counts_cover_all_probe_domains`
- `test_phase1_sqlite_projection_preserves_probe_payloads`

## 4. 严谨验收测试

已运行:

```powershell
python -m pytest APV3.0test/tests -q
```

结果:

```text
20 passed in 0.98s
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

验收覆盖:

- 五类 probe 的内存态期望锚点全部命中。
- 同一 state 保存到 SQLite 并恢复后, `run_parity_probe` 结果与内存态完全一致。
- projection 表数量覆盖全部 probe 域:
  - `online_embedding_tokens = 6`
  - `explicit_transitions = 5`
  - `paradigm_sa = 5`
  - `action_outcomes = 3`
  - `percept_prototypes = 1`
- projection payload 可读且关键字段不丢失:
  - `你好.support = 6.0`
  - `三顾 -> 茅庐` 后继边存在
  - `p:color_object` 范式存在
  - `focus_task_pressure.drive_bias = 0.42`
  - `visual:yellow_apple` 保留颜色/对象特征

## 5. 最终汇总

本轮 Phase1.0 最小 parity probe 已通过。

这说明:

- APV3.0test 当前的 runtime state 压缩保存与恢复没有破坏最小 AP 运行本体。
- SQLite projection 表可以作为后续 Bn/Cn/范式/行动后果检索的基础索引层。
- audit db 仍不参与运行恢复。
- 单一 scorer 在持久化往返中保持确定性。

边界声明:

- 这还不是自由中文开放对话底座完成。
- 这还不是旧 GL 技能包完整复现。
- 当前 Bn 候选特征来自 fixture, 不是完整 ANN/索引检索。
- 当前 Cn 读取是显式 transition 精准读取, 还未接真实 runtime 的后继竞争。
- 还没有测试草稿逐字输出、提交清空和实时学习写入。

## 6. 下一步

建议下一轮进入 Phase1.1:

1. 增加 “学习写入 -> 保存 -> 恢复 -> 再召回” probe。
2. 让一个新教学 episode 写入:
   - learned token/vector/support
   - transition
   - ParadigmSA
   - ActionOutcomeMemory
3. 保存 SQLite 后重启恢复。
4. 验证新学内容能在恢复态参与 Bn/Cn/范式/行动后果 probe。
5. 然后再进入 Phase1.2: 逐字草稿/commit 清空 parity。
6. Phase1.1 和 Phase1.2 都过后, 才适合接旧 GL 技能包小批复现。

