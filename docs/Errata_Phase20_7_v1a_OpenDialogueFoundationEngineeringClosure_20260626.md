# Phase20.7 v1a 工程闭合 Errata 与自审报告

日期: 2026-06-26  
对象: `Design_APV3_Phase20_7_OpenDialogueFoundation_EngineeringMath_v1_20260626.md`  
状态: v1a 已吸收, 可作为 Stage 0 开工前设计基线。  

---

## 1. 本轮补足内容

本轮不是修改 AP 哲学, 而是把白皮书落地到更难误解的工程规格。

### E1 Stage 依赖闭合

问题: v1 中 Stage 1 要验收“教学不串场”, 但统一经验流和 B/C/C* 在后续 Stage 才出现, 容易诱发 teaching shortcut。

修订:

1. Stage 1 改为 `StatePool + SSP + 最小 EventLog + DraftGrid 文本闭环`。
2. Stage 1 引入 exact structural B0 召回, 只处理 exact/near-exact 结构匹配。
3. Stage 2 扩展完整经验流和索引, 不再是第一次写记忆。
4. Stage 3 扩展相似结构 B/C/C*, 不作为 Stage 1 的隐藏依赖。

### E2 未闭合感 AP-native 化

问题: `task_pressure`、`curiosity_from_explanation_gap` 等词容易被实现成新实体。

修订:

1. U 来源拆为 reward/punish 预测不满足、先天规则投影、C* 预测不验、行动被打断。
2. U 必须引用 `source_event_id`、`prediction_slot_id`、`action_trace_id` 或 `innate_rule_id`。
3. 放弃/解除必须有 cancellation、impossibility、cost revaluation、source removal、teacher release 等来源。

### E3 source_trust 局部化

问题: v1 的 source_trust 容易成为全局教师权威。

修订:

1. source_trust 改为 `source x context x modality`。
2. 只有当前 source 参与事件时才更新。
3. trust 只调制学习、召回权重和来源透明度, 不直接给答案。

### E4 SQLite provenance 与记忆包卸载

问题: 仅靠 `payload_json` 不足以支撑回放、导入去重、精准卸载。

修订新增:

1. `phase20_7_source_packets`
2. `phase20_7_action_records`
3. `phase20_7_import_batches`
4. `phase20_7_package_memberships`
5. `phase20_7_derived_runtime_snapshots`

卸载规则: 只删除该 import_batch 新增且无共享引用的对象, dedup/共享对象保留。

### E5 RuntimeTickEvent v2 审计链

问题: 有 trace 不等于可审计。

修订新增:

1. `experience_event_ids_written`
2. `source_refs`
3. `action_record_ids`
4. `rejected_candidates`
5. `index_query_trace`
6. `package_delta_refs`

### E6 视觉焦点行动化

问题: focus_policy 容易写成固定扫描。

修订:

1. focus 必须由 action competition 的 `move_focus / maintain_focus / widen_focus` 给出。
2. `p_sample` 显式 `clamp01`。
3. 固定扫描只能是低优先级探索候选。
4. teacher focus 只提升 saliency, 不绑定 label。

### E7 六阶段学习协议与 SDPL 映射

问题: GL/teacher-off 若后补, 容易和 runtime 脱节。

修订:

1. 学习事件可携带 `LearningProtocolTrace`。
2. 包含 learning_stage、sdpl_packet_key、epistemic_source、teacher_off_status、leakage_guard。
3. SDPL 只做来源与证据分化, 不提供答案。

### E8 完整发布 demo

问题: v1 的“最小惊艳 demo”不符合最终发布目标。

修订:

1. Section 16 改为“完整可发布 demo”。
2. 覆盖聊天、主动学习、闲时思考、视觉、听觉、画板、记忆包、Agent API、审计回放。
3. 交付物增加 release demo flow、性能报告、红线报告、用户说明、demo assets。

---

## 2. 当前设计是否符合白皮书

结论: 符合。

依据:

1. 真相源仍是统一经验流。
2. StatePool 是 type projection, SSP 是 occurrence flow。
3. B/C/C* 负责现状认知、未来预测和过去解释。
4. DraftGrid 是行动 substrate, 不是字符串输出缓存。
5. 视觉感受器提供证据, 不给 label 结论。
6. 听觉初期作为 audit/节奏/焦点证据, 不冒充识别。
7. 未闭合感由奖惩、先天规则、预测不验和行动未完成派生, 不新增任务实体。
8. 伪因果允许形成, 后天反例和奖惩逐步松动。
9. UI 只读 RuntimeTickEvent。
10. LLM 只允许作为教师、课程、审计或工程辅助, 不作为学生侧答案。

---

## 3. 剩余风险

### R1 视觉重建质量

设计已闭合, 但实现需要真实 patch payload、clarity map、R/V sketch、source mask。若偷懒只画椭圆或贴原图, 直接失败。

### R2 idle_think 拟人程度

阈值太低会烦人, 太高会像死系统。必须通过 ask_fatigue、recent_asked、user_busy_signal、U 阈值联调。

### R3 B/C/C* 性能

大库下必须两阶段召回。索引可以加速, 但删除索引后必须可重建并慢速运行。

### R4 source_trust 泛化过度

必须测试同一个 source 在不同 context/modality 下 trust 分离。

### R5 记忆包卸载等价性

必须测试导入、去重、共享引用、卸载后状态等同未导入。

---

## 4. 开工建议

可以开工, 但必须按以下顺序:

1. Stage 0: 新 `apv3test/runtime/phase20_7/` 边界 + 红线扫描。
2. Stage 1: StatePool + SSP + 最小 EventLog + exact B0 + DraftGrid。
3. Stage 2: 完整 EventLog schema + provenance + 可重建索引。
4. Stage 3: B/C/C*。
5. Stage 4: 未闭合感 + idle_think + request_teacher。
6. Stage 5: 视觉 patch payload + inner picture。
7. Stage 6: audio audit + xiaoyi TTS actuator。
8. Stage 7: 工作台/API。
9. Stage 8: 完整发布 demo 包。

禁止:

1. 先做 UI。
2. 先做整图识别。
3. 先做记忆包生态。
4. 先接桌宠。
5. 只做最小 demo 就停下。

---

## 5. 可实现性自评分

目标不是成人 LLM, 而是会学的 3-5 岁小孩级本地 AP 底座。

| 项 | 评分 | 理由 |
|---|---:|---|
| 理论一致性 | 9.0/10 | 已回到白皮书闭环 |
| AP-native 纯度 | 8.8/10 | 仍需实现阶段红线守住 |
| 工程可执行性 | 8.0/10 | v1a 已补 schema、trace、stage 依赖 |
| 视觉重建风险 | 6.5/10 | 最大工程风险 |
| 闲时思考风险 | 7.0/10 | 阈值调校关键 |
| 发布 demo 可达性 | 7.6/10 | 需要 Stage 0-8 全部完成 |

总体判断: 可以按 v1a 开工。若 Stage 1-4 做真, 中文自由对话底座的核心会成立; 若 Stage 5 视觉也做真, 发布 demo 会有足够惊艳感。
