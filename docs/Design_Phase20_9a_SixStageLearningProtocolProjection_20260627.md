# Phase20.9a 设计：六阶段学习协议的 RuntimeTickEvent 投影

日期：2026-06-27

## 1. 目标

Phase20.8 已经把 B/C/C*、StatePool 回灌、SSP 短期结构流、未闭合闲时续写、主动请求教学、表达范式与当前 referent 绑定收束到同一条 AP 信息流中。Phase20.9a 的目标是在这颗认知心脏上接入“六阶段学习协议”的最小 runtime 表达。

本阶段不实现完整六阶段课程系统，也不宣称 AP 已完成六阶段学习。它只做一件事：每个非 stage0 的真实 tick，在 `RuntimeTickEvent.learning_deltas` 中追加一条 `learning_protocol_projection`，用 AP 当前 tick 的真实证据投影当前学习态。

## 2. AP 约束

1. 阶段投影只来自已有 RuntimeTickEvent 字段：感受器输出、B 候选、C_forward、C_backward、C*、action competition、teacher feedback、unclosed、DraftGrid。
2. 不新建答案表，不新增 teacher 脚本，不新增 hidden solver。
3. 投影不参与回复选择，只进入 `learning_deltas` 供审计与 UI 展示。
4. 不写 `six_stage_complete`、`online_embedding_converged`、`l1_l2_l3_complete` 这类完成性声明。
5. stage0 边界 tick 不补学习投影，避免把边界事件误当认知 tick。

## 3. 六阶段投影

本阶段采用白皮书/GL 协议中的六阶段序列：

```text
demonstrate
-> strong_scaffold
-> weak_scaffold
-> feedback_only
-> teacher_off
-> cold_retest
```

这不是外部 pipeline，而是对当前 tick 的状态投影。当前 tick 可同时拥有多个阶段分数，最终选择分数最高的 `current_protocol_stage`。

## 4. 数学形式

对每个 tick 计算以下内部信号：

```text
teacher_signal          = f(integrate_feedback, teacher_feedback_event, experience_alignment_written)
request_scaffold_signal = f(request_teacher, maintain_unclosed, corresponding action drive)
receptor_signal         = f(external_inputs, receptor_outputs)
b_support               = max(B support, weak tick evidence support)
structural_signal       = 1 if structural_b active else 0
exact_signal            = 1 if exact_b0 active else 0
cstar_grasp             = C*.grasp
candidate_count         = C*.unified_candidate_statistics.candidate_count
teacher_off_signal      = 1 if teacher absent and B active and not requesting teacher else 0
```

阶段分数：

```text
score(demonstrate)
  = sensory_action * 0.50
  + receptor_signal * 0.32
  + has_c_forward * 0.10

score(strong_scaffold)
  = teacher_signal * 0.70
  + integrate_feedback * 0.18

score(weak_scaffold)
  = request_scaffold_signal * 0.56
  + weak_memory_signal * 0.28
  + structural_signal * 0.20

score(feedback_only)
  = teacher_signal * 0.38
  + feedback_only_hint * 0.22

score(teacher_off)
  = teacher_off_signal
  * (0.46 + b_support * 0.34 + cstar_grasp * 0.14 + exact_signal * 0.06)

score(cold_retest)
  = teacher_off_signal * cold_retest_hint * (0.44 + b_support * 0.34)
```

输出：

```text
learning_delta = {
  delta_kind: learning_protocol_projection,
  formula_id,
  protocol_phases,
  current_protocol_stage,
  stage_index,
  stage_support,
  stage_scores,
  evidence,
  projection_only: true,
  creates_reply_candidate: false,
  writes_answer_directly: false
}
```

## 5. 与人类过程的对应

人类学习并不是每次都处在同一个阶段。看见新东西是观察/示范；不会时会请求强脚手架；有一点相似经验但不确定时属于弱脚手架；老师只给反馈时是反馈期；能脱离老师回忆和行动时是 teacher-off；隔一段时间重新做对才接近 cold retest。

Phase20.9a 对应的是“让 AP 知道自己此刻像处在学习过程的哪个位置”。它不让 AP 直接变聪明，但让后续调参、教师退场、范式自学习、在线嵌入更新有共同的审计坐标。

## 6. 对抗性审查

保留方案：

- 把投影放在 `complete_every_tick_cognitive_cycle`，因为它已经是每 tick B/C/C* 补齐层。
- 只追加 `learning_deltas`，不改变回复行为。
- 阶段按分数竞争，不用用户输入关键词。
- 所有阶段证据写入 `evidence`，便于 UI 和报告核对。

拒绝方案：

- 不新增 `learning_stage` 数据库表。
- 不把六阶段写成外部课程状态机。
- 不把 teacher-off 写成全局成熟结论。
- 不用 `six_stage_complete` 等完成性字段。

## 7. 验收标准

1. 未知输入触发 `request_teacher` 时，投影到 `weak_scaffold`。
2. 教师反馈整合 tick 投影到 `strong_scaffold`。
3. 无当前教师的 exact B0 召回 tick 投影到 `teacher_off`。
4. 视觉感受器观察 tick 投影到 `demonstrate`。
5. stage0 不出现学习协议投影。
6. 旧的 20.8 链路、20.7+20.8 总链、红线扫描继续通过。

