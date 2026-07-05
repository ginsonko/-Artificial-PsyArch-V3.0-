# Phase20.9j 最终报告: 结构泛化价值调制与闲时输入抢占

日期: 2026-06-28

## 完成内容

1. 低把握结构泛化接入 AP 主流程。
   - `_structural_similarity(...)` 增加后缀、最长连续片段、最长子序列对齐。
   - `_find_structural_b(...)` 保留 unified experience candidate 路径, 不新增答案表。
   - structural B 支持度接入历史 `reward/punish`。
   - 对共享片段少、残差多的候选加入 `residual_conflict_penalty`, 防止公共前缀误泛化。

2. 工作台连续闲时输入 bug 修复。
   - 新增 `pendingUserTurn`。
   - 用户在 idle 请求进行中发送输入时, 暂停连续闲时并排队用户 turn。
   - idle 空请求不排队。

3. 审计字段增强。
   - `structural_query_coverage`
   - `structural_residual_ratio`
   - `value_reward_boost`
   - `value_punish_penalty`
   - `low_grasp_generalization_uncertainty`
   - `structural_generalization_value_modulation`

## 效果示例

教学:

```text
用户: 没错,你好聪明
教学: 谢谢
```

下一次 teacher-off:

```text
用户: 你好聪明
AP: 谢谢
```

tick 审计中可见:

```text
B = structural_b
structural_sequence_fit = 0.9057
structural_query_coverage = 1.0
value_reward_boost > 0
residual_conflict_penalty = 0
writes_answer_directly = false
```

反例:

```text
用户: 你是谁
AP: 我还不太知道怎么说。
```

公共前缀反例:

```text
教学: phase20o knowledge question -> red apple
用户: phase20o unrelated unknown
AP: 我还不太知道怎么说。
```

该反例证明 AP 不会只因共享 `phase20o` 片段就把知识回复串过去。

惩罚版:

```text
教学: 没错,你好聪明 -> 谢谢, punish=1.0
用户: 你好聪明
AP: 我还不太知道怎么说。
```

## 验收命令

已通过:

```powershell
python -m pytest tests\test_phase20_9j_structural_generalization_value_modulation.py tests\test_phase20_9j_workbench_idle_input_preemption.py -q
node --check apv3test\web\static\phase20_7_workbench.js
python -m pytest tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_9h_self_test_feedback.py tests\test_phase20_9i_workbench_learning_lifecycle.py -q
$tests = @(rg --files tests | rg "test_phase20_(7|8|9)"); python -m pytest @tests -q
python scripts\red_line_check_v14.py --phase 20.7-stage8
python scripts\check_constant_governance.py
python scripts\verify_phase20_7_release_demo.py
```

## 边界

本阶段可以证明:

- 子序列/片段级结构泛化已经能进入 structural B。
- reward/punish 已能调制低把握泛化是否被采用。
- 连续闲时不会再直接吞掉用户发送的真实输入。

仍不能声明:

- 完整六阶段学习 runtime 完成。
- L1/L2/L3 在线嵌入完成。
- 完整范式自学习完成。
- 主动外显发言已经 AP-native 完成。
- 数学列竖式完成。
- object-centric 视觉想象完成。

下一步建议:

Phase20.9k 应把“主动给用户发消息”做成 AP action competition 中的 `outward_speech` 候选, 由 idle private thought、未闭合感、C* 预测、奖惩期望、重复疲劳和无反馈惩罚共同决定, 不能使用定时模板或固定寒暄。
