# APV3 Phase20.8/20.9 连续闲时运行设计备案

日期: 2026-06-26

## 1. 目标

Phase20.7 已经把开放对话底座的 turn 级闭环接到 RuntimeTickEvent。下一步若要让用户感到“它一直活着”, 需要把闲时 tick 从手动按钮升级为可控的连续运行器。

目标不是做 UI 定时器日志, 而是让无外部输入时仍然由 AP-native runtime 产生真实 tick:

1. 用户不输入时, AP 可以被未闭合感拉回, 继续思考尚未弄懂的内容。
2. 用户输入到来时, 最新外部输入插入下一 tick, 并唤醒较高频率运行。
3. 无事可想时, AP 进入低频待机或休眠, 避免 CPU 空转。
4. 主动说话必须经过行动竞争, 不能由 UI 或固定模板直接触发。
5. 所有闲时观察、闲时思考、主动询问、主动回复都必须写入 RuntimeTickEvent 和统一经验流。

## 2. Phase20.7 工作台预览

当前工作台中的“连续闲时”只是可视化预览:

1. 前端每秒调用一次 `/api/phase20_7/turn` 的空输入路径。
2. 若多次返回 `idle_observe`, 前端退避到 2.5 秒和 5 秒。
3. 它只用于体验和验收 idle_think trace, 不代表最终后台常驻调度器。
4. 它不会复用输入框中的图片/音频路径, 防止无输入时反复重新处理同一媒体。

## 3. 正式连续 runtime 边界

正式版本应新增 AP-native scheduler, 但 scheduler 只负责节奏和预算, 不负责认知内容:

```text
外部输入队列
  -> RuntimeTickScheduler
  -> run_ap_tick(context)
  -> RuntimeTickEvent
  -> ExperienceLog / StatePool / SSP
  -> UI 订阅最新 tick
```

Scheduler 可以决定 tick 频率, 但不能决定回答内容、视觉识别、教学结果或主动话题。

## 4. 节奏模型

建议默认参数:

```text
active_rate = 1 tick/s
thinking_rate = 0.5 tick/s
standby_rate = 0.2 tick/s
sleep_rate = 0.03 tick/s
idle_quiet_to_standby = 5 ticks
standby_quiet_to_sleep = 60 ticks
wake_on_external_input = true
```

状态转移:

1. 外部输入到来: `sleep/standby/thinking -> active`
2. 未闭合感 U 高: `standby -> thinking`
3. 连续无高 U、无新奇、无行动获胜: `thinking -> standby -> sleep`
4. 主动输出获胜: 保持 `active` 一个短窗口, 然后按是否仍有 U 回落。

## 5. 主动输出门

主动说话不能因为“时间到了”发生, 必须由行动竞争获胜:

```text
drive_proactive_speak =
  sigmoid(
    w_u * U_relevant
  + w_n * novelty
  + w_teacher * ask_need
  + w_social * innate_social_bias
  - w_fatigue * ask_fatigue
  - w_interrupt * user_busy_risk
  )
```

其中 `innate_social_bias` 是先天规则倾向, 不是独立的“社交期待实体”。它只能调制行动竞争, 不能跳过 B/C/C*。

## 6. 闲时内容来源

闲时不能硬编码哲学问题或梦想列表。可被想起的对象必须来自:

1. 未闭合项 U。
2. 近期短期结构池中的高能对象。
3. 长期经验流中被 B/C/C* 召回的相似结构。
4. 先天规则导致的探索倾向。

哲学问题、梦想、理想、困惑等拟人内容, 应当是用户长期输入和 AP 自身经验流积累后的结果, 而不是默认话题表。

## 7. UI 展示要求

1. 每秒刷新最新 tick、内心画面、想法云、曲线和草稿格。
2. 页面不随对话增长而变长; 对话区、回放区、记忆区各自滚动。
3. 每个 tick 必须能解释:
   - 看到/听到/读到什么。
   - 状态池里什么变强。
   - B/C/C* 召回或预测了什么。
   - 行动竞争里哪些动作参与竞争。
   - 为什么选中当前动作。
4. UI 只翻译 RuntimeTickEvent, 不补编 AP 没有产生的心理活动。

## 8. Phase20.8 优先级

连续运行可以带来惊艳感, 但下一阶段的核心仍然应是视觉教学闭环:

1. 视觉 patch/空间结构/clarity 与文本教学绑定。
2. 解决苹果/香蕉互相覆盖问题。
3. 让图片再认依赖视觉差异, 而不是最近教学文本。
4. 再把连续 runtime 接进视觉学习验收, 展示 AP 会继续观察、移动视焦点和积累内心画面。

因此建议顺序:

```text
Phase20.8a: 视觉教学闭环
Phase20.8b: 视觉泛化与画板/教师辅助视焦点
Phase20.9: 后台连续 runtime + 主动输出门
```

## 9. 验收

1. 连续运行 60 秒, 所有 tick 都有 RuntimeTickEvent。
2. 无未闭合项时频率自动降到低频。
3. 新用户输入后 1 秒内恢复 active。
4. AP 主动说话必须能在 action_competition 中看到获胜原因。
5. UI 展示的内心画面、想法云、曲线都能追溯到同一 tick。
6. 红线扫描不得出现 UI-only 心理日志、固定主动话题表或整图识别捷径。
