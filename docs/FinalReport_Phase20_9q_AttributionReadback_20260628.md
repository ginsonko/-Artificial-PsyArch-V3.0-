# APV3.0test Phase20.9q 奖惩调制溯源巩固与 DraftGrid 回读回流验收报告

日期: 2026-06-28

## 1. 设计

Phase20.9q 承接白皮书新增的两个 AP-native 规则:

```text
1. 每 tick 的 C_backward 不只解释现在, 也为奖惩学习提供候选因.
2. DraftGrid read_draft 是 SELF_DRAFT_GRID 感受器回流, 不是 UI 展示.
```

目标是让:

```text
draft_grid_write -> draft_grid_read -> draft_grid_commit/teacher_feedback
```

真实进入 SSP/ExperienceFlow, 并让奖励/惩罚读取同 tick 或近邻 tick 的 C_backward cause_slot、SSP occurrence/edge 和注意/行动 eligibility, 形成可动摇的期待、压力、抑制和替代搜索倾向.

本阶段没有新增信念模块、迷信模块、强迫模块、编辑模块或外显意图模块.

## 2. 审查完善

### 2.1 为什么要补 `SELF_DRAFT_GRID` occurrence

Phase20.9p 已经让 `read_draft` 成为真实行动和 `draft_grid_read` 事件, 但事件本身还不等于 AP 看见了自己的草稿. 若没有 occurrence/edge, 后继 B/C/C* 只能看到日志, 看不到短期结构.

所以 Phase20.9q 让:

```text
draft_grid_write -> SELF_DRAFT_GRID unit occurrence
draft_grid_read -> SELF_DRAFT_GRID readback occurrence
write occurrence -> readback occurrence edge
readback occurrence -> short_structure_flow occurrence
```

这样 AP 才有“我写了这个, 我又看见了这个”的结构证据.

### 2.2 为什么奖惩归因不新增实体

奖励/惩罚调制只作为 `learning_deltas` 和 carryover 进入现有行动竞争:

```text
request_teacher
maintain_unclosed
write_cell
commit_reply
idle_think
read_draft
edit_cell
stop_generating
```

奖励提高期待和注意偏置; 惩罚提高压力、抑制和替代搜索. 它们都是可动摇权重, 不是绝对规则.

### 2.3 兼容性修正

最初 9q carryover 覆盖了 9e 学习循环 carryover. 这不符合“合流而非替代”的 AP 主流程. 已修正为:

```text
Phase20.9e learning_loop_carryover
+ Phase20.9q attribution_consolidation_carryover
-> merged carryover
```

保留 9e 的 `formula_id`, 并在子字段中保留 9q 归因巩固证据.

## 3. 通过落地

修改文件:

```text
apv3test/runtime/phase20_7/runtime.py
tests/test_phase20_9p_draftgrid_action_competition.py
tests/test_phase20_9q_attribution_readback.py
```

新增公式:

```text
PHASE20_9Q_DRAFTGRID_READBACK_FLOW_ID =
  apv3_phase20_9q_draftgrid_readback_self_flow/v1

PHASE20_9Q_ATTRIBUTION_CONSOLIDATION_ID =
  apv3_phase20_9q_reward_punish_backward_attribution_consolidation/v1
```

新增 trace:

```text
draftgrid_readback_self_flow:
  occurrence_id
  substrate = SELF_DRAFT_GRID
  source_write_occurrence_ids
  edge_ids
  readback_energy
  read_drive
  conflict_pressure
  writes_answer_directly = false

reward_punish_backward_attribution_consolidation:
  reward / punish
  cause_grasp
  eligible_occurrences
  eligible_edges
  expected_reward_delta
  expected_punish_delta
  attention_bias_delta
  inhibition_delta
  alternative_search_delta
  subjective = true
  may_be_wrong = true
```

## 4. 严谨验收测试

新增测试:

```text
tests/test_phase20_9q_attribution_readback.py
```

覆盖:

1. `draft_grid_read` 真实写入 `SELF_DRAFT_GRID` readback occurrence.
2. readback occurrence 与最近 `draft_grid_write` occurrence 有 `draft_write_to_readback` edge.
3. 奖励反馈产生 `expected_reward_delta` 和 `attention_bias_delta`.
4. 惩罚反馈产生 `expected_punish_delta`、`inhibition_delta` 和 `alternative_search_delta`.
5. 奖励/惩罚 carryover 进入现有行动竞争, 不新增行动实体.
6. 惩罚场景下 `edit_cell` 仍然只是候选审计, 没有替代单元时不假编辑.

本轮执行:

```text
python -m py_compile apv3test\runtime\phase20_7\runtime.py apv3test\runtime\phase20_7\cognitive_cycle.py
PASS

pytest -q tests\test_phase20_9q_attribution_readback.py
3 passed

pytest -q tests\test_phase20_9a...test_phase20_9q...
55 passed

pytest -q tests\test_phase20_7_stage0...stage8...
48 passed

pytest -q tests\test_phase20_8b...test_phase20_8r...
58 passed

python scripts\red_line_check_v14.py --phase 20.7-stage8
OK: Phase 20.7-stage8 deliverables present
OK: All red line checks pass on runtime/cognitive

python scripts\check_constant_governance.py
OK: Governance check passed (507 numeric constants)
仍有既有 91 个 @experimental constants pending rationale
```

## 5. 小白可理解展示

以前:

```text
AP 写草稿 -> 日志里有 read_draft 事件 -> 提交
```

现在:

```text
AP 写了每个字
-> 每个字作为 SELF_DRAFT_GRID occurrence 进入短期结构
-> AP 回读草稿
-> 回读也作为 SELF_DRAFT_GRID occurrence 进入短期结构
-> 写入和回读之间有 SSP edge
-> 如果用户奖励/惩罚, AP 会把当时“写过/读过/归因过”的对象当作候选因学习
```

奖励时, 它会更敢沿相似召回和草稿提交继续做.

惩罚时, 它不会硬删记忆, 而是更容易谨慎、请教、回读、准备修改或寻找替代解释.

## 6. 对抗性自审

### 已解决

1. `draft_grid_read` 不再只是事件日志, 已有 `SELF_DRAFT_GRID` occurrence.
2. DraftGrid 写入和回读已有 SSP edge.
3. 奖惩调制 C_backward 归因巩固已进入 learning delta.
4. 9q carryover 已与 9e 学习循环合流, 没有互相覆盖.
5. 红线扫描通过, 未新增关键词路线、答案表、隐藏求解器或 LLM.

### 仍需注意

1. `edit_cell` 仍不是完整真编辑, 因为替代单元还没有由 C* 稳定地产生.
2. 奖惩归因目前是 trace/carryover 级, 还不是完整 L3 在线嵌入.
3. 低把握泛化已能被奖励/惩罚调制, 但还需要更多跨 session/冷启动验收.
4. DraftGrid readback 进入 ExperienceFlow 后, 还应继续让 C_backward 更明确地显示“回读解释了哪个草稿冲突”.
5. 仍不能声明完整六阶段 runtime、完整范式自学习、数学列竖式、object-centric 视觉想象或 Phase21 视觉教学泛化闭环完成.

## 7. 下一步

下一步建议 Phase20.9r:

```text
把 readback conflict -> C* alternative unit -> edit_cell 真局部修订打通.
```

也就是让 AP 在回读草稿后, 如果 C* 中已经存在更合适的替代字符/片段, `edit_cell` 才能从“候选审计”变成真实局部修改行动. 这一步会直接服务长回复、范式自学习和后续竖式计算.

