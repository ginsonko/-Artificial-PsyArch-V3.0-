# APV3.0test Phase20.9m fallback 表达种子化验收报告

日期: 2026-06-28

## 1. 设计

本阶段目标是把反馈确认里的固定表达继续收束进 AP 主流程。

原问题:

```text
教师纠正/教学后, runtime 直接使用 LEARNING_ACK_TEXT = "嗯,记下了。"
```

这会让反馈确认看起来像固定宏。按照白皮书, 先天编码可以提供初始倾向, 但表达能力应逐步由经验流、DraftGrid、奖惩和表达范式接管。因此本阶段裁定:

```text
固定确认表达不是答案表,
而是无经验时的低优先级先天表达种子.

一旦 AP 被教师纠正过"反馈确认应该怎么说",
后续同类 integrate_feedback 行动应优先从经验流与 DraftGrid 表达记忆中选择.
```

信息流保持为:

```text
teacher_feedback
  -> experience_alignment
  -> integrate_feedback action
  -> _select_request_expression(...)
  -> DraftGrid write_cell
  -> commit_reply
  -> RuntimeTickEvent trace
```

没有新增反馈确认模块、专属意图竞争器、关键词路由或答案表。

## 2. 审查完善

### 2.1 AP 哲学审查

人类儿童一开始可能只会用简单固定话回应"教会了", 例如"嗯"。但如果照料者反复教他说"好, 我记住了", 后续确认表达会被经验塑形。这个过程不是新增一个"确认模块", 而是已有行动角色在相似内在状态下召回表达经验。

因此本阶段只把已有 `integrate_feedback` 行动纳入已有表达选择路径:

```text
EXPRESSION_INTENTS =
  request_teacher
  maintain_unclosed
  integrate_feedback
```

`integrate_feedback` 不是新实体, 它本来就是已有行动竞争中的行动类型。本阶段只是允许它和 `request_teacher / maintain_unclosed` 一样, 使用同一套表达经验候选。

### 2.2 对抗性审查结论

通过审查后保留的改动:

- 反馈确认调用已有 `_select_request_expression(...)`.
- DraftGrid 写入与提交保存 `request_expression_selection` trace.
- `_expression_role_for_target_event(...)` 允许教师针对上一条 `integrate_feedback` commit 教表达.
- `_expression_role_match(...)` 只在已有行动角色相同时匹配.
- C* carryover 在当前 selected action 为 `integrate_feedback` 时, 压力优先推向 `integrate_feedback / idle_think`, 不再同时把 `request_teacher` 抬高.

拒绝的方向:

- 不新增 `_select_feedback_ack_expression`.
- 不新增"外显意图竞争"实体.
- 不按中文"记住/嗯/好"做路由.
- 不把教师反馈内容写成确认答案表.

## 3. 通过落地

修改文件:

```text
apv3test/runtime/phase20_7/runtime.py
```

新增验收:

```text
tests/test_phase20_9m_fallback_expression_seedification.py
```

关键 trace 字段:

```text
fallback_seed_formula_id = apv3_phase20_9m_fallback_expression_seedification/v1
fallback_used
learned_expression_preferred_over_seed
innate_seed_low_priority
fallback_text_hash
```

这些字段只用于审计, 不生成答案候选。

## 4. 严谨验收测试

定向验收:

```text
python -m pytest tests\test_phase20_9m_fallback_expression_seedification.py -q
结果: 2 passed
```

表达与行动竞争回归:

```text
python -m pytest \
  tests\test_phase20_8o_request_expression_from_experience_flow.py \
  tests\test_phase20_8p_expression_paradigm_slots.py \
  tests\test_phase20_8q_draftgrid_expression_fragment_composition.py \
  tests\test_phase20_8r_current_referent_expression_binding.py \
  tests\test_phase20_9b_learning_protocol_drive_modulation.py \
  tests\test_phase20_9c_learning_loop_metrics.py \
  tests\test_phase20_9j_structural_generalization_value_modulation.py \
  tests\test_phase20_9k_outward_speech_action_competition.py \
  tests\test_phase20_9m_fallback_expression_seedification.py -q
结果: 31 tests, 修复后通过
```

Phase20 分段全量验收:

```text
Phase20.1-7.4: 74 passed
Phase20.7 visual/API/release: 25 passed
Phase20.8b-8k: 33 passed
Phase20.8l-8r: 25 passed
Phase20.9a-9m + open_dialogue_foundation: 48 passed
合计: 205 passed
```

红线与治理:

```text
python scripts\red_line_check_v14.py --phase 20.7-stage8
结果: OK: All red line checks pass on runtime/cognitive

python scripts\check_constant_governance.py
结果: OK: Governance check passed (507 numeric constants)
      仍有既有 91 个 @experimental constants pending rationale

python scripts\verify_phase20_7_release_demo.py
结果: OK: Phase20.7 release demo package verified
```

小白可理解展示:

```text
1. 第一次教学:
   AP 回复: 嗯,记下了。
   trace.source_kind = innate_minimal_expression
   trace.fallback_used = True

2. 用户针对这条确认表达教学:
   教学: 好,我记住啦

3. 第二次教学:
   AP 回复: 好,我记住啦
   trace.source_kind = teacher_feedback_expression
   trace.fallback_used = False
   trace.learned_expression_preferred_over_seed = True
   trace.writes_answer_directly = False
```

## 5. 边界

本阶段可以证明:

- `integrate_feedback` 的固定确认表达已经降为低优先级先天种子.
- 教师可以后天塑形反馈确认表达.
- 学到的确认表达会通过经验流和 DraftGrid trace 参与后继输出.
- 该路径没有新增关键词路由、答案表、专属确认模块或 UI 认知旁路.

仍不能声明:

- 完整 L1/L2/L3 在线嵌入完成.
- 完整六阶段学习 runtime 完成.
- 完整范式自学习完成.
- 数学列竖式完成.
- object-centric 视觉想象完成.
- Phase21 视觉教学泛化闭环完成.

## 6. 下一步

下一步建议进入 Phase20.9n:

```text
把 integrate_feedback 的 drive 也从固定基线继续下沉到
B/C/C* 支持度 + 奖惩反馈 + 学习阶段 + 重复疲劳 + 当前整合压力.
```

本阶段已经修正了表达层的固定种子问题, 但行动竞争中 `integrate_feedback` 仍保留旧的固定高基线。这不影响本阶段验收, 但它是下一处最值得 AP-native 化的硬点。

