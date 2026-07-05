# APV3 Phase20+ 开放对话底座 — 任务进度统合 (冷保存进度文件)

**最近更新**: 2026-07-02
**用途**: 记录从 Phase20.13c 闭合后, 所有规划/进行/已完成的任务, 防遗漏. 每次循环更新.
**当前总体进度**: 约 96% (距小白可用惊艳底座约 4%)
**全量回归基线**: 923 passed / 0 failed (路2.3); 裁剪回归 128/0 (codex验收后)
**codex验收**: 2026-07-02 codex对抗性审查通过, "奖励过近似匹配太敢写"经实测判定为AP设计特性(子序列泛化, 9j保护)非bug, punctuation-only无问题（2026-07-02 修正: 语言域子序列泛化保留; 数字/高证据单元残差经 P0-2 反例通道收紧, 13+7≠10 已修）

## 2026-07-02 Fable5 核心修复

| 项 | 内容 | 关键位置 |
|---|---|---|
| P0-1 | punish>reward 的反馈标 alignment_role=counter_evidence，不进 exact_b0_index，召回候选排除 | runtime.py _record_teacher_feedback; experience_recall.py 过滤 |
| P0-2 | _alignment_counter_count + _unit_evidence_count 新派生计数；structural_b 的 source_coverage_penalty 由 residual_novelty+counter_pressure 经验后验驱动 | experience_log.py; runtime.py _find_structural_b |
| P0-3 | _channel_signals_from_experience 新函数，3 个调用点给 12 通道传 reward_pressure/punish_pressure/continue_count/repetition_fatigue | runtime.py |
| P1-1 | 意图层真竞争：先算 write/ask drive 再比较，瀑布删除；_competition 排序改纯 drive | runtime.py stage1 loop + _competition |
| P1-2 | 每 tick pool.tick_decay（10 个 tick 增量点）；状态池跨 turn 落盘/恢复 | runtime.py |
| P1-4 | 视觉回指=学得的指代：教学时共现绑定 + 提问时解析到最近视觉窗口 | runtime.py |
| M2 | 统一召回竞争: exact/structural 各算 write drive 竞争选源, exact>=0.62 快路径; 输出源跟随胜者 | runtime.py stage1 loop |

---

## §A 用户指出的重大遗漏 — 技能/课程体系未接通 phase20_7 (2026-07-01 补录)

白皮书 §40 "技能形成: 数学、语文、识字、绘图、桌面控制" + §65 "竖式数学: DraftGrid二维空间与行动序列" + §38 "模仿、续写、范式、风格、语法与表达".
配套: SKILL_PACKAGES.md (math21b/22/23/24b竖式数学, desktoptext12/13/14画字桌面, visualtext3/4/5 UI阅读, commonsense4/5/6/7日常对话) + EDUCATION_PROTOCOL.md (技能教学协议).

**已做本地适配但未接通 phase20_7**:
- Phase13 全套课程: 13_2字符部首/13_3词汇/13_4视觉/13_5音频/13_5b字符焦点数学/13_6表达范式/13_7动作原型/13_8社交常识
- 技能包: math21b除法竖式/math22混合题/math23桥接/math24b严格竖式审计/desktoptext12画字/visualtext3-5 UI阅读/commonsense4-7日常对话
- phase20_7 只接通 expression_paradigm_slot (8p), 其余技能全断

**已接通 (按白皮书§40/§65/§38, 2026-07-01完成第一批)**:
1. 竖式数学: DraftGrid 二维空间行动序列 (§65) — phase13_5b 已有 charfocus math
2. 识字/字符细化: 字符部首+chunk细化 (§38/§8) — phase13_2 已有
3. 常用字/常用词/范式句式泛化: 词汇+表达范式 (§38) — phase13_3/13_6 已有
4. 画字/桌面控制: desktoptext 技能包 (§40) — 已有技能包
5. 日常对话常识: commonsense 技能包 — 已有

**接通方式待设计**: 技能包是§37源分化包 (非答案表), 可作为课程输入接通 phase20_7. 但需审查每类技能的接通方式是否合规 (数学竖式是否走DraftGrid行动序列非答案表; 画字是否走canvas action非硬编).

---

## §1 已完成 (闭合, 有报告 + 测试 + 全量绿)

| 阶段 | 阶段名 | 报告 | 关键产出 |
|---|---|---|---|
| 13b | L3 行动后果向量嵌入 | FinalReport_Phase20_13b | L3 向量 + 退火 + §173.3 公式 |
| 13c | 语言学习阶梯投影 | FinalReport_Phase20_13c | 6 阶纯派生 ladder projection |
| Preexist | 4 失败独立清理 | FinalReport_Phase20_PreexistFailures_Cleanup | phrase_id 命名空间+陈旧断言 |
| 14 | 场景学成判据 | FinalReport_Phase20_14_SceneLearnedProjection | 三因子乘法 scene_learned |
| 9j-grasp | 泛化驱动结果锚定门控 | FinalReport_Phase20_9j_GeneralizationGraspGating | support×grasp×0.58 |
| 7v-A | 视焦点认知驱动 | FinalReport_Phase20_7v_VisualFocusCognitiveDrive | confidence_gap 注入 saliency |
| 7w-B1 | 未闭合压力认知涌现 | FinalReport_Phase20_7w_UnclosedPressureEmergent | _statepool_unresolved_pressure + u_delta 涌现 |
| 7x | §30.2 认知感受12通道 | FinalReport_Phase20_7x_CognitiveFeelingsPath1 | 11通道_cognitive_feelings_from_pool+把握9j-grasp |
| 7y | §31 情绪慢量积分 | FinalReport_Phase20_7y_EmotionSlowChannel | _integrate_emotion_from_ticks 6维度 |
| 首屏 | 冷启动体验示例 | FinalReport_DemoExperience_FirstScreen | 体验示例/数学/范式种子三按钮 |
| E-0' | 行动序列共现发现 | (在FinalSummary) | _observe_action_sequence_cooccurrence 存经验流 |
| E-0 | §29先天编码显式化 | (在FinalSummary) | 7条InnateRule+审计 |
| D-1' | 竖式数学范式涌现 | (在FinalSummary) | write→read→commit共现16次涌现 |
| D-2' | 造句表达范式涌现 | (在FinalSummary) | L2 linear_next+short_structure_next涌现 |
| D-3' | 画字桌面控制范式 | (在FinalSummary) | DraftGrid write_cell+observe闭环共现 |
| §38.2 | 范式材料导入 | (在FinalSummary) | 130个styled范式种子导入经验流 |
| codex验收 | 对抗性审查 | FinalSummary_Phase20_Plus_FullCycle | "太敢写"实测判为AP设计特性, 裁剪128✓ |

**对抗性已核实=已做完, 不再列待办**:
- A (对象中心组合式视觉想象): stage5 `_reconstruct_canvas_from_patch_payloads`+Phase21 object_centric 已实现 24/24 测试绿; 7v 注入 confidence_gap. codex"未验实"判错.
- B 泛化胆量/谨慎 posterior: 9j-grasp 已是 §173.5 合规 posterior (support_count 锚定); B 真 surprise_boost 在把握感标量上下文不可得会增实体, 诚实判无可合规深化.

---

## §2 待办 (按白皮书优先级, P0 最高)

### P0 (大缺口, 直接影响拟人涌现)

#### B-2: §30 认知感受通道接通 phase20_7 [~4%]
- **现状**: `runtime/cognitive/cognitive_feelings/factory.py` 实现通道 (fluency/boredom/fulfillment/satisfaction + reality_sense/imagination_sense/hearsay_sense/guess_sense/incongruity) **与白皮书 §30.2 的12通道不一致** — factory 是 §37 源分化+通用流畅度, 不是 §30.2. phase20_7 的 `_feelings_for_output` 已部分接通 grasp(把握✓) + draftgrid 通道, 但缺 §30.2 大部分通道.
- **不接通 factory.py** (会引入不合规实现), 改为 phase20_7 自补 §30.2 通道.
- **白皮书 §30.2 12通道**: 惊/违和/合理/正确/把握/期待/压力/未闭合/时间感/节奏感/证据缺口/重复疲劳
- **白皮书 §30.3 数学**: `feeling_channel_i = activation(metric_i, threshold_i, slope_i, fatigue_i)`
- **白皮书 §32.2 调制**: 行动竞争 `drive += emotion_modulation_a`

##### 路1 (路2的前置, 4核心通道, 对应求知欲/恐惧涌现)

| 通道 | 白皮书公式 | 派生源 | phase20_7 接入点 | 状态 |
|---|---|---|---|---|
| 1. 惊 Surprise | `Surprise_i = max(P_i - theta_surprise, 0)` (§30.2 + §721) | StateItem.cognitive_pressure (P=R-V) | _feelings_for_output + 状态池R/V | ✓ 已接 (路1) |
| 2. 违和 Dissonance | P<0 倒置 + 结构冲突 (§30.2+§516) | StateItem.cognitive_pressure (P<0) | _feelings_for_output | ✓ 已接 (路1) |
| 3. 合理 Reasonable | `Reasonable += cause_grasp*surprise_reduction` (§30.2+§1199) | C_backward cause_grasp + 惊衰减 | _feelings_for_output (commit 后回读) | ✓ 已接 (路1) |
| 4. 压力 Pressure | `Pressure=predicted_punish_energy` (§27.3) | 9y reward/punish_total + 7w pressure_emergent | _feelings_for_output + 已有u_value | ✓ 已接 (路1) |

##### 路2 (路1 后续, 补剩 8 通道)

| 通道 | 派生源 | 状态 |
|---|---|---|
| 5. 把握 Grasp | 9j-grasp 已接通 | ✓ 已接 (路1前置已做) |
| 6. 正确 Correct | low_abs(P) + reward_signal (反馈路径); verified_prediction 留补 | ✓ 已接 (路2.1, 2026-07-01) |
| 7. 期待 Expectation | reward_pressure (9y) + reward_signal (反馈路径); 纯未来奖励预测留 C_forward | ✓ 已接 (路2.2, 2026-07-01) |
| 8. 未闭合 Unclosed | u_value (7w已涌现) + §27.6 (B-1.2 边界+时间衰减) | ✓ 已接 (路2.3, 2026-07-01) |
| 9. 时间感 | §13.4熟悉快陌生慢 (1-surprise)*c_backward; 召回tick差波峰待补 | ✓ 已接 (路2.4, 2026-07-01) |
| 10. 节奏感 | continue_count*(1-repetition_fatigue) (§1294后继波峰); rhythm_lag边待补 | ✓ 函数已接 (路2.5, 2026-07-01, 调用点传参待rhythm_lag) |
| 11. 证据缺口 | (1-c_backward_grasp)*0.5+surprise*0.3+unclosed*0.2 (§1937+§3258) | ✓ 已接 (路2.6, 2026-07-01) |
| 12. 重复疲劳 | StateItem.fatigue聚合 + repetition_fatigue (§738 F_i公式) | ✓ 已接 (路2.7, 2026-07-01) |

**路2 完成状态**: §30.2 12通道全部接通 (11在_cognitive_feelings_from_pool + 把握grasp在 Feelings_for_output外部接入). 27/27测试✓ + 裁剪回归131/0✓ + 路2.3全量923/0✓.
**留补**: 正确感verified_prediction第3项 (待readback通过信号); 节奏感rhythm_lag边 (待SSP rhythm_lag); 期待纯未来奖励预测 (待C_forward接奖励路径).

**路1→路2 完成顺序**: 1→2→3→4 (路1闭合) → 6→7→8→9→10→11→12 (路2分期) → 5 已做.
每通道都走完整"设计→审查→落地→验收→报告"小循环, 不一股脑全塞.

#### 末屏冷启动体验 [~2.5%]
- **现状**: 小白打开 web workbench 是空白回放, 看不到 AP 看图拟人识别+学习过程
- **要做的**: 设计"开箱即用教学之旅" (预置教学资产+idle触发调味+中文化)
- **对抗性预审**: 预置教学资产是否合规 (§132 派生可重建 + 勿增答案表) — 需审查
- **白皮书**: §87 最终形态

### P1 (重要, 影响深度拟人)

#### B-3: §31 情绪慢量积分→表达风格 [✓ 已做 2026-07-01]
- **白皮书**: §31.1/§31.2/§31.3/§31.4
- **落地**: `_integrate_emotion_from_ticks(tick_events)` 从 turn 内 §30 12通道 feelings 衰减加权积分出 valence/arousal/dominance/pressure_tone/curiosity_tone/fatigue_tone 6维度
- Phase207TurnResult 加 emotion 字段 (向下兼容); 3主返回点接入
- 3测试✓ + 裁剪回归142/0✓
- **留补**: 跨turn持久化+memory_recall项待state持久机制接通; 表达风格调制待§1736 expression_style接通
- **报告**: FinalReport_Phase20_7y_EmotionSlowChannel_20260701.md

#### B-4: §27.6 evidence型释放 (1/5→2/5) [✓ 已做 2026-07-01]
- **白皮书**: §27.6 五种释放 (closure/source_removal/giving_up/impossibility/cost_revaluation)
- **落地**: impossibility_evidence 在 _decay_unclosed_for_idle 中实现 —
  attempt_count>=4 + 无后继 → 额外衰减; >=6+u<0.20 → resolved放下.
  §27.4 "条件不成立→放下, 不像机器TODO强行做".
- 2测试✓ + 裁剪回归134/0✓
- 2/5达成 (closure+impossibility); source_removal/giving_up/cost_revaluation 留补:
  - source_removal: 需外部用户输入信号"不用了" (非idle路径)
  - giving_up: 需stop_generating/abandon行动+现实支持
  - cost_revaluation: 需fatigue+punish信号优雅接通

#### B-5: §2363 counter_evidence 5项完整 [中]
- **现状**: L1 向量更新含方向 (§33.1 锚点不对称), 但 §2363 五种 counter_evidence (unfulfilled_prediction/observed_without_predicted/failed_action_outcome/teacher_correction/repeated_counterexample) 未单独落地
- **要做的**: 视错觉不可逆/创伤松动等由 §2363 涌现 — 需补证据通道
- **白皮书**: §2363 整条

### P2 (中等, 影响深度但非主线)

#### social 依恋/共情接通 phase20_7
- runtime/cognitive/social 存在 (Phase9.4/9.6), phase20_7 不接
- §171 红线: 共情不得魔法字段, 由奖惩+状态池+表情语音共现涌现

#### sleep 固化回放接通
- runtime/cognitive/sleep 存在 (Phase9.8), idle_think 不接
- §173.5 support_count 退火 + Phase10f memory_consolidation_forgetting_rhythm 部分有

#### habit 快系统接通
- apv3test/runtime/habit_system.py 存在, phase20_7 不接
- §24 快系统 + §32.2 habit_support

### P3 (低优先级/质量保障)

#### C: codex 外审其余"偏硬"点逐条核实 [✓ 已做 2026-07-01]
- **codex 提的偏硬点**: 见 `docs/FinalReport_C_CodexHardcodedReview_20260701.md`
- **逐条判定**: 5点全部判为合规或codex判错, 无需修改:
  - _support_from_reward_punish "手调先验" → 判错 (support_count锚定已是posterior)
  - STRUCTURAL_B_THRESHOLD 0.55 → 合规阈值 (§30.3 theta工程取值)
  - _bounded_multiplier → 合规边界 (§32.2 drive有界)
  - _apply_learning_protocol_competition_modulation → 合规调制 (§36六阶段)
  - _draftgrid_successor_action_outcome_modulation → 合规调制 (§173.3 L3)
- **当前状态**: ✓ 已做 (2026-07-01, 5点全合规不改)

#### 视焦点 idle 触发节奏调味
- 7v 注入了 confidence_gap 但 _next_idle_focus_from_canvas 在默认参数下未触发
- 需调 estimate_idle_visual_drive 或 turn 节奏让 idle visual tick 真正在小白默认打开时出现

#### S1 SimStruct 分层工程证据补强
- exact_b0/structural_b 已不依赖嵌入 (审查报告 S1 出路的工程实现), 但缺显式审计标注+测试证明

---

## §3 拟人涌现对照 (来自全人类心理机制↔AP清单)

参见 `docs/HumanPsychology_AP_Mapping_20260701.md`.

接通 P0+B-1 已完成的: §27.1 认知压→压力涌现 (求知/恐惧底层)
未接通的 (按心理机制):
- 求知欲完整涌现 (需 B-2 §30 通道接通 + B-4 §27.6 释放)
- 失恋注意难集中 (需 B-4 §27.6 evidence 释放让 U 自动降)
- 视错觉不可逆 (需 B-5 §2363 counter_evidence)
- 恐怖谷边际违和 (需 7v 残差边际调优 + B-2 违和通道接通)
- 情绪色彩调表达 (需 B-3 §31 慢量积分)
- 依恋/共情涌现 (需 social 接通)
- 创伤/单次强改 (需 §173.6 boost 弱区分 + §2363 反例松动)
- 睡眠固化 (需 sleep 接通)

---

## §4 进度更新规则

每完成一个循环 (设计→审查→落地→验收→对抗审阅→报告) 后:
1. 把已完成项移到 §1
2. 更新待办优先级/进度百分比
3. 记录全量回归数字
4. 标注下一步