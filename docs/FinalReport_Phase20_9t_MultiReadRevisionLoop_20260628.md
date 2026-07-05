# APV3.0test Phase20.9t 多次回读-修订循环验收报告

日期: 2026-06-28

## 1. 设计

Phase20.9t 承接 Phase20.9q/9r/9s:

```text
9q: draft_grid_read -> SELF_DRAFT_GRID occurrence/edge
9r: readback conflict -> C* alternative unit -> edit_cell
9s: edit_cell outcome -> learning delta -> action competition
```

本阶段目标是把原来的单次流程:

```text
写 -> 读 -> 改 -> 提交
```

推进为真实跨 tick 的:

```text
写 -> 读 -> 改 -> 再读 -> 必要时再改 -> 再读 -> 提交/停下
```

关键原则:

1. 不新增“编辑器”“纠错器”“答案修复器”等认知实体。
2. 不新增关键词、正则、答案表、字符串替换器、隐藏 solver 或学生侧 LLM。
3. 不直接从 teacher feedback 或 expected text 写最终回复。
4. 每次修订只能来自已有 C* alternative unit。
5. 每次 edit 后必须再次产生真实 `draft_grid_read` 事件和 `SELF_DRAFT_GRID` occurrence/edge。
6. 终止条件来自 AP 主流程: tick 预算、草稿为空、或 C* 不再给出可修订单元。

## 2. 审查完善

### 2.1 为什么不新增 Phase20.9t 公式 ID

本阶段没有引入新的认知机制。它只是把已有机制串成连续流程:

```text
PHASE20_9Q_DRAFTGRID_READBACK_FLOW_ID
PHASE20_9R_EDIT_CELL_ID
PHASE20_9S_EDIT_OUTCOME_ID
```

如果再新增一个“multi-read revision module”式公式, 会让实现看起来像新实体。最终选择不新增公式 ID, 只保留真实事件链:

```text
draft_grid_read
draft_grid_edit
draft_grid_read
draft_grid_commit
```

### 2.2 为什么这是 AP-native

人类写东西时并不是一次性提交, 而是:

```text
写一点 -> 看一眼 -> 发现不顺 -> 改一个地方 -> 再看一眼 -> 顺了才说出去
```

在 AP 中对应:

```text
DraftGrid 写入
SELF_DRAFT_GRID 回读
C* 最小误差比较
edit_cell 局部动作
edit outcome 学习
下一 tick 再回读
commit_reply 行动竞争
```

这不是外部编辑器, 而是 AP 对自身行动后果的感知、归因、修订和再确认。

## 3. 通过落地

修改文件:

```text
apv3test/runtime/phase20_7/runtime.py
tests/test_phase20_9t_multiread_revision_loop.py
```

核心落地:

1. 将 Stage1 文本闭环中的单次 read/edit 改成 `while` 形式的 DraftGrid 回读-修订循环。
2. 每轮先生成真实 `read_draft` action 和 `draft_grid_read` event。
3. 每轮 read 后调用已有 `_select_cstar_alternative_unit_for_draftgrid_edit(...)`。
4. 如果 C* 给出可修订单元, 执行一个 `edit_cell`, 写入 `draft_grid_edit`, 并产生 9s edit outcome learning delta。
5. edit 后回到循环开头, 产生下一次真实 readback。
6. 如果没有可修订单元, 进入 commit。
7. 没有固定“最多改 2 次”的工程硬规则; 由 `turn_tick_budget` 与 C* alternative unit 自然约束。

## 4. 严谨验收测试

新增测试:

```text
tests/test_phase20_9t_multiread_revision_loop.py
```

覆盖:

1. 单格错误:

```text
cat 被测试注入写成 bat
read_draft 读到 bat
edit_cell 把 b 改成 c
read_draft 再读到 cat
commit_reply 提交 cat
```

2. 两格错误:

```text
cat 被测试注入写成 bot
read_draft: bot
edit_cell: b -> c
read_draft: cot
edit_cell: o -> a
read_draft: cat
commit_reply: cat
```

3. 无错误路径:

```text
readback 已经等于 C* 期望
只读一次
不产生 fake edit
不产生 fake extra loop
直接 commit
```

本轮执行结果:

```text
python -m py_compile apv3test\runtime\phase20_7\runtime.py tests\test_phase20_9t_multiread_revision_loop.py
PASS

pytest -q tests\test_phase20_9t_multiread_revision_loop.py -vv
3 passed

$phase209 = Get-ChildItem -Path tests -Filter 'test_phase20_9*.py' | ForEach-Object { $_.FullName }; pytest -q @phase209
61 passed

pytest -q tests\test_phase20_7_stage0...stage8...
48 passed

pytest -q tests\test_phase20_8b...test_phase20_8r...
58 passed

python scripts\red_line_check_v14.py --phase 20.7-stage8
OK: All red line checks pass on runtime/cognitive

python scripts\check_constant_governance.py
OK: Governance check passed (507 numeric constants)
仍有既有 91 个 @experimental constants pending rationale warnings
```

## 5. 小白可理解效果

以前 AP 像这样:

```text
心里想写: cat
草稿误写: bat
看了一眼: bat
改成: cat
立刻提交
```

现在 AP 像这样:

```text
心里想写: cat
草稿误写: bot
看了一眼: bot
觉得第 1 格不对
改 b -> c
再看一眼: cot
觉得第 2 格不对
改 o -> a
再看一眼: cat
这次顺了
提交: cat
```

这更接近人类写字、回看、局部修改、再确认的过程。

## 6. 对抗性自审

### 已解决

1. edit 后不再直接 commit, 而是真实再 readback。
2. 多格错误不会一次性字符串修复, 而是一轮只改一个 C* alternative unit。
3. 无错误路径不会为了展示而假造多次回读。
4. `commit_reply` 仍然读取 `DraftGrid.visible_text()`, 不读取 expected answer。
5. 9s edit outcome carryover 能继续影响后继 read/commit 行动竞争。
6. 未新增数据库表、认知模块、答案表、隐藏 solver 或 LLM。

### 仍需保留边界

1. 这还不是完整长回复写作系统。当前仍主要验证短文本和局部字符修订。
2. 这还不是完整六阶段 runtime, 只是为六阶段里的回读、修订、自测提供底层循环。
3. 这还不是 L1/L2/L3 在线嵌入。
4. 这还不是完整范式自学习。
5. 这还不是数学列竖式。
6. 这还不是 object-centric 视觉想象。
7. 当 tick 预算耗尽时, 当前行为是停止后续 read/commit, 还没有把 `stop_generating` 作为显式被选中事件写出。这应进入下一步。

## 7. 下一步

下一步建议 Phase20.9u:

```text
把 commit_reply / read_draft / edit_cell / continue_writing / stop_generating 的循环终止选择进一步交给行动竞争。
```

也就是当 AP 写完草稿后, 不只是“无冲突就提交”, 而是让它根据:

```text
DraftGrid 完整度
C* 支持度
剩余误差
edit outcome
重复疲劳
未闭合感
tick 预算压力
stop_generating 倾向
```

来决定:

```text
再读一遍 / 再改一下 / 继续写 / 停下 / 提交
```

这会把 Phase20.9t 的流程从“有界真实循环”继续推进到“行动竞争自然选择循环”, 为长回复、范式自学习和后续竖式计算铺路。
