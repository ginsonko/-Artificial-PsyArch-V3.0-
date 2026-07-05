# APV3.0test Phase20.9p DraftGrid 后续行动竞争下沉验收报告

日期: 2026-06-28

## 1. 设计

Phase20.9o 已经把 `commit_reply` 的固定高 drive 下沉到 AP 主流程。但主对话路径仍偏“一次写完再提交”，缺少人类写话时常见的:

```text
写一点 -> 回看草稿 -> 犹豫是否继续 -> 发现冲突时准备修改 -> 决定提交或停下
```

Phase20.9p 的目标不是新增“编辑模块”，也不是让 UI 假装回看，而是把已有 DraftGrid 工作面上的后续行动纳入同一套行动竞争:

```text
continue_writing
read_draft
edit_cell
stop_generating
```

这些候选读取:

```text
DraftGrid 已写内容
+ B/C/C* 支持
+ 教师/反馈/未闭合压力
+ 学习闭环 carryover
+ 最近写入/回读次数
+ 低把握与冲突压力
-> DraftGrid 后续行动 drive
```

其中 `read_draft` 真实执行并写入经验流；`edit_cell` 在没有替代字符/片段从 B/C/C* 产生时只作为候选审计，不假修改。

## 2. 审查完善

### 2.1 为什么不直接做真编辑

白皮书要求 DraftGrid 行动必须来自状态池、SSP、B/C/C*、行动竞争和经验流。当前 runtime 还没有“替代字符/替代片段”由 C* 真实产生的机制。如果现在强行执行 `edit_cell`，就会变成隐藏编辑规则或模板修正。

所以本阶段只做:

- `read_draft` 真实落地。
- `continue_writing / edit_cell / stop_generating` 进入同一 AP-flow 行动竞争 trace。
- `edit_cell` 明确标记 `candidate_only_no_alternative_unit = true`。
- 不新增答案表、关键词规则、专属编辑器或 UI 认知旁路。

### 2.2 人类类比

人写话时会看到自己写出的东西。这个“看见草稿”会影响后续动作:

- 草稿短、后继还强，会继续写。
- 草稿已有内容、冲突压力高，会回看。
- 回看后觉得不对，才可能修改。
- 已经足够、继续压力低，才会提交或停下。

Phase20.9p 把这个过程压回 DraftGrid 工作面和行动竞争，而不是把回复当成一次性字符串。

## 3. 通过落地

修改文件:

```text
apv3test/runtime/phase20_7/runtime.py
apv3test/runtime/phase20_7/cognitive_cycle.py
tests/test_phase20_9p_draftgrid_action_competition.py
```

新增公式:

```text
PHASE20_9P_DRAFTGRID_ACTION_ID =
  apv3_phase20_9p_draftgrid_action_competition_from_ap_flow/v1
```

新增真实事件:

```text
event_kind = draft_grid_read
selected_action.action_type = read_draft
```

关键 trace:

```text
draftgrid_action_from_ap_flow:
  formula_id
  has_visible_text
  visible_text_hash
  visible_unit_count
  source_support
  request_pressure
  feedback_pressure
  low_grasp
  unclosed_pull
  conflict_pressure
  learning_write_support
  learning_commit_support
  recent_read_count
  recent_write_count
  continue_writing.drive
  read_draft.drive
  edit_cell.drive
  stop_generating.drive
  writes_answer_directly = false
  creates_reply_candidate = false
```

`_competition(...)` 现在会把这四个 DraftGrid 后续行动作为同一组候选加入行动竞争。`_feelings_for_output(...)` 也会暴露:

```text
readback_need
edit_pressure
stop_tendency
continue_tendency
```

## 4. 严谨验收测试

新增测试:

```text
tests/test_phase20_9p_draftgrid_action_competition.py
```

覆盖:

1. 写完后真实出现 `read_draft`，并且在 `commit_reply` 前发生。
2. `continue_writing / read_draft / edit_cell / stop_generating` 共享同一个 AP-flow context。
3. `edit_cell` 是审计候选，不在无替代单元时假修改。
4. commit tick 保留 DraftGrid readback readiness trace，且 write_cell 被 DraftGrid continue gate 压低。

本轮执行:

```text
python -m py_compile apv3test\runtime\phase20_7\runtime.py apv3test\runtime\phase20_7\cognitive_cycle.py
PASS

pytest -q tests\test_phase20_9p_draftgrid_action_competition.py
4 passed

pytest -q tests\test_phase20_9a...test_phase20_9p...
52 passed
```

Phase20 分段回归:

```text
Phase20.1-5: 24 passed
Phase20.6: 27 passed
Phase20 open_dialogue_foundation: 6 passed
Phase20.7: 48 passed
Phase20.8: 58 passed
Phase20.9: 52 passed
合计: 215 passed
```

红线与治理:

```text
python scripts\red_line_check_v14.py --phase 20.7-stage8
OK: Phase 20.7-stage8 deliverables present
OK: All red line checks pass on runtime/cognitive

python scripts\check_constant_governance.py
OK: Governance check passed (507 numeric constants)
仍有既有 91 个 @experimental constants pending rationale

python scripts\verify_phase20_7_release_demo.py
OK: Phase20.7 release demo package verified
```

## 5. 小白可理解展示

一次教学确认 turn 的行动序列现在类似:

```text
observe_text
integrate_feedback
write_cell
write_cell
write_cell
write_cell
write_cell
write_cell
read_draft
commit_reply
reply_tts_audio
```

可以理解为:

```text
AP 收到教学 -> 吸收反馈 -> 一个字一个字写草稿
-> 看一眼自己写好的草稿
-> 觉得可以提交
-> 提交并朗读
```

在 `read_draft` tick 中:

```text
read_draft drive = 0.4688
continue_writing drive = 0.0703
edit_cell drive = 0.1336
stop_generating drive = 0.0967
```

含义:

```text
AP 不是 UI 上“显示了一下草稿”。
它是真的多了一个 read_draft 行动和 draft_grid_read 经验事件。
后续 commit_reply 能看到刚才的 readback_need、continue_tendency、edit_pressure、stop_tendency。
```

## 6. 对抗性自审

### 已解决

- `stop_generating` 不再只是 `_competition` 中裸 `0.12` 固定行。
- DraftGrid 后续行动进入统一 AP-flow trace。
- `read_draft` 真实写入经验流，不是前端假展示。
- commit tick 能保留 DraftGrid action readiness trace。
- `edit_cell` 不假执行，不生成替代答案。

### 仍需注意

- `edit_cell` 目前仍不是完整编辑能力，只是候选审计。真正编辑必须等替代单元从 B/C/C* 或 DraftGrid 自回读冲突中产生。
- `continue_writing` 当前是候选与门控，不是真正重新规划长草稿。长回复还需要 successor 虚能量和 DraftGrid 游标更深结合。
- idle outward speech 路径中仍有自己的提交逻辑，后续应统一到同一套 DraftGrid action/commit readiness。
- 仍不能声明完整 L1/L2/L3 在线嵌入、完整六阶段 runtime、完整范式自学习、数学列竖式、object-centric 视觉想象或 Phase21 视觉教学泛化闭环完成。

## 7. 下一步

下一步建议 Phase20.9q:

```text
把 DraftGrid readback 的结果回灌到 SSP/ExperienceFlow，
让 read_draft 不只是一个经验事件，而能在后继 tick 产生“草稿已读、哪里不顺、哪里可能冲突、是否需要修改”的短期结构。
```

这一步会把 `edit_cell` 从“候选审计”推进到更真实的“有替代单元时可局部修订”，也是未来长回复和数学竖式的必要基础。
