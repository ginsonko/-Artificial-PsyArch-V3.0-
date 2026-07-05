# APV3.0test Phase20.9x DraftGrid 后继行动结果调制验收报告

日期: 2026-06-28

## 1. 设计

Phase20.9x 承接 Phase20.9w:

```text
9w: DraftGrid readback 后可以从 ExperienceFlow / SSP 召回历史后继片段。
9x: 后继片段召回后, 继续写 / 读回 / 修改 / 停下 / 提交 不再只看固定支持度, 而是受历史奖惩和行动结果调制。
```

本阶段不新增“拟人决策模块”。所有调制都进入既有 AP 主流程:

```text
ExperienceFlow successor
-> reward/punish value signal
-> DraftGrid action competition
-> continue_writing / read_draft / edit_cell / stop_generating / commit_reply 竞争
```

这对应白皮书里“奖励事件会强化当前归因的因, 惩罚事件会提高谨慎、替代搜索、抑制和回读”的机制。

## 2. 审查完善

审查发现:

1. Phase20.9j 已经让 reward/punish 调制结构泛化。
2. Phase20.9q 已经让 reward/punish backward attribution 调制后继行动倾向。
3. Phase20.9s 已经让 edit outcome 调制读/改/提交倾向。
4. Phase20.9w 的 ExperienceFlow successor 仍主要给 continue_writing 固定加成。

因此 9x 的正确落点是“把 9w successor trace 转成现有 DraftGrid action competition 的调制项”, 而不是增加新实体。

初始探针发现 `successor_trace.target_event_id` 指向 `draft_grid_read`, 它自身没有 reward/punish。最终修正为:

```text
先读 target/source event 的 reward/punish
若没有, 则用 successor target_text_hash 反查已有 experience_alignment.output_hash 的 reward/punish
```

这仍然是读取已有经验流, 没有新增表或旁路。

## 3. 通过落地

修改文件:

```text
apv3test/runtime/phase20_7/runtime.py
tests/test_phase20_9x_draftgrid_successor_outcome_modulation.py
```

新增公式:

```text
apv3_phase20_9x_draftgrid_successor_action_outcome_modulation/v1
```

调制信号:

```text
flow_support
flow_score
source_fit / target_fit
pending_successor_pressure
source_support
low_grasp
conflict_pressure
repetition_fatigue
reward
punish
positive_evidence
caution_evidence
```

输出到已有行动:

```text
continue_writing_delta
read_draft_delta
edit_cell_delta
stop_generating_delta
commit_reply_delta
```

奖励过的 successor:

```text
continue_writing 上升
commit_reply 上升
read_draft 下降
stop_generating 下降
```

惩罚过的 successor:

```text
continue_writing 下降
read_draft 上升
edit_cell 上升
stop_generating 上升
commit_reply 下降
```

## 4. 小白可测效果

奖励场景:

```text
先教 AP 一段长回复, 并给奖励。
之后 AP 只想起前半段。
它读回草稿后, 想起历史上后面接过后半段。
因为这个后继曾经被奖励, 它更敢继续写, 更敢提交, 不那么想停下。
```

惩罚场景:

```text
先教 AP 一段长回复, 但给惩罚。
之后 AP 只想起前半段。
它仍然可能想起后半段, 但行动竞争里会更谨慎:
更想再读一遍、更倾向修改或停下, 提交倾向下降。
```

这就是更拟人的地方: AP 不是硬阈值决定“写/不写”, 而是根据成功/失败经验改变自己的胆量和谨慎度。

## 5. 严谨验收测试

新增专项:

```text
pytest -q tests\test_phase20_9x_draftgrid_successor_outcome_modulation.py -vv
2 passed
```

相邻回归:

```text
pytest -q tests\test_phase20_9w_experienceflow_draftgrid_successor.py tests\test_phase20_9t_multiread_revision_loop.py
5 passed
```

Phase20.9 全量:

```text
$phase209 = Get-ChildItem -Path tests -Filter 'test_phase20_9*.py' | ForEach-Object { $_.FullName }
pytest -q $phase209
71 passed
```

Phase20.8 回归:

```text
pytest -q tests\test_phase20_8b...test_phase20_8r...
58 passed
```

Phase20.7 回归:

```text
pytest -q tests\test_phase20_7_stage0...stage8...
48 passed
```

红线与常量治理:

```text
python scripts\red_line_check_v14.py --phase 20.7-stage8
OK: Phase 20.7-stage8 deliverables present
OK: All red line checks pass on runtime/cognitive

python scripts\check_constant_governance.py
OK: Governance check passed (507 numeric constants)
仍有既有 91 个 @experimental constants pending rationale warnings
```

## 6. 对抗性自审

已解决:

1. 9w successor 不再只是固定加成, 已进入奖惩/压力/疲劳联合调制。
2. reward/punish 不是从新表读取, 而是回查已有 experience_alignment。
3. 调制只影响既有 DraftGrid action competition, 不创建回复候选, 不直接写答案。
4. 运行时代码没有针对测试文本的特殊处理。
5. 惩罚不会删除记忆, 只改变主观倾向: 更谨慎、更想回读/修改/停下。

仍需保留边界:

1. 这还不是完整范式自学习。
2. 这还不是 L1/L2/L3 在线嵌入完成。
3. 这还不是完整六阶段 runtime。
4. 这还不是数学列竖式。
5. 当前奖惩调制仍是公式化硬化版本, 还需要后续继续让参数本身被经验调参器调制。

## 7. 下一步

下一步建议 Phase20.9y:

```text
把 DraftGrid successor outcome modulation 从“固定公式硬化”推进到“经验调参器参与”的版本。
```

目标:

```text
AP 自己逐步学会:
低把握但奖励过时可以更大胆。
低把握且被纠正过时要更谨慎。
重复发出没有反馈时要降低外显倾向。
多次回读后仍有冲突时要更倾向停下或请教。
```

这会继续逼近“像人一样会形成习惯、迷信、谨慎、胆量和后天修正”的开放对话底座。
