# Phase20.9c 设计：feedback-only / teacher-off / cold-retest 学习闭环指标

日期：2026-06-27

## 1. 目标

Phase20.9a 让每个真实 tick 有“六阶段学习协议投影”。Phase20.9b 让这份投影开始调制 `request_teacher / maintain_unclosed / teacher-off` 的行动竞争。

Phase20.9c 继续推进一步：不改变回复、不新增课程状态机，而是在每个真实 tick 的 `learning_deltas` 中追加一条 `learning_loop_metrics`，让 AP 能审计当前学习闭环的四个倾向：

1. `feedback_only_readiness`：当前更像“只需要反馈，不需要重新示范”；
2. `teacher_off_readiness`：当前更像“可以短暂脱离教师，靠自身经验回忆/行动”；
3. `cold_retest_readiness`：当前更像“教师缺席、时间拉开、仍有记忆可验证”的冷重测压力；
4. `scaffold_regression_need`：当前更像“把握不足，应回到弱/强脚手架”。

这些不是外部课程脚本，也不是完成性声明。它们只是把白皮书里的把握感、未闭合感、B/C/C*、行动竞争、反馈整合、教师退场这些已有 AP 信号，整理成可审计的闭环指标。

## 2. AP 约束

本阶段遵守：

- 不新增数据库表，不保存独立课程状态。
- 不根据用户文字关键词判断阶段。
- 不生成答案，不改写回复，不制造 B 候选。
- 不把 `teacher_off_readiness` 解释成能力成熟，只表示当前 tick 的教师退场倾向。
- 不把 `cold_retest_readiness` 解释成冷重测完成，只表示当前 tick 有冷重测压力。
- 所有指标都必须能追溯到当前 `RuntimeTickEvent` 的真实字段。

## 3. 信息流位置

Phase20.9c 位于 `complete_every_tick_cognitive_cycle(...)` 的末尾：

```text
RuntimeTickEvent
  -> B/C/C* 补齐
  -> C* 最小误差整合
  -> learning_protocol_projection
  -> learning_loop_metrics
```

它只追加 `learning_deltas`，不影响 action selection，不参与 DraftGrid，不写回复文本。

## 4. 数学形式

核心输入：

```text
teacher_signal          = 当前 tick 是否正在整合教师反馈
request_signal          = request_teacher / maintain_unclosed 的脚手架信号
b_support               = B 候选或 tick evidence B 的支持度
exact_signal            = exact B0 是否存在
structural_signal       = structural B 是否存在
cstar_grasp             = C* 最小误差整合后的把握感
conflict_entropy        = 行动竞争冲突熵
feedback_hint           = 是否存在 recovered target / backward attribution
cold_hint               = 教师缺席且时间拉开的冷重测弱提示
has_memory              = 是否有 B 候选、结构候选或统一候选证据
```

反馈期指标：

```text
feedback_only_readiness
  = teacher_signal * 0.26
  + feedback_hint * 0.34
  + cstar_grasp * 0.16
  + (1 - conflict_entropy) * 0.10
  + written_experience_ratio * 0.14
```

若没有教师信号，该指标乘以 `0.35`，防止无教师时误判为 feedback-only。

教师退场指标：

```text
teacher_off_readiness
  = b_support * 0.38
  + cstar_grasp * 0.24
  + exact_signal * 0.18
  + structural_signal * 0.08
  + (1 - request_signal) * 0.07
  + (1 - conflict_entropy) * 0.05
```

该指标只在 `teacher_signal == 0` 且存在记忆证据，且当前动作不是 `request_teacher / maintain_unclosed` 时计算。

冷重测指标：

```text
cold_retest_readiness
  = teacher_off_readiness * 0.72
  + cold_hint * 0.28
```

该指标只表示“像冷重测”，不表示冷重测已经通过。

回退脚手架指标：

```text
scaffold_regression_need
  = (1 - b_support) * 0.24
  + (1 - cstar_grasp) * 0.28
  + request_signal * 0.24
  + conflict_entropy * 0.12
  + request_action_bonus * 0.12
```

若当前正在整合教师反馈，则乘以 `0.45`；若 `teacher_off_readiness >= 0.62`，则乘以 `0.55`。

最终输出：

```text
learning_delta = {
  delta_kind: learning_loop_metrics,
  formula_id,
  current_protocol_stage,
  feedback_only_readiness,
  teacher_off_readiness,
  cold_retest_readiness,
  scaffold_regression_need,
  dominant_learning_tendency,
  tendencies,
  evidence,
  projection_only: true,
  creates_reply_candidate: false,
  writes_answer_directly: false
}
```

## 5. 与人类过程的对应

小孩第一次不会时，会问，也会更依赖脚手架；这对应 `scaffold_regression_need` 高。

老师正在纠正时，小孩会先听和整合，而不是立刻继续问；这对应 `feedback_only_readiness` 上升。

已经能靠记忆回答时，小孩会少问老师；这对应 `teacher_off_readiness` 上升。

隔一段时间后，老师不提示，小孩还能不能想起来，会形成“冷重测”的压力；这对应 `cold_retest_readiness` 上升。

## 6. 对抗性审查

保留方案：

- 把指标放在 `learning_deltas`，因为它是学习审计层，不是回复层。
- 指标只从当前 tick 的 AP 字段计算，保持所有信息可追溯。
- 用连续分数表达倾向，避免把学习过程硬切成外部阶段。
- 保留 `dominant_learning_tendency` 只作为审计摘要，不作为行动脚本。

拒绝方案：

- 拒绝新建课程状态机或阶段表。
- 拒绝用关键词判断“用户在测试我 / 用户在纠正我”。
- 拒绝把 cold-retest 做成定时任务；当前只记录压力，后续再让 AP 主流程调度。
- 拒绝把 teacher-off readiness 等同于已学会。

## 7. 验收标准

1. 第一次未知输入的主导倾向为 `return_to_scaffold`。
2. 教师反馈整合 tick 的 `feedback_only_readiness` 明显升高。
3. exact B0 召回 tick 的 `teacher_off_readiness` 明显升高。
4. 后期教师缺席且有记忆证据的 tick 出现 `cold_retest_readiness`。
5. 所有指标都写明 `creates_reply_candidate=False`、`writes_answer_directly=False`。
6. Phase20.7+20.8+20.9 全链路测试通过。
7. 红线扫描无命中，release demo 验证通过。

