# APV3.0test Phase20.9r C* 替代单元驱动 DraftGrid 局部修订验收报告

日期: 2026-06-28

## 1. 设计

Phase20.9r 承接 Phase20.9q 的 DraftGrid 回读回流:

```text
draft_grid_write -> draft_grid_read -> SELF_DRAFT_GRID occurrence/edge
```

本阶段目标是继续打通:

```text
readback conflict -> C* alternative unit -> edit_cell 真局部修订
```

核心约束:

1. `edit_cell` 不能直接读教师答案.
2. `edit_cell` 不能作为字符串纠错器、正则修复器或隐藏 solver.
3. 只有 DraftGrid 回读内容与当前 C*/B 期望单元不一致, 且 C* 能给出替代单元时, 才允许真实修改某个 cell.
4. 修改后仍必须经 DraftGrid visible_text 回读和 `commit_reply`, 不能绕过 DraftGrid 直接写 `reply_text`.

## 2. 审查完善

### 2.1 为什么不能用同轮教学文本验收

最初测试直接在带 `teacher_feedback` 的同一轮模拟写错. 这会混入 `integrate_feedback` 的确认表达, 例如:

```text
嗯,记下了。
```

这不是 Phase20.9r 要证明的“局部修订”, 而是教学整合后的外显确认. 若把教师反馈文本直接当作 edit 的替代单元, 会重新滑向“教学答案直通 DraftGrid”的红线.

已修正为更 AP-native 的两轮验收:

```text
第 1 轮: 用户输入 -> 教师反馈 -> experience_alignment / exact B0 经验写入
第 2 轮: teacher-off 复问 -> B/C/C* 召回要写的输出 -> 故意模拟某个 DraftGrid cell 写错 -> read_draft -> edit_cell 局部修订 -> commit_reply
```

### 2.2 测试故障注入不是认知实体

新增参数:

```text
debug_draftgrid_write_mutation
```

只用于测试“行动执行时写错一个格子”的可观测故障. 它不参与 B/C/C*、不生成候选、不参与行动竞争, 也不是 runtime 的正常能力. 是否能编辑仍由:

```text
DraftGrid visible_text
+ expected_output_chars from exact_b0 / structural_bccstar / C*
+ draftgrid_action_context
```

共同决定.

## 3. 通过落地

修改文件:

```text
apv3test/runtime/phase20_7/runtime.py
tests/test_phase20_9r_edit_cell_cstar_alternative.py
```

新增公式:

```text
PHASE20_9R_EDIT_CELL_ID =
  apv3_phase20_9r_cstar_alternative_unit_edit_cell/v1
```

新增/强化 trace:

```text
cstar_alternative_unit:
  can_edit
  row / col / cell_index
  old_unit / alternative_unit
  source = cstar_expected_output_vs_self_draftgrid_readback
  source_support
  conflict_pressure
  drive
  subjective = true
  may_be_wrong = true
  writes_answer_directly = false
  creates_reply_candidate = false

draftgrid_edit_self_flow:
  occurrence_id
  substrate = SELF_DRAFT_GRID
  source_occurrence_ids
  edge_ids
  old_unit_hash
  alternative_unit_hash
  visible_text_hash
```

落地行为:

1. `read_draft` 后检查当前 visible DraftGrid 与 C*/B 期望输出单元.
2. 若无替代单元, `edit_cell` 只保留为候选审计.
3. 若存在替代单元, `edit_cell` 写回具体 row/col.
4. `draft_grid_edit` 写入 ExperienceLog.
5. `SELF_DRAFT_GRID` edit occurrence 和 `readback_conflict_to_edit` edge 写入 SSP.
6. 后续 `commit_reply` 读取修改后的 `grid.visible_text()`.

## 4. 严谨验收测试

新增测试:

```text
tests/test_phase20_9r_edit_cell_cstar_alternative.py
```

覆盖:

1. 正常回读无冲突时, `edit_cell` 只作为候选审计, 不执行修改.
2. teacher-off 复问时, B/C/C* 召回预期输出.
3. 测试故障注入让 DraftGrid 第一格写错.
4. `read_draft` 后 C* 替代单元生成.
5. `edit_cell` 真正把错误 cell 从旧单元改成替代单元.
6. `draft_grid_edit` 事件写入 SQLite.
7. edit occurrence 使用 `SELF_DRAFT_GRID` substrate.
8. 最终 `commit_reply` 读取修订后的 DraftGrid 文本.

本轮执行:

```text
python -m py_compile apv3test\runtime\phase20_7\runtime.py tests\test_phase20_9r_edit_cell_cstar_alternative.py
PASS

pytest -q tests\test_phase20_9r_edit_cell_cstar_alternative.py -vv
2 passed

$phase209 = Get-ChildItem -Path tests -Filter 'test_phase20_9*.py' | ForEach-Object { $_.FullName }; pytest -q @phase209
57 passed

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
AP 写完草稿 -> 回读一下 -> 直接提交
```

如果草稿中间某一格写错了, AP 没有真正的“看见错误并改一个格子”的能力.

现在:

```text
AP 先学到: phase20.9r edit prompt -> 猫好
下一次 teacher-off 复问
AP 召回 C*/B 期望输出: 猫好
测试故障让 DraftGrid 实际写成: 狗好
AP read_draft 看见: 狗好
C* 仍支持第 0 格应为: 猫
edit_cell 修改第 0 格: 狗 -> 猫
commit_reply 提交: 猫好
```

这更接近人类写字时的过程:

```text
心里知道要写什么 -> 手写错一个字 -> 自己读一遍 -> 改掉那个字 -> 再交出去
```

## 6. 对抗性自审

### 已解决

1. `edit_cell` 已能从候选审计变成真实局部修订行动.
2. 修改依据来自 DraftGrid 回读冲突和当前 C*/B 期望单元, 不是隐藏字符串 fixer.
3. `draft_grid_edit` 进入 ExperienceLog, 且写入 `SELF_DRAFT_GRID` occurrence 和 SSP edge.
4. 修改后 `commit_reply` 读取修改后的 DraftGrid, 没有绕过草稿框.
5. 验收路径采用 teacher-off 复问, 避免把同轮教学文本当答案直通.
6. 红线扫描通过, 未新增关键词路线、答案表、隐藏求解器或 LLM.

### 仍需注意

1. 本阶段证明的是“单 cell 局部修订”, 还不是长回复多处修订.
2. 替代单元目前主要来自当前 `expected_output_chars`, 仍需继续下沉到更完整的 SA 粒度 C* 虚能量竞争.
3. `debug_draftgrid_write_mutation` 只是测试故障注入, 不能被当作正常认知能力.
4. edit 结果已写入 SSP, 但还需要后续让 edit 成功/失败反馈进一步调制未来的读回、继续写、停下和提交.
5. 仍不能声明完整六阶段 runtime、完整范式自学习、L1/L2/L3 在线嵌入、数学列竖式、object-centric 视觉想象或 Phase21 视觉教学泛化闭环完成.

## 7. 下一步

下一步建议 Phase20.9s:

```text
把 edit_cell 的成功/失败结果继续回灌行动竞争与学习闭环.
```

具体是让:

```text
edit_cell -> draft_grid_read -> commit_reply -> reward/punish/self_test
```

产生可追踪的学习 delta, 反过来影响:

```text
read_draft
edit_cell
continue_writing
stop_generating
commit_reply
```

这样 AP 会更像人一样: 写完后是否回看、哪里需要改、改完是否还要再读一遍、什么时候可以提交, 都逐步由经验和 C* 后果预测调制, 而不是固定流程.
