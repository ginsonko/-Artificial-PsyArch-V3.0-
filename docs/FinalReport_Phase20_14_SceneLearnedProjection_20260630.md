# Phase20.14 — 场景学成判据 纯派生投影 — 最终汇总报告

**日期**: 2026-06-30
**范围**: Phase20.14 — 统一"场景学成判据"投影, 合成 13c 阶梯判据 + 10b lifecycle teacher_exit/cold_retest 就绪度
**循环**: 设计 → 审查完善 → 通过落地 → 严谨验收测试 → 最终汇总报告
**白皮书/勿增实体**: 全程遵守; 纯派生投影, 零新表/零新实体/零路由/零答案, 软判据不产布尔 passed

---

## §1 起因与目标

白皮书 `EDUCATION_PROTOCOL.md` 630 行明确: "keyword_organization_stage_passed=true before claiming a scene learned", 配合 148-149 行 scaffold 褪除顺序 "teacher_off -> cold_retest". 13c 已实现语言学习阶梯投影 (6 阶软判据), 10b 已实现学习对象生命周期 (7 阶 teacher_exit_ready/cold_retest_ready 就绪度). 但二者**并存互补, 未合成** —— 课程编排无法直接读"该场景在 teacher_off + cold_retest 双条件下是否走完 keyword_organization".

Phase20.14 目标: 合成一个**纯派生**的 `scene_learned_projection`, 回答上述问题, 供课程编排读取. 勿增实体: 只读既有 13c/10b/carryover 键, 不采集新信号, 不新增存储.

---

## §2 设计阶段 — 实读核实 (非摘要假设)

### 白皮书要求 (实读 EDUCATION_PROTOCOL)
- **630 行**: `keyword_organization_stage_passed=true` before claiming a scene learned (核心条件)
- **631-633 行**: `student_side_llm=false` / `full_sentence_action=false` / `answer_table_lookup=false` (红线, 已守)
- **791 行**: 成熟度标签含 `keyword_organization_stage` / `grammar_refinement_stage`
- **964 行**: 审计标签 `keyword_organization_pass` / `grammar_refinement_pass`
- **148-149 行**: scaffold 褪除顺序 `teacher_off -> cold_retest` (双褪除)

### 既有结构 (实读源码)
- **13c 阶梯投影** (`_language_learning_ladder_projection`, runtime.py:8844): 产 `ladder_scores` (6 阶连续分数) + `dominant_ladder_stage` + `ladder_confidence`, 主观 may_be_wrong, **不声称通过**.
- **10b lifecycle** (`_learning_object_lifecycle_projection`, runtime.py:9003 → `_learning_object_lifecycle_from_events`, 9550): 产 `lifecycle_stages` (7 阶: taught→...→teacher_exit_ready→cold_retest_ready) + `current_stage` + `stability`/`regression`/`cold_retest_pressure`. **确认 9850 行输出 `lifecycle_stages` 字段**, 供 14 派生索引.
- **carryover**: `teacher_off_readiness` / `feedback_only_readiness` / `cold_retest_readiness` / `scaffold_regression_need`.
- **合流点** (`_apply_learning_stage_runtime_progression`, 8642-8674): 13c 阶梯挂载于 8670, 14 挂载于其后.

---

## §3 审查完善 — 合规判定与方案

### 关键合规判定
1. **不能声称"学成=真"**: 白皮书 630 用 `passed=true`, 但 13c 已确立"阶梯是软判据 may_be_wrong, 不声称通过/收敛". 故 14 也**不产布尔 `passed=true`**, 只产连续 `scene_learned_confidence ∈ [0,1]` + `dominant_blocking_stage` (最拖后腿的阶), 让课程编排读软信号.
2. **禁用串**: 不出现 `scene_learned_complete`/`keyword_organization_converged`/`ladder_complete` 等. 用 `scene_learned_confidence` + `may_be_wrong=True`.
3. **双褪除就绪** (白皮书 148-149): `min(teacher_off_readiness, cold_retest_readiness)` 两者都高才算真褪除; 单教师退场不算学成 (冷重测可能暴露假学成). `scaffold_regression_need` 高反向拉低.
4. **keyword_organization 阶走完** (白皮书 630): 要求 `ladder_scores["keyword_organization"]` 高 **且** dominant 已到 keyword_organization 或 grammar_refinement (不能停前 4 阶却声称学成).
5. **生命周期就绪** (10b): `current_stage` 已到 `teacher_exit_ready` 或 `cold_retest_ready`.

### 合成逻辑 (三因子乘法, 软判据 may_be_wrong)
```
dual_fade_readiness      = min(teacher_off, cold_retest) * (1 - scaffold_need*0.5)
keyword_org_readiness    = min(ladder_scores[keyword_organization], reached_keyword_or_later)
lifecycle_readiness      = (stage_index - teacher_exit_idx) / (cold_retest_idx - teacher_exit_idx)
scene_learned_confidence = dual_fade * keyword_org_readiness * lifecycle_readiness
dominant_blocking_stage  = 三因子中最低者对应的阶名
```
三因子皆高才高 (乘法合成), 任一拖后腿则置信度低 —— 软判据, 非硬布尔 AND.

### 对抗预审 (落地前)
| 项 | 结论 |
|---|---|
| 新增实体? | 否, 只读既有键, 纯派生 |
| 声称学成布尔? | 否, 产连续 confidence + may_be_wrong |
| 红线? | student_side_llm/full_sentence_action/answer_table_lookup 全程不碰 |
| 双条件? | teacher_off + cold_retest 同时高才高 |
| 劫持主流? | projection_only / writes_answer_directly=False / creates_reply_candidate=False |

---

## §4 通过落地 — 改动清单

### `apv3test/runtime/phase20_7/runtime.py`
1. **常量** (PHASE20_13C 后): `PHASE20_14_SCENE_LEARNED_ID = "apv3_phase20_14_scene_learned_projection/v1"`
2. **挂载** (合流点, 13c 挂载后): 
   ```python
   scene_learned = _scene_learned_projection(merged, ladder=ladder, lifecycle=lifecycle, source_tick=source_tick)
   merged["scene_learned_projection"] = scene_learned
   merged["merged_with_scene_learned_formula_id"] = scene_learned.get("formula_id")
   ```
3. **投影函数** `_scene_learned_projection` (插在 `_inactive_language_learning_ladder` 后): 纯派生, 三因子乘法, 软判据.
4. **inactive 变体** `_inactive_scene_learned(reason)`.
5. **reason 补全**: 主逻辑 inactive 时给 `blocked_at_{dominant_blocking}_confidence_zero` (可诊断, 与 inactive 变体同型).
6. **索引派生优雅化**: `lifecycle_readiness` 从 `lifecycle_stages` 结构派生 `teacher_exit_idx`/`cold_retest_idx`, 非裸魔数 4/2.

### `tests/test_phase20_14_scene_learned_projection.py` (新, 10 测试)

---

## §5 严谨验收测试

### 5.1 import 自检
```
IMPORT_OK
PHASE20_14: apv3_phase20_14_scene_learned_projection/v1
has func: True True
```

### 5.2 新增 10/10 通过
- scene_projection_mounted_with_confidence (投影挂载, 连续 confidence, 无布尔 passed)
- guardrails_match_other_projections (projection_only/不写答案/不产候选/may_be_wrong)
- confidence_is_product_of_three_factors (三因子乘法一致性)
- dominant_blocking_stage_is_weakest_factor (最弱因子派生一致性)
- no_active_carryover_yields_inactive (无 carryover 时 inactive)
- far_text_does_not_fake_scene_learned (远输入不伪学成)
- runtime_does_not_claim_scene_learned_completion (禁用 over-claim 串)
- zero_regression_to_reply_and_selected (不改回复/不改 selected)
- reached_keyword_org_flag_matches_dominant (reached flag 与 dominant 一致)
- low_confidence_when_ladder_not_at_keyword_org (白皮书 630: 未到 keyword_org 阶时 confidence=0)

### 5.3 邻批 (13c/10b/10a/teaching/cooccurrence) 23/23 通过
源码改动零回归.

### 5.4 全量回归 (权威, 单进程)
```
890 passed in 1488.49s (0:24:48)
exit code 0
```
**890 passed / 0 failed** — 从既存失败清理后 880/0 → 14 后 890/0 (新增 10 测试全过), **零新增回归**, 底座持续全绿.

---

## §6 对抗性审阅 (写完后二次自检)

| 审阅项 | 结论 |
|---|---|
| 硬编码? | reached_keyword_or_later 用阶名 (keyword_organization/grammar_refinement) 是白皮书 630/791 结构阶名, 非答案/路由. lifecycle_readiness 索引已从结构派生 (非裸 4/2). dual_fade 的 *0.5 是软调制幅度非布尔门, 可接受 |
| 隐患? | 乘法合成致 conf 易为 0 — 这是正确的 (白皮书要三条件都过才算学成, 软判据 may_be_wrong). reason 字段已补, inactive 可诊断 |
| 白皮书不符? | 否. 630 软判据化 (不产布尔 passed, 与 13c 一致). 148-149 双褪除用 min(teacher_off, cold_retest). §35.4/§132/§19.3b 全程未碰 |
| 可更泛化/优雅? | 已做 — lifecycle_readiness 索引从 lifecycle_stages 派生 (原硬编码 4/2 改为结构 index), 更泛化 |
| 声称学成? | 否. 产 scene_learned_confidence ∈ [0,1] + may_be_wrong=True, 无 passed=true/converged/complete |

对抗性审阅通过.

---

## §7 勿增实体 / 白皮书合规

- 未新增任何认知实体/答题模块/隐藏解题器/外部课程脚本/答案表/关键词路由/学生侧 LLM/UI 决策逻辑.
- scene_learned_projection 是**纯派生投影**: 只读 13c ladder_scores / 10b current_stage+lifecycle_stages / carryover readiness, 不采集新信号, 不新增存储, 不改 selected, 不写答案, 不产候选.
- 软判据: 产连续 scene_learned_confidence, 不产布尔 passed, 不声称收敛/完成 (与 13c 同 may_be_wrong).
- 双褪除: teacher_off + cold_retest 两者都高才算真褪除 (白皮书 148-149).
- keyword_organization 阶走完: 白皮书 630 核心条件, dominant 未到该阶时 confidence=0 (不伪学成).
- §35.4 红线1 (在线嵌入不替代显式通道) / §132 (向量索引派生可重建) / §19.3b (学生侧无外部语义权威) 全程未触碰.

---

## §8 边界

- scene_learned_projection 只是投影, 不写库, 不路由, 不产候选, 不替 SSP/L2 显式通道.
- 它合成 13c + 10b, 但**不替代**二者: 13c 仍独立产阶梯分数, 10b 仍独立产生命周期阶段, 14 只在其上合成"场景学成"软判据.
- 教3次通常只到 process_paradigm_binding 阶, scene_learned_confidence 正确地为 0 (白皮书 630: 要 keyword_organization 阶过了才算学成) — 这是合规, 非缺陷.

---

## §9 下一步

Phase20.14 闭合后, 底座已具备:
- 13b L3 动作-后果在线嵌入 (从奖惩长进)
- 13c 语言学习阶梯 6 阶投影 (停在第几阶)
- 14 场景学成判据 (双褪除+keyword_org 走完 的软判据)
- 4 既存失败已清理 (底座全绿)

候选下一步 (待用户授权):
- **课程编排读取 scene_learned_projection**: 让课程编排层根据 scene_learned_confidence + dominant_blocking_stage 决定"该场景该加 scaffold 还是该准备冷重测". 需独立设计→审查循环.
- **更多拟人化语言效果**: 在 AP 主流约束下, 让底座在 teacher_off + cold_retest 条件下表现出"我学会了, 不用你盯着"的连贯语言风格 (仍走 AP 主流, 勿增实体).
