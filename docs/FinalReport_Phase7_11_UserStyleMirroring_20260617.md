# APV3 Phase7.11 User Style Mirroring 最终报告

日期: 2026-06-17
阶段: Phase7.11
状态: 通过

## 1. 设计

Phase7.11 验证用户强调的目标: 系统能否通过后天观察，而不是教学协议或 LLM policy，逐渐接近正在和它交流的用户的表达方式。

本阶段不允许 runtime 创建新 phrase。所谓“靠近用户风格”，限定为:

- 用户高频使用的表达必须在 seed corpus 内。
- 系统通过 `observe_existing_phrase_cooccurrence()` 把这些表达与当前 feeling 建立共现。
- 长期后，同一 feeling 的 top-K phrase 集合向该用户常用短语偏移。
- 不同用户训练后，同一 feeling 的输出集合明显不同。

这是一种安全的 mirroring: 不扩词、不造句、不倒灌，只在固定词库内重新分配支持度和共现权重。

## 2. 审查完善

验收设计了两个模拟用户:

- 用户 A 高频使用: `嗯 / 哦 / 试试`
- 用户 B 高频使用: `好 / 可以 / 再说一次`

两者训练的是同一个结构态 `UNCERTAIN_VIEWS`，因此如果训练后 top-3 不同，说明差异来自后天共现，而不是不同 feeling 或不同 route。

红线:

- 词库外长表达 `我 完整 解释 一下` 不进入 phrase memory。
- commit_text 必须 100% 来自 seed corpus。
- runtime 不出现 `USER_A/USER_B/user_style ==` 等用户特例分支。

## 3. 通过落地

新增:

- `tests/test_phase7_11_user_style_mirroring.py`
- `docs/FinalReport_Phase7_11_UserStyleMirroring_20260617.md`
- `reports/APV3_Phase7_11_UserStyleMirroring_Showcase_20260617.html`

实际 trace:

```text
phase7_11_user_a_top3 ['哦', '嗯', '试试'] teacher_off 哦
phase7_11_user_b_top3 ['可以', '好', '再说一次'] teacher_off 可以
phase7_11_jaccard 0.0
```

## 4. 严谨验收测试

已执行:

```text
python -m pytest APV3.0test\tests\test_phase7_11_user_style_mirroring.py -q
python -m pytest APV3.0test\tests\test_phase7_10_longrun_stability.py APV3.0test\tests\test_phase7_11_user_style_mirroring.py -q
python -m pytest APV3.0test\tests\test_phase7_0_teacher_off_three_stage_milestone.py ... APV3.0test\tests\test_phase7_11_user_style_mirroring.py -q
python -m pytest APV3.0test\tests -q
python -m compileall APV3.0test\apv3test APV3.0test\tests -q
rg -n "phase7_10_|phase7_11_|longrun|USER_A|USER_B|user_style ==|incoming_external_query ==|answer_table|student_side_llm|_most_common_reply|must_reply" APV3.0test\apv3test\runtime
```

结果:

- Phase7.11 targeted: `6 passed`
- Phase7.10-7.11 combined: `10 passed`
- Phase7.0-7.11 combined regression: `82 passed`
- Full suite: `255 passed`
- Compileall: passed
- Runtime redline scan: no matches

## 5. 最终汇总

Phase7.11 证明了:

- 同一 feeling 下，不同用户的高频表达能把系统带向不同 top-3 phrase 集合。
- 用户 A/B 的 top-3 集合 Jaccard 为 `0.0`，差异明确。
- teacher-off 输出也随用户风格不同而不同。
- 词库外长句不会进入 phrase memory。
- 所有输出仍来自 seed corpus，风格红线保持有效。

仍不能宣称:

- 系统已经能学会任意用户创造的新短语。
- 词库外表达扩展机制已经上线。
- 真实用户长程 Web UI mirroring 已经完成。

下一步建议:

- Phase7.12: context 条件化表达，同一 feeling 在不同 context/关系状态下召回不同 phrase。
- 或进入 Phase8.0 工程化预备: 清理测试探针、定义干净 runtime profile、准备最小本地体验入口。
