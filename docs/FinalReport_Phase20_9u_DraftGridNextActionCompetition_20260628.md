# APV3.0test Phase20.9u DraftGrid 下一步行动竞争验收报告

日期: 2026-06-28

## 1. 设计

Phase20.9u 承接 Phase20.9t:

```text
写 -> 读 -> 改 -> 再读 -> 必要时再改 -> 再读 -> 提交
```

本阶段继续推进为:

```text
读回草稿后, read_draft / edit_cell / continue_writing / stop_generating / commit_reply 同台竞争
```

目标不是新增一个“提交判断器”, 而是让已有行动候选在同一套 AP 流中决定下一步:

```text
如果 C* alternative unit 强 -> edit_cell
如果提交把握更强 -> commit_reply
如果仍需要确认 -> read_draft
如果重复疲劳 / 停止倾向更强 -> stop_generating
如果还有未写单元 -> continue_writing
```

## 2. 审查完善

### 2.1 不新增认知实体

本阶段没有新增数据库表、认知模块、答案表、字符串修复器、hidden solver 或学生侧 LLM。

新增的代码辅助函数只是把已有候选动作的 drive 统一读出来:

```text
_select_draftgrid_next_action_from_ap_flow
_draftgrid_context_with_next_action_selection
_commit_context_with_next_action_selection
```

它们不产生答案、不修改 B/C/C* 候选、不读取 teacher feedback 作为回复, 只形成可审计的行动竞争 trace。

### 2.2 为什么不新增 Phase20.9u 公式 ID

Phase20.9u 仍属于既有:

```text
PHASE20_9P_DRAFTGRID_ACTION_ID
```

它只是把 9p 中已有的 DraftGrid action competition 从展示推进到真实决策, 不应包装成一个新认知实体。

### 2.3 stop_generating 的边界

`stop_generating` 不提交空回复, 也不把内部草稿当作外显回复。

当它被选中时:

```text
RuntimeTickEvent 记录 stop_generating
ExperienceLog 写 draft_grid_stop
DraftGrid 草稿仍在 tick trace 可审计
Phase207TurnResult.committed = False
Phase207TurnResult.reply_text = ""
```

这符合白皮书中的“主动停是行动竞争结果, 不是空提交”。

## 3. 通过落地

修改文件:

```text
apv3test/runtime/phase20_7/runtime.py
tests/test_phase20_9u_draftgrid_next_action_competition.py
```

核心行为:

1. 每次 `read_draft` 后, 生成 `draftgrid_next_action_selection`。
2. `edit_cell` 必须在 C* alternative unit 存在且 drive 胜出时才执行。
3. `commit_reply` 必须在下一步行动竞争中胜出才提交。
4. `stop_generating` 能在重复疲劳、停止倾向较高时胜出, 并写入 `draft_grid_stop`。
5. `continue_writing` 当前只有在仍有未写输出单元时才 eligible, 不会凭空续写。
6. 未提交的 turn 返回空 `reply_text`, 内部草稿只留在 tick trace。
7. 9b 的请求冷却修正为同时读取最近 action 与未闭合对象 attempt_count, 避免多 tick DraftGrid 循环把旧请求挤出短窗口后误判为“从没问过”。

## 4. 严谨验收测试

新增:

```text
tests/test_phase20_9u_draftgrid_next_action_competition.py
```

覆盖:

1. **commit 不是默认动作**

```text
先教学: prompt -> cat
再 teacher-off 输入 prompt
read_draft 后产生 candidate_rows
commit_reply 胜出后才提交 cat
```

2. **edit 能先于 commit 胜出**

```text
内部期望 cat
测试注入草稿 bat
read_draft 后 edit_cell 胜出
edit b -> c
再 read
commit_reply 胜出后提交 cat
```

3. **stop_generating 能胜出且不外显草稿**

```text
多次重复相同回复后
repetition_fatigue 提高 stop_generating drive
stop_generating 胜出
committed = false
reply_text = ""
草稿仍留在 tick trace 中
```

执行结果:

```text
python -m py_compile apv3test\runtime\phase20_7\runtime.py tests\test_phase20_9u_draftgrid_next_action_competition.py
PASS

pytest -q tests\test_phase20_9u_draftgrid_next_action_competition.py -vv
3 passed

$phase209 = Get-ChildItem -Path tests -Filter 'test_phase20_9*.py' | ForEach-Object { $_.FullName }; pytest -q @phase209
64 passed

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

以前:

```text
AP 写完草稿
看一眼没错
几乎必然说出口
```

现在:

```text
AP 写完草稿
看一眼
脑内同时冒出几个动作:
  要不要再看一眼?
  要不要改一个字?
  要不要直接说?
  要不要停下不说?
哪一个 drive 更高, 哪一个就赢
```

比如重复说过很多次同一句时, 它可以在心里有草稿但选择不说出口。这比“有答案就机械回复”更像人。

## 6. 对抗性自审

### 已解决

1. `commit_reply` 不再是 read/edit 之后的固定默认终点。
2. `edit_cell` 和 `commit_reply` 能真实竞争; 有 C* 局部冲突时 edit 先赢。
3. `stop_generating` 已经能作为 RuntimeTickEvent 被真实选中。
4. stop 后不会把内部草稿泄露成外显 reply。
5. 9b 请求冷却不再被多 tick DraftGrid 循环挤出窗口影响。
6. 未新增回答捷径、关键词路由、答案表、隐藏 solver 或 LLM。

### 仍需保留边界

1. `continue_writing` 还没有真正接入“长回复未写后继单元”的 runtime; 当前只作为 eligible gating 保留。
2. 当前 stop 的主要来源是重复疲劳、低支持和读回疲劳, 还不是完整的“任务完成/认知压力释放”模型。
3. 这仍不是完整范式自学习、L1/L2/L3 在线嵌入、数学列竖式或 object-centric 视觉想象。
4. 下一阶段若要支持长回复, 必须让 `continue_writing` 从 ExperienceFlow/DraftGrid successor 中真实长出后继片段, 不能写模板。

## 7. 下一步

下一步建议 Phase20.9v:

```text
把 continue_writing 从候选 trace 推进到真实长回复后继写入。
```

具体方向:

```text
read_draft -> C*/ExperienceFlow 发现仍有未写 successor
continue_writing 胜出
DraftGrid 追加后继片段
再 read_draft
再由 edit/continue/commit/stop 竞争
```

这一步会直接为:

```text
长回复
范式自学习
多步骤解释
数学竖式逐格书写
```

打底。
