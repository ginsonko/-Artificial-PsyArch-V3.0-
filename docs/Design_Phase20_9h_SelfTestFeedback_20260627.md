# Phase20.9h 设计: 自测结果反向调制后继学习倾向

日期: 2026-06-27

## 1. 目标

Phase20.9g 已经让 AP 在闲时形成私有自测事件。Phase20.9h 继续推进: 自测结果不只是审计字段, 而是会被下一次闲时复盘读取, 反向调制后继学习倾向。

拟人对应:

- 自测成功: “我好像真的记住了”, teacher-off 更稳, scaffold 压力下降。
- 自测失败: “我刚才没想对”, scaffold/request 压力回升, teacher-off 降低。

## 2. AP 约束

本阶段遵守:

- 不新增数据库表。
- 不新增成绩表。
- 不新增课程状态机。
- 不把自测成功等同于完整学会。
- 不把自测失败等同于必须立刻问用户。
- 不把自测结果写入聊天框。
- 只读取 `short_structure_flow::self_test::*` occurrence。

## 3. 信息流

```text
short_structure_flow::self_test occurrence
  -> latest self_test feedback
  -> idle_learning_review_metric
  -> teacher_off / cold_retest / scaffold modulation
  -> learning_loop_carryover
  -> idle action competition
```

## 4. 数学形式

读取:

```text
G = self_test_grasp
M = match_score
E = expected_text
R = recalled_text
```

反馈分类:

```text
success if G >= 0.68 and M >= 0.70
failure otherwise
```

成功调制:

```text
teacher_off = clamp01(teacher_off + 0.12G)
cold_retest = clamp01(cold_retest * 0.82 + 0.06G)
scaffold = clamp01(scaffold * max(0.35, 1 - 0.42G))
feedback_only = clamp01(feedback_only * 0.88)
```

失败调制:

```text
mismatch = 1 - M
teacher_off = clamp01(teacher_off * 0.58)
cold_retest = clamp01(cold_retest * 0.72 + 0.10mismatch)
scaffold = clamp01(max(scaffold, 0.24 + 0.46mismatch))
feedback_only = clamp01(max(feedback_only, 0.18mismatch))
```

## 5. 对抗性审查

保留方案:

- 反馈来自自测 occurrence, 不来自外部成绩表。
- 成功/失败只调制能量倾向, 不直接写答案。
- 失败会提高 scaffold, 但不强制马上问用户。
- 成功会提高 teacher-off, 但不声明“完整学会”。

拒绝方案:

- 拒绝建立独立学习成绩表。
- 拒绝把 expected/recalled 变成答案库。
- 拒绝让 UI 判断自测成功失败。
- 拒绝自测后立刻向用户报告。

## 6. 验收标准

1. 成功自测后, 下一次 idle review 出现 `self_test_feedback`。
2. `self_test_feedback.formula_id` 为 `apv3_phase20_9h_self_test_feedback/v1`。
3. 成功自测使 teacher-off 上升或保持更稳。
4. 失败自测使 scaffold 上升, teacher-off 下降。
5. 无 self-test 时不出现 feedback packet。
6. 全 Phase20 回归、红线扫描和 release demo 通过。

