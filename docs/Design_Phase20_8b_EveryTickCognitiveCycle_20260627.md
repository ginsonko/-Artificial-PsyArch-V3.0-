# Phase20.8b 每 tick 通用 B/C/C* 认知循环设计

日期: 2026-06-27

## 1. 设计目标

Phase20.8a 已经证明文本 occurrence 可以通过经验流召回视觉 patch 并重建内心画面, 但当前实现仍存在一个结构性问题: 视觉、听觉、文本、闲时思考分别在各自 helper 中手写 `c_forward` / `c_backward` / `cstar_packet`。这会让 AP 主流程看起来像多个局部模块拼起来, 而不是同一个每 tick 能量闭环。

Phase20.8b 的目标是引入一个统一的每 tick 认知循环补齐器:

```text
RuntimeTickEvent(raw)
  -> extract current evidence
  -> build B candidates summary
  -> build C_forward prediction
  -> build C_backward attribution
  -> build C* min-error packet
  -> RuntimeTickEvent(completed)
```

该补齐器只读取当前 tick 已经真实形成的证据, 包括:

- receptor_outputs
- state_pool_top
- ssp_active_summary
- selected_action
- action_competition
- experience_event_ids_written
- existing b_candidates / c_forward / c_backward
- visual_inner_picture / audio_inner_sketch
- draft_grid / unclosed_items / feelings

它不读取原始图片、不读取文件名、不读取答案表、不改 reply_text、不决定输出内容。

## 2. AP 哲学约束

1. 每个认知 tick 都有预测和归因, 但不是每个 tick 都必须高把握。
2. B/C/C* 是对当前状态池和短期结构流的白箱审计, 不是另一个回答模块。
3. 若某个 tick 已经有模态专属 C_forward / C_backward, 通用循环只补齐缺失字段, 不覆盖局部真实证据。
4. Stage0 boundary tick 是 schema/边界验收, 不是认知 tick, 可保留 `no_write_reason`。
5. 允许主观、低把握、可能错误的归因; 不追求机器式绝对正确。
6. 所有模态一等: 文本、视觉、听觉、行动、草稿、闲时思考都通过同一个 event 结构被解释。

## 3. 数学形式

对每个 tick \(t\), 设已形成的证据集合为:

\[
E_t = R_t \cup S_t \cup A_t \cup D_t \cup M_t
\]

其中:

- \(R_t\): receptor outputs
- \(S_t\): state pool top items
- \(A_t\): selected action and action competition
- \(D_t\): draft grid / action write evidence
- \(M_t\): memory recall, visual inner picture, audio inner sketch, unclosed pressure

### 3.1 B 候选摘要

如果 tick 已有 B 候选, 保留。否则从当前 tick 证据构造弱 B:

\[
B_t = \operatorname{top}_k(\text{evidence sources by support})
\]

support 来源:

- selected action drive
- state pool top energy
- receptor clarity / inner energy
- existing recall support

弱 B 不生成答案, 只说明“当前 tick 主要由什么经验/感受支撑”。

### 3.2 C_forward

若已有 C_forward, 保留; 否则按 action family 形成最小预测:

\[
C^+_t = f(B_t, A_t, S_t)
\]

例:

- `move_focus` -> 预测继续采样会提高 clarity。
- `visual_imagination_recall` -> 预测回忆 patch 会继续牵引内心画面。
- `write_cell` -> 预测草稿长度增加并可能进入 commit。
- `idle_think` -> 预测短期结构流继续叙事化发展。
- `audio_audit_sensor` -> 预测可形成内心音频 trace。

### 3.3 C_backward

若已有 C_backward, 保留; 否则构造低把握主观归因:

\[
C^-_t = g(E_t, B_t)
\]

归因槽包括:

- receptor source
- selected action
- strongest state item
- experience event ids
- unclosed item
- visual/auditory inner source

归因误差:

\[
e^-_t = 1 - \operatorname{cause\_grasp}_t
\]

该归因可错, 后续教师反馈与经验反例再修正。

### 3.4 C* 最小误差包

每 tick 形成:

\[
C^*_t = \arg\min (E^+_t + E^-_t + E^{conflict}_t)
\]

工程上先记录可审计字段:

- `prediction_count`
- `attribution_count`
- `b_candidate_count`
- `grasp`
- `e_forward`
- `e_backward`
- `conflict_entropy`
- `completed_by`

它不替 AP 做答案, 只把当 tick 的预测/归因闭环明确写进 RuntimeTickEvent。

## 4. 落地方式

新增文件:

- `apv3test/runtime/phase20_7/cognitive_cycle.py`

新增函数:

- `complete_every_tick_cognitive_cycle(event)`
- `complete_turn_cognitive_cycle(result)`

接入点:

- `run_phase20_7_turn(...)` 返回 Stage1-Stage6 结果前统一调用。
- Stage0 不调用, 因为它不是认知 tick。

## 5. 验收标准

1. Stage1-Stage6 每个 tick 都有 `cstar_packet.kind = every_tick_min_error_cycle` 或更具体的已有 C*。
2. 每个认知 tick 都至少有一个 C_forward 与一个 C_backward。
3. 视觉、听觉、文本、闲时、草稿、TTS tick 都能通过同一字段看见预测/归因。
4. 不改变 reply_text 和教学结果。
5. 红线扫描无标签表、直接答案、原始视觉资产渲染路径。

## 6. 自审结论

该设计符合 AP 白皮书方向, 因为它将“每 tick 都有预测和归因”落实为通用事件层闭环, 且不新增答案模块。当前版本仍是最小数学硬化: 它先统一事件结构和审计字段, 后续需要把 B/C 的候选来源进一步接入真正的 StatePool/SSP/ExperienceFlow 结构对齐与在线嵌入。
