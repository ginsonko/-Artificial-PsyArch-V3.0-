# Phase20.13c — Language Learning Ladder 纯派生判据投影 · 最终汇总报告

日期: 2026-06-30
子项目: APV3.0test
白皮书依据: `EDUCATION_PROTOCOL.md` "2026-06-09 Addendum: Language Learning Ladder" 6 阶段; Course Requirements (`keyword_organization_stage_passed=true` 才能算场景学成; `student_side_llm=false`/`full_sentence_action=false`/`answer_table_lookup=false`)
设计前对话决策: 用户授权"增设阶梯投影(纯派生)"方向, 守勿增实体红线.

---

## 1. 做了什么

实现白皮书 Language Learning Ladder 6 阶段的纯派生判据投影 `_language_learning_ladder_projection`, 与既有 `learning_stage_runtime_progression` (教学褪除) / `learning_object_lifecycle` (冷重测就绪) 三者并存互补. ladder 是"语言学习阶梯判据", 不替代教学褪除判定.

**不增实体 (守住)**:
- 6 阶梯判据信号**全部已在 runtime 现成为 projection_only 量**, ladder 只做派生聚合, 零新增存储表/列/认知实体/路由/答案表/正则路由/学生端 LLM.
- ladder 投影挂入既有 `learning_loop_carryover` 新 key `language_learning_ladder` (与 `learning_stage_runtime_progression` 同载体同 guardrail).
- **不进 `_competition` 的 drive 调制** — ladder 是判据投影, 不是动作竞争源 (区别于 L3 调制); selected 仍由 AP 主闭环决定.
- 主观 `may_be_wrong=True`, 不在学生侧硬判"已学成"布尔门, 让 B/C/草稿涌现继续驱动.

## 2. 落地文件

| 文件 | 改动 |
|---|---|
| `apv3test/runtime/phase20_7/runtime.py` | 新增常量 `PHASE20_13C_LANGUAGE_LEARNING_LADDER_ID`; 新增 `_language_learning_ladder_projection` + `_inactive_language_learning_ladder`; 在 `_apply_learning_stage_runtime_progression` 内 lifecycle 之后调用并挂入 carryover 两个新 key |
| `tests/test_phase20_13c_language_learning_ladder.py` | 新增 7 测试, 镜像 10x 投影测试结构 |

## 3. 6 阶梯判据公式 (纯派生, 无新采集)

每条 score 经 `_unit` 收敛到 [0,1], 权重是判据公式必要系数 (与现有 10a stage_scores 同性质, 非答案/路由硬编码):
1. **echo_imitation** — `review_count + reward_pressure`: 已复读有过反馈 (复用 lifecycle 计数)
2. **successor_prediction** — `self_test_count + (consolidation - forgetting) + self_test 阶`: 已自测且记忆在巩固 (接续真有召回)
3. **multi_reply_aggregation** — `generalization + reward_pressure + self_test_success`: B 候选重叠抬能 (复用 10a stage_scores.generalization)
4. **process_paradigm_binding** — `self_test_stage + (1 - scaffold) + cold_retest_pressure`: 内部过程锚下自助
5. **keyword_organization** — `max(teacher_off, feedback_only) + self_test_success + (consolidation - forgetting) + generalization`: **白皮书关键** — 仅在 teacher_off/feedback_only 条件下才上抬, "教师退场/纯反馈下通过此阶才算学成"
6. **grammar_refinement** — `refinement_pressure (edit_count+read_count) + reward_pressure + (stability - regression) - punish_pressure`: 反复读稿/编辑精修 (白皮书 grammar=refine grammar/particles/tone/continuity)

主司: `dominant_ladder_stage = max(scores)`, `ladder_confidence`, `ladder_stage_order` 元组.

## 4. 对抗性代码审阅 (用户强制要求, coding 后做)

1. **牵强信号修正 (coding 后发现, 已修)**: 初版 grammar_refinement 用 `boldness_multiplier - 1.0` 作"形式打磨倾向". 对抗性审阅发现 boldness 是"胆壮敢写" (write_cell 的胆壮乘子), 不是"语法定调打磨" — 牵强派生, 违白皮书 grammar 语义. **已修**: 改用 9z tuner 的 `edit_count + read_count` 派生 `refinement_pressure` (反复读稿/编辑微调, 正合白皮书 refine continuity/tone). 复测 7/7 通过.
2. **裸小数权重判定**: 6 阶梯用 0.42/0.30/0.38 等权重. 审阅判定: 这些是连续 score 的判据权重 (与现行 `_learning_stage_runtime_progression` 的 0.62/0.64/0.18 同性质), 非答案表/路由硬编码; 公式 docstring 已说明每阶段语义. 保留.
3. **学成布尔门红线**: 白皮书明确 `keyword_organization_stage_passed=true` 才算学成. 对抗性: 若做成硬布尔门则越界 (学生侧硬判学成). ladder 保持连续 score + `may_be_wrong=True`, 不做布尔门 — 让判据供课程编排 读 + 让 B/C/草稿涌现继续驱动, 守住边界.
4. **挂载重复隐患检查**: 我加 `merged["learning_object_lifecycle"] = lifecycle` (line 8661) 与 `_merge_learning_stage_with_object_lifecycle` 内挂载 (line 8837) 分属不同作用域, 不冲突. compile + 23 邻批通过确认.
5. **导出策略**: FORMULA_ID 未加顶层 `__init__.py` 导出 — 与现有 10x FORMULA_ID 一致 (__init__ 都不导 FORMULA_ID), 测试用 `from apv3test.runtime.phase20_7 import runtime as _rtm; _rtm.PHASE20_13C_...` 拿, 同构保守, 不破坏现有导出面.

## 5. 严谨验收 (实际跑过)

| 项 | 实际结果 |
|---|---|
| `py_compile` runtime.py | EXIT=0 ✓ |
| `tests/test_phase20_13c_language_learning_ladder.py` | **7/7 通过** (4.43s) ✓ — 多于计划 6 个 (多写一个 zero-regression 测试) |
| 13c+13b+lifecycle+stage_prog+carryover 邻批 (23 测试) | **23/23 通过** ✓ — 确认改 `_apply` 未碰坏 learning_stage/lifecycle/L3/carryover 路径 |
| red_line_check_v14 main gate | `OK: All red line checks pass on runtime/cognitive` ✓ |
| 三组样本探针 | s1 教→"嗯,记下了"; s2/s3 未知→"我还不太知道怎么说"中立; idle review 时 ladder active (dominant=process_paradigm_binding) 暴露但不破坏回复 ✓ |
| ladder 投影形状实测 | active=3 行, 6 scores (echo 0.30/successor 0.073/aggregation 0.325/process 0.593/keyword 0.173/grammar 0.367), projection_only=True, writes/creates=False ✓ |
| 全套回归 (前台权威单进程跑完, 25min) | **876 passed / 4 failed** (880 tests, 1510s) ✓ — 873(13b基线)+13c新增7 = 880; 4 失败正是已核实既存 4 个, **13c 零新增回归** |

## 6. 勿增实体边界守住的证据

- 零新增表/列: vector_l3 等已存; ladder 全在既有 carryover.
- 零新增采集: 6 阶梯全读 carryover/progression/lifecycle/tuner 现成 key.
- 零答案/路由硬编码: 不写答案、不改 selected、不藏 solver、无正则路由、无学生端 LLM.
- 不过度宣称: 无 `ladder_complete`/`ladder_converged`/`keyword_organization_converged`/`l1_l2_l3_complete`/`six_stage_learning_complete` 等禁词 (测试 test_phase20_13c_runtime_does_not_claim_ladder_convergence_or_completion 锁住).
- 与现有 10x 投影 guardrail 完全一致: `projection_only/subjective/may_be_wrong/uses_existing_ap_flow/writes_answer_directly=False/creates_reply_candidate=False`.

## 7. 既存失败 (4 个, 独立于 13c)

13b 已核实并记录的 4 个既存失败 (phase7_9 phrase_kind 红线 / phase8 web 模板演进×2 / sqlite ontology 多表) — 13c 改动**完全不碰**这些文件. 13c 全量回归权威 (**880 tests: 876 passed / 4 failed**), 4 失败正是这同一组既存失败, **13c 零新增回归**.

## 8. 下一步

- **13c 已闭合** (待全量回归最终确认). Language Learning Ladder 6 阶梯判据已落地为纯派生投影.
- **Phase20.14 候选**: 把 6 阶梯判据 (ladder) + 教学褪除 (lifecycle teacher_exit/cold_retest) 合并为统一"场景学成判据"投影, 喂给 cold_retest/generalization 闭环, 让课程编排能读"某场景是否通过 keyword_organization, 在教师退场/冷重测条件下成立". 届时独立走设计→审查循环.
- **既存 4 失败**: 建议作为独立 phase20.x 清理任务 (改陈旧测试以匹配 web/ontology 演进, 或按 AP 主流重构 phrase_kind 路由), 不在 13c 循环内夹带, 避免越界改非相邻代码.