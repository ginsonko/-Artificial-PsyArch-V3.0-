# APV3.0test Phase20.9v ContinueWriting 后继写入验收报告

日期: 2026-06-28

## 1. 设计

Phase20.9v 承接 Phase20.9u:

```text
read_draft 后, edit_cell / commit_reply / read_draft / continue_writing / stop_generating 同台竞争
```

本阶段把 `continue_writing` 从候选 trace 推进成真实行为:

```text
DraftGrid 先写入一个可见片段
read_draft 回读草稿
如果 C*/ExperienceFlow/DraftGrid 仍有未写 successor 单元
continue_writing 在同一套 DraftGrid action competition 中胜出
继续逐格写入后继片段
再次 read_draft
再由 edit / continue / commit / stop 竞争
```

这里没有新增“长回复模块”。未写内容来自本轮已经由 B/C/C*、教师反馈整合或表达范式选择出的 `output_chars`; Phase20.9v 只是让这些虚拟后继单元不再一次性写完, 而是进入 DraftGrid 行动循环。

## 2. 审查完善

### 2.1 AP-native 边界

本阶段没有新增数据库表、答案表、关键词路由、隐藏 solver、学生侧 LLM、专属长回复器或 UI 认知模块。

新增的只是 DraftGrid 写入机械:

```text
_draftgrid_linear_units
_draftgrid_linear_text
_draftgrid_target_output_unit_count
_draftgrid_initial_write_unit_limit
_draftgrid_next_successor_span
```

这些 helper 不产生答案、不选择答案、不绕开 B/C/C*, 只负责把已经存在的 DraftGrid 单元序列按写入位置读出来。

### 2.2 为什么仍使用 Phase20.9p 公式

Phase20.9v 没有新增公式 ID。它继续使用:

```text
apv3_phase20_9p_draftgrid_action_competition_from_ap_flow/v1
```

原因是本阶段不是新的认知实体, 而是让 9p 已有的 `continue_writing` 候选真正参与行动执行。

### 2.3 关键修正

1. `pending_output_unit_count` / `pending_output_ratio` 接入 `_draftgrid_action_drive_context`。
2. 未写 successor 会提高 `continue_writing` 倾向, 并轻微降低重复 `read_draft` 的卡住倾向。
3. `commit_reply` 在仍有 pending successor 时不再 eligible, 避免把半句提交为完成回复。
4. `stop_generating` 仍可胜出, 表示 AP 可以中止草稿, 但不会把未完成草稿泄露成外显回复。
5. DraftGrid 内部比较改用线性写入单元, 保留空格等真实写过的格子; 提交给用户时使用线性文本, 不把网格换行当作外显回复内容。

## 3. 通过落地

修改文件:

```text
apv3test/runtime/phase20_7/runtime.py
tests/test_phase20_9v_continue_writing_successor.py
```

核心行为:

```text
短回复:
  一次写完 -> read_draft -> commit_reply

长回复:
  写第一片段 -> read_draft
  pending successor 仍存在 -> continue_writing 胜出
  写后继片段 -> read_draft
  pending 清空后 -> commit_reply 胜出
```

小白可理解例子:

```text
以前:
AP 心里有一句长话, 一口气写完, 看一眼就说。

现在:
AP 先写“我还不太确定……”
自己读一遍
发现后面还想写“你可以教我”
continue_writing 胜出
继续写后半句
再读一遍
确认没剩下没写的部分后才提交。
```

## 4. 严谨验收测试

新增测试:

```text
tests/test_phase20_9v_continue_writing_successor.py
```

覆盖:

1. `continue_writing` 能从 pending successor units 中胜出。
2. 续写后的后继片段必须再次 `read_draft`, 然后才允许 `commit_reply`。
3. 短回复保持原有单片段路径, 不被强行拆成多段。

执行结果:

```text
python -m py_compile apv3test\runtime\phase20_7\runtime.py tests\test_phase20_9v_continue_writing_successor.py
PASS

pytest -q tests\test_phase20_9v_continue_writing_successor.py -vv
3 passed

$phase209 = Get-ChildItem -Path tests -Filter 'test_phase20_9*.py' | ForEach-Object { $_.FullName }; pytest -q @phase209
67 passed

pytest -q tests\test_phase20_7_stage0...stage8...
48 passed

pytest -q tests\test_phase20_8b...test_phase20_8r...
58 passed

python scripts\red_line_check_v14.py --phase 20.7-stage8
OK: Phase 20.7-stage8 deliverables present
OK: All red line checks pass on runtime/cognitive

python scripts\check_constant_governance.py
OK: Governance check passed (507 numeric constants)
仍有既有 91 个 @experimental constants pending rationale warnings
```

## 5. 对抗性自审

已解决:

1. `continue_writing` 不再只是候选展示, 已经能真实产生 `draft_grid_write` 事件。
2. 长回复不再强制一次性写完, 而是进入写-读-续写-再读-提交循环。
3. pending successor 未清空时不能 `commit_reply`, 避免半成品外显。
4. DraftGrid 多行换行不再污染外显回复文本。
5. 空格作为真实写入单元被保留, 不会触发伪 C* edit 冲突。
6. 没有新增关键词规则、答案捷径、隐藏 solver 或 UI 认知。

仍需保留边界:

1. successor 单元仍主要来自本轮已选出的 `output_chars`; 还不能说已经完全由学习到的 DraftGrid/ExperienceFlow 后继范式自发长出。
2. 这还不是完整范式自学习、L1/L2/L3 在线嵌入、六阶段 runtime 全量完成、数学列竖式或 object-centric 视觉想象。
3. 续写片段大小仍是 DraftGrid 机械执行边界, 不是已经通过经验调参学出的个体化书写节奏。

## 6. 下一步

下一步建议 Phase20.9w:

```text
把 continue_writing 的后继来源从当前 output_chars 进一步接到 ExperienceFlow / DraftGrid successor 片段。
```

目标是让 AP 不只是继续写“已经选好的一整句”, 而是能从回读草稿、短期结构流、C* 残差和已学表达范式中继续长出下一段:

```text
写一段 -> 读回 -> 发现解释还没闭合 -> 召回相邻表达片段 -> 继续写 -> 再读 -> 局部修改/停下/提交
```

这会继续为长回复、范式自学习、多步骤解释和数学竖式逐格书写打基础。
