# Phase20.9b 设计：学习协议对请教驱动力的 AP-native 调制

日期：2026-06-27

## 1. 目标

Phase20.9a 已经把“六阶段学习协议”投影到每个真实 `RuntimeTickEvent`：AP 可以在审计层看到当前 tick 更像示范、强脚手架、弱脚手架、反馈期、教师退场，还是冷重测。

Phase20.9b 的目标是让这份学习状态开始影响 AP 的行动竞争，重点只做三件事：

1. 未知且低把握时，允许 `request_teacher` 继续升高；
2. 同一个未闭合对象反复问不到答案时，让请教驱动力自然降温，避免机械刷屏；
3. 已经能 exact/structural recall 或正在整合教师反馈时，让请教动作退后，把能量交给回忆、整合、继续思考。

这不是外部课程表，也不是新增教学脚本。它只是把白皮书中“学习阶段、未闭合感、把握感、行动竞争、教师退场”的同一套信号，投到 `request_teacher / maintain_unclosed` 的驱动力上。

## 2. AP 约束

本阶段必须遵守：

- 不新增答案表、教学表、标签表或课程状态机。
- 不用用户输入关键词、正则、整句匹配来决定是否请教。
- 不写回复文本，不制造 B 候选，不绕过 DraftGrid。
- 不把 `six_stage_complete`、`online_embedding_converged`、`l1_l2_l3_complete` 这类完成性结论写进 runtime。
- 调制必须来自已有 AP 主流程信号：B/C/C* 支持度、未闭合尝试次数、近期 action competition、教师反馈事件、当前 intent。

## 3. 信息流位置

Phase20.9b 有两个入口：

1. `_teacher_request_drive_context(...)`

   这里原本已经根据低把握、未闭合感、当前观察和 B 支持度计算 `request_drive` 与 `maintain_drive`。20.9b 在该结果后叠加学习协议调制，并把审计字段写入 `teacher_request_drive_context.learning_protocol_drive_modulation`。

2. `_competition(...)`

   当当前 tick 已经出现 `exact_b0`、`structural_bccstar` 或 `integrate_feedback` 时，请教不是当前最合理的主动作。20.9b 会在 action competition 行上降低 `request_teacher / maintain_unclosed` 的竞争强度，但不删除它们，让后续 tick 仍可根据真实状态重新竞争。

## 4. 数学形式

基础项来自 Phase20.8n：

```text
base_request_drive  = f(low_grasp, unclosed_pull, observation, b_support)
base_maintain_drive = f(existing_unclosed, unclosed_pull, low_grasp)
```

Phase20.9b 只做乘性调制：

```text
recent_request_count  = count(selected_action in {request_teacher, maintain_unclosed}, last 24 ticks)
recent_feedback_count = count(event_kind == teacher_feedback_event, last 24 ticks)
attempt_count         = existing_unclosed.attempt_count

request_frequency_cooldown
  = min(0.34, recent_request_count * 0.035 + attempt_count * 0.075)

teacher_fade_pressure
  = min(0.28, unit(b_support) * 0.22 + recent_feedback_count * 0.025)

feedback_wait
  = min(0.12, max(0, recent_request_count - recent_feedback_count) * 0.025)
```

当 intent 是 `maintain_unclosed`：

```text
request_multiplier
  = max(0.42, 1 - request_frequency_cooldown - teacher_fade_pressure - feedback_wait)

maintain_multiplier
  = max(0.60, 1 - request_frequency_cooldown * 0.45 - feedback_wait * 0.35)
```

当 intent 是 `request_teacher`：

```text
request_multiplier
  = max(0.50, 1 - request_frequency_cooldown * 0.80 - teacher_fade_pressure)

maintain_multiplier
  = max(0.68, 1 - request_frequency_cooldown * 0.30)
```

输出：

```text
request_drive_after  = unit(base_request_drive  * request_multiplier)
maintain_drive_after = unit(base_maintain_drive * maintain_multiplier + unclosed_pull * 0.02)
```

action competition 层的教师退场调制：

```text
if intent == exact_b0:
  request_teacher *= 0.42
  maintain_unclosed *= 0.70

if intent == structural_bccstar:
  request_teacher *= 0.56
  maintain_unclosed *= 0.82

if intent == integrate_feedback:
  request_teacher *= 0.38
  maintain_unclosed *= 0.72
```

这些系数不是完成性证明，只是当前工程的可审计默认值。后续自适应调参器可以根据“问得太多 / 问得太少 / 反馈整合是否成功”继续微调。

## 5. 与人类过程的对应

人类小孩第一次遇到不会的东西，会很自然地问：“这是什么？”这对应低把握、未闭合感和 `request_teacher` 的上升。

如果同一个问题问了几次没人回答，小孩通常不会每秒重复同一句，而会先继续看、换个角度想、过一会儿再问。这对应 `request_frequency_cooldown`。

如果刚刚已经学会了“这是苹果”，再看到同一个苹果时，小孩更倾向于直接说“苹果”，而不是继续问“这是什么”。这对应 exact B0 或 structural B/C/C* 激活时的教师退场压力。

如果老师正在纠正，小孩会把注意力放在“听懂和记住老师说的内容”上，而不是同时又发起新的问题。这对应 `integrate_feedback` 时压低新请教。

## 6. 小白例子

### 例子一：第一次不会

用户：这是什么？

AP 没有相似经验，低把握高，未闭合感高。此时 `recent_request_count=0`、`attempt_count=0`，调制不会冷却请教，所以 AP 会更容易选择“请教我 / 我还不确定”。

### 例子二：重复问不到答案

用户没有教，AP 又连续几次想到同一个未闭合对象。

这时 `recent_request_count` 和 `attempt_count` 上升，AP 不会一直把聊天框刷满“请教我”，而是降低请教驱动，把更多 tick 留给观察、回忆、闲时续写。

### 例子三：已经会了

用户教过：

```text
这是什么？ + 苹果图像 -> 是苹果
```

后来再次输入相似图像时，exact/structural B 支持度上升。AP 的 `request_teacher` 竞争行会被压低，回复或行动更倾向于从已学经验中长出来。

## 7. 对抗性审查

保留方案：

- 调制放在已有 `request_teacher` 驱动力和 action competition 上，因为这正是 AP 做行动选择的位置。
- 只使用近期 tick 的真实事件、B 支持度、未闭合尝试和反馈事件，不增加外部课程对象。
- 所有调制都写审计字段，UI 与测试可以看到“为什么少问了 / 为什么退场了”。
- 调制只改变能量竞争，不改变答案来源。

拒绝方案：

- 拒绝按输入文字写“如果用户说这是什么就请教”的关键词规则。
- 拒绝新增 `learning_stage` 数据库表，把六阶段变成外部状态机。
- 拒绝把 exact recall 直接等同于“已经学会”，这里只表示当前 tick 有较高把握。
- 拒绝为了演示效果直接生成固定请教话术；表达仍必须走 20.8o/p/q/r 已经接入的经验片段与 DraftGrid。

## 8. 验收标准

1. 第一次未知输入保留请教驱动力，不被冷却。
2. 重复未闭合且没有得到反馈时，请教 / 维持未闭合驱动力下降。
3. exact B0 召回时，`request_teacher` competition 行被教师退场压力压低。
4. feedback integration tick 中，`request_teacher` 被压低，避免一边整合一边继续问。
5. 审计字段明确 `creates_reply_candidate=False`、`writes_answer_directly=False`。
6. Phase20.7+20.8+20.9 全链路测试通过。
7. 红线扫描无命中，release demo 验证通过。

