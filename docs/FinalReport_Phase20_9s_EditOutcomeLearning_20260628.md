# APV3.0test Phase20.9s edit_cell 后果学习回灌验收报告

日期: 2026-06-28

## 1. 设计

Phase20.9s 承接 Phase20.9r:

```text
readback conflict -> C* alternative unit -> edit_cell 真局部修订
```

本阶段目标是继续打通:

```text
edit_cell -> edit outcome -> learning delta -> action competition
```

也就是让 AP 不只会“改一个格子”, 还要能把这次修改的后果带入下一 tick 的行动竞争:

```text
read_draft
edit_cell
continue_writing
stop_generating
commit_reply
```

核心约束:

1. 不新增“编辑学习器”实体.
2. 不把 edit 结果写成答案表.
3. 不使用字符串 fixer、关键词规则、正则修复器、hidden solver 或 LLM.
4. 只从 DraftGrid visible_text 与 C*/B 期望单元之间的拟合变化产生学习信号.

## 2. 审查完善

### 2.1 为什么 edit outcome 是 AP-native

白皮书要求每 tick 都有预测、回读、最小误差和行动反馈. `edit_cell` 后的可见草稿就是 AP 自己行动后的现实读回, 所以它可以形成:

```text
fit_before = similarity(编辑前草稿, C* 期望)
fit_after  = similarity(编辑后草稿, C* 期望)
fit_improvement = fit_after - fit_before
remaining_error = 1 - fit_after
```

这不是外部模块判断“对不对”, 而是 AP 内部的最小误差变化.

### 2.2 为什么不新增实体

本阶段只新增一个公式 ID:

```text
PHASE20_9S_EDIT_OUTCOME_ID
```

它不是模块、表、旁路或候选答案系统. 它只是 `learning_deltas` 中的一类 action outcome trace, 然后通过既有:

```text
_learning_loop_carryover_from_events
_apply_learning_loop_carryover_to_competition
```

合流到现有行动竞争.

## 3. 通过落地

修改文件:

```text
apv3test/runtime/phase20_7/runtime.py
tests/test_phase20_9s_edit_outcome_learning.py
```

新增公式:

```text
PHASE20_9S_EDIT_OUTCOME_ID =
  apv3_phase20_9s_edit_outcome_learning_carryover/v1
```

新增 trace:

```text
draftgrid_edit_outcome_learning:
  fit_before
  fit_after
  fit_improvement
  remaining_error
  verification_need
  edit_success
  source_support
  subjective = true
  may_be_wrong = true
  writes_answer_directly = false
  creates_reply_candidate = false

edit_outcome_carryover:
  read_draft_delta
  edit_cell_delta
  commit_reply_delta
  write_cell_delta
  stop_generating_delta
  idle_think_delta
```

落地行为:

1. `edit_cell` 执行后计算编辑前后草稿与 C*/B 期望输出的拟合变化.
2. 生成 `draftgrid_edit_outcome_learning` delta.
3. 下一 tick 的 carryover 合流 9e 学习阶段、9q 奖惩归因和 9s edit outcome.
4. `commit_reply`、`read_draft`、`edit_cell` 等行动竞争行能看到 `edit_outcome_carryover`.
5. `commit_reply` 使用 edit 后的 DraftGrid 上下文, 不再拿 edit 前的旧 draft action context.

## 4. 严谨验收测试

新增测试:

```text
tests/test_phase20_9s_edit_outcome_learning.py
```

覆盖:

1. 先教学形成经验.
2. teacher-off 复问召回 C*/B 输出.
3. 测试故障注入让 DraftGrid 写错一格.
4. `edit_cell` 改正该格.
5. edit tick 产生 `draftgrid_edit_outcome_learning` delta.
6. `fit_after > fit_before`.
7. `commit_reply` 行动竞争读取 `edit_outcome_carryover`.
8. `read_draft` 和 `edit_cell` 行动候选也能看到同一个 edit outcome carryover.
9. 最终提交的是修订后的 DraftGrid 文本.

本轮执行:

```text
python -m py_compile apv3test\runtime\phase20_7\runtime.py tests\test_phase20_9s_edit_outcome_learning.py
PASS

pytest -q tests\test_phase20_9s_edit_outcome_learning.py -vv
1 passed

$phase209 = Get-ChildItem -Path tests -Filter 'test_phase20_9*.py' | ForEach-Object { $_.FullName }; pytest -q @phase209
58 passed

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
AP 会改: 狗好 -> 猫好
但这次“改得怎么样”还没有进入下一步行动判断.
```

现在:

```text
AP 心里期望: 猫好
DraftGrid 写错: 狗好
AP 回读后改成: 猫好
AP 比较改前/改后:
  改前更不像“猫好”
  改后更像“猫好”
于是下一 tick:
  commit_reply 更有把握
  read_draft / edit_cell 仍保留可审计倾向
  stop_generating 因成功修订而下降
```

这更像人类写作:

```text
我写错了一个字 -> 我改了 -> 我看起来顺了 -> 我更敢交出去
```

如果改完仍不像预期, AP 会保留 remaining_error, 后续更倾向再读、再改或停下.

## 6. 对抗性自审

### 已解决

1. `edit_cell` 的后果已能进入 `learning_deltas`.
2. edit outcome 已通过现有 carryover 进入行动竞争, 没有新增行动实体.
3. `commit_reply` 已能读取 edit outcome 的正向调制.
4. `read_draft` / `edit_cell` 也能看到同一 edit outcome carryover.
5. 红线扫描通过, 未新增关键词路线、答案表、隐藏求解器或 LLM.
6. 本轮删除了临时残留的 dead helper, 避免无用实体污染主流程.

### 仍需注意

1. 当前 edit outcome 仍是单 tick 单 cell 级, 不是长回复多处修订.
2. `fit_before/fit_after` 目前是字符位置拟合, 还不是完整 SA 能量场级最小误差.
3. 还没有把 edit outcome 持久化为长期 L3 行动后果嵌入.
4. 还不能声明完整范式自学习、完整六阶段 runtime、数学列竖式、object-centric 视觉想象或 Phase21 视觉教学泛化闭环完成.

## 7. 下一步

下一步建议 Phase20.9t:

```text
让 read_draft / edit_cell / commit_reply 形成多次回读-修订循环.
```

也就是从:

```text
写 -> 读 -> 改 -> 提交
```

推进到:

```text
写 -> 读 -> 改 -> 再读 -> 必要时再改 -> 提交/停下
```

这一步是长回复、范式自学习和后续数学竖式计算的直接前置能力.
