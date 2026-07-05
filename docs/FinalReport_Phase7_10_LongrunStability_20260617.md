# APV3 Phase7.10 Longrun Stability 最终报告

日期: 2026-06-17
阶段: Phase7.10
状态: 通过

## 1. 设计

Phase7.10 验证 Phase7.8/7.9 的极简中文表达底座和多轮对话流在长跑中是否稳定。

验收目标:

- 5000 tick 混合对话长跑。
- 词汇库 phrase 不被测试过程污染，也不被错误淘汰。
- phrase 支持度分布健康，不由少数 phrase 吃掉绝大多数支持。
- introspection prototype 数量稳定，不爆炸、不清空。
- cooccurrence store 容量增长有界。
- 所有 commit_text 继续满足 Phase7.8 风格红线。
- SQLite 中途多次 save/load 后，与连续运行输出等价。

## 2. 审查完善

本阶段吸收用户关于“测试污染”的提醒:

- 所有 SQLite 验收均使用 pytest `tmp_path`。
- 不写入正式 runtime DB，不污染未来用户体验环境。
- 报告和 showcase 只保存聚合指标与测试结论，不保存可误用为真实用户状态的测试 DB。

长跑第一轮发现一个真实风险: seed corpus 作为固定按钮库时，被通用 `compact()` 当作普通短期记忆淘汰，只剩少量被频繁使用的 phrase。这不符合“上线固定词库”的设计。

修复:

- `ExpressionPhraseMemory.compact()` 在 `allow_new_phrases=False` 的 seed corpus 模式下不删除 phrase。
- 支持度仍可随观察和反馈变化，但按钮本体保留。

## 3. 通过落地

新增:

- `tests/test_phase7_10_longrun_stability.py`
- `docs/FinalReport_Phase7_10_LongrunStability_20260617.md`
- `reports/APV3_Phase7_10_LongrunStability_Showcase_20260617.html`

更新:

- `apv3test/runtime/expression_phrase_memory.py`

抽样 trace:

```text
phase7_10_trace turns 1200 records 120 top5_share 0.1675 gini 0.2019 pairs 14 paradigm_pairs 14
```

目标测试执行 5000 tick 主长跑，并使用 1800 tick 序列做多次 SQLite warm-load parity。

## 4. 严谨验收测试

已执行:

```text
python -m pytest APV3.0test\tests\test_phase7_10_longrun_stability.py -q
python -m pytest APV3.0test\tests\test_phase7_10_longrun_stability.py APV3.0test\tests\test_phase7_11_user_style_mirroring.py -q
python -m pytest APV3.0test\tests\test_phase7_0_teacher_off_three_stage_milestone.py ... APV3.0test\tests\test_phase7_11_user_style_mirroring.py -q
python -m pytest APV3.0test\tests -q
python -m compileall APV3.0test\apv3test APV3.0test\tests -q
rg -n "phase7_10_|phase7_11_|longrun|USER_A|USER_B|user_style ==|incoming_external_query ==|answer_table|student_side_llm|_most_common_reply|must_reply" APV3.0test\apv3test\runtime
```

结果:

- Phase7.10 targeted: `4 passed`
- Phase7.10-7.11 combined: `10 passed`
- Phase7.0-7.11 combined regression: `82 passed`
- Full suite: `255 passed`
- Compileall: passed
- Runtime redline scan: no matches

## 5. 最终汇总

Phase7.10 证明了:

- 极简表达底座可进行 5000 tick 长跑。
- 固定 seed phrase corpus 不被长跑测试错误淘汰。
- 支持度分布健康，未出现少数 phrase 过度垄断。
- prototype 与 cooccurrence store 均保持有界。
- 多次 SQLite warm-load 后，多轮输出序列与连续运行等价。
- 测试数据库保持在 tmp_path，不污染正式工作区。

仍不能宣称:

- 真实用户长期运行已经完成。
- 10G 级 SQLite 压测和长期遗忘策略已经完成。
- Web UI 环境中的真实输入噪声已经覆盖。

下一步 Phase7.11 已完成: 验证用户风格 mirroring，即系统能在固定词库内通过后天共现向不同用户的高频表达趋同。
