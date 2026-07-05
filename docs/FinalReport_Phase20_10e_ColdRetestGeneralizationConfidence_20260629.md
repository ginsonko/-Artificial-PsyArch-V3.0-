# Phase20.10e 冷启动复测泛化胆量/谨慎调制最终报告

日期: 2026-06-29

## 1. 设计目标

Phase20.10e 的目标是把“冷启动复测成功/失败”继续回灌到 AP 主流程:

- 冷测成功的学习对象: 后续遇到低把握但结构相似的 B 召回时, 更敢尝试泛化。
- 冷测失败的学习对象: 后续更倾向复盘、请教、回读或局部修正, 不盲目提交。
- 所有调制只影响 StatePool/SSP/ExperienceFlow/B/C/C*/Action Competition 的支持度和行动 drive, 不直接生成回复, 不新增答案表、课程脚本或专属认知实体。

对应公式:

`apv3_phase20_10e_cold_retest_generalization_confidence_tuning/v1`

## 2. 审查结论

这一步不新增认知实体。实现只读取既有数据:

- `short_structure_flow::self_test::*` occurrence
- `experience_alignment`
- `learning_object_lifecycle`
- 结构 B 候选与已有行动竞争

冷测调制被限制在两个既有通道:

- 结构 B 支持度与接受阈值: 让相似召回读取冷测稳定性或退行性。
- 生命周期 action deltas: 让后继 tick 的 `write_cell / commit_reply / request_teacher / read_draft / edit_cell / idle_think` 被同一投影调制。

红线:

- 不写答案。
- 不创建回复候选。
- 不绕过 DraftGrid。
- 不新增表。

## 3. 落地内容

### Runtime

文件: `apv3test/runtime/phase20_7/runtime.py`

新增:

- `PHASE20_10E_COLD_RETEST_GENERALIZATION_ID`
- `_cold_retest_self_test_rows_for_alignment(...)`
- `_cold_retest_generalization_tuning(...)`
- `_cold_retest_generalization_tuning_for_alignment(...)`

改动:

- `_find_structural_b(...)` 读取冷测调制:
  - `cold_retest_generalization_boost`
  - `cold_retest_caution_penalty`
  - `cold_retest_relief`
  - `cold_retest_guard`
- `_learning_object_lifecycle_from_events(...)` 合并 10e 的 action deltas。

### Workbench

文件: `apv3test/web/static/phase20_7_workbench.js`

新增只读展示:

- 学习对象摘要中的 `泛化胆量 / 泛化谨慎`
- 审计曲线:
  - `对象:泛化胆量`
  - `对象:泛化谨慎`

### Tests

文件: `tests/test_phase20_10e_cold_retest_generalization_confidence.py`

覆盖:

- 冷测成功: 相似召回出现泛化胆量, `commit_reply/write_cell` 倾向提高, `request_teacher` 降低。
- 冷测失败: 泛化谨慎升高, `request_teacher/read_draft/edit_cell` 倾向提高, `commit_reply` 降低。
- 两条路径均证明 `writes_answer_directly=False` 且 `creates_reply_candidate=False`。

## 4. 验收结果

已通过:

- `pytest -q tests/test_phase20_10e_cold_retest_generalization_confidence.py -vv`: 2 passed
- `pytest -q tests/test_phase20_10d_long_interval_cold_retest.py tests/test_phase20_10b_learning_object_lifecycle.py tests/test_phase20_10e_cold_retest_generalization_confidence.py -vv`: 6 passed
- Phase20.10 全量: 11 passed
- Phase20.9 全量: 76 passed
- Phase20.8 全量: 58 passed
- Phase20.7 全量: 48 passed
- `python -m py_compile apv3test/runtime/phase20_7/runtime.py apv3test/web_chat.py`: PASS
- `node --check apv3test/web/static/phase20_7_workbench.js`: PASS
- `python scripts/red_line_check_v14.py --phase 20.7-stage8`: PASS
- `python scripts/check_constant_governance.py`: PASS, 91 existing experimental warnings retained

## 5. 小白可测示例

1. 教:
   - 用户: `没错,你好聪明`
   - 教学: `谢谢`
2. 让 AP 闲时运行, 等它出现冷启动复测自测。
3. 再问:
   - 用户: `你好聪明`
4. 预期:
   - AP 更敢用结构相似召回。
   - tick 回放中能看到:
     - `cold_retest_generalization_boost > 0`
     - `generalization_courage > generalization_caution`
     - `creates_reply_candidate=False`
     - `writes_answer_directly=False`

失败场景:

如果冷测记错, tick 回放中会看到:

- `generalization_caution > generalization_courage`
- `request_teacher/read_draft/edit_cell` delta 上升
- `commit_reply` delta 下降

## 6. 边界

现在可以声明:

- 冷测成功/失败已经能反向调制低把握结构泛化与行动竞争。
- “隔久还答对 -> 更敢举一反三; 隔久答错 -> 更谨慎复盘/请教/修订”已经进入 AP 主流程。

仍不能声明:

- L1/L2/L3 在线嵌入已完成。
- 完整范式自学习已完成。
- 数学列竖式已完成。
- Phase21 视觉教学泛化闭环已完成。

## 7. 下一步

下一步建议进入 Phase20.10f:

把 20.10e 的冷测胆量/谨慎继续接到“学习对象长期稳定度”与“遗忘/复习节律”上。也就是让 AP 不只是一次冷测后调制, 而是能在更长时间里形成类似人的记忆巩固、遗忘、复习、再巩固循环, 仍然只使用 ExperienceFlow / SSP / StatePool / B/C/C* / action competition。
