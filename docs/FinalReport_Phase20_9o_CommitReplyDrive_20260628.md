# APV3.0test Phase20.9o commit_reply drive 下沉验收报告

日期: 2026-06-28

## 1. 设计

Phase20.9n 已经把 `integrate_feedback` 的固定高 drive 下沉到 AP 主流程。Phase20.9o 继续处理下一个硬点:

```text
commit_reply 原先在主对话提交路径中固定为 0.95
```

这会让 AP 像“写完就必然提交”的流水线，而不是像人一样在草稿、把握感、奖惩预期、未闭合压力、重复疲劳和当前社交/教学压力之间竞争。

本阶段目标不是新增“提交模块”，而是让已有的 `commit_reply` 行动候选读取 AP 主流程中的信号:

```text
DraftGrid 可见草稿
+ B/C/C* 支持
+ 教师请求/未闭合/反馈整合压力
+ 后天表达经验
+ 学习闭环 carryover
- 低把握/未闭合冲突
- 近期重复提交疲劳
-> commit_reply drive
```

提交 drive 只决定“要不要把 DraftGrid 已经写出的内容外显提交”，不生成回复候选，不绕过 DraftGrid，不写答案表。

## 2. 审查完善

### 2.1 与 AP 白皮书的一致性

白皮书和冷保存标准要求:

```text
感受器 -> 状态池 -> SSP/ExperienceFlow -> B/C/C* -> 认知感受 -> 行动竞争 -> DraftGrid/行动器 -> 经验流
```

`commit_reply` 是行动竞争的一员。它不应该由草稿长度或固定常数决定，而应由认知场中的支持、压力、冲突和后果预测共同塑形。

本阶段没有新增:

- 专属提交模块。
- 提交意图实体。
- 关键词/正则路由。
- 答案表。
- 整句宏。
- UI 决策旁路。

新增的是一个可审计公式函数和经验流统计 helper，属于已有行动竞争的数学硬化。

### 2.2 人类类比

人写完一句话后，不是机械地立刻发送。常见过程是:

- 草稿已经完整，发送倾向变强。
- 如果自己很确定，发送倾向变强。
- 如果只是低把握猜测，发送倾向下降，可能改成“我不确定”或问人。
- 如果刚刚被奖励过类似表达，会更敢发。
- 如果同一句已经重复发过很多次，会产生疲劳，不再那么想重复。
- 如果对方在教学或等待确认，提交确认的压力会变强。

Phase20.9o 把这些压回同一套 AP 信号，而不是写成单独的“发送规则”。

## 3. 通过落地

修改文件:

```text
apv3test/runtime/phase20_7/runtime.py
tests/test_phase20_9o_commit_reply_drive.py
```

新增公式标识:

```text
PHASE20_9O_COMMIT_DRIVE_ID =
  apv3_phase20_9o_commit_reply_drive_from_ap_flow/v1
```

新增/扩展关键函数:

```text
_commit_reply_drive_context(...)
_recent_committed_text_hash_count(...)
_competition(..., commit_drive_context=...)
_feelings_for_output(..., commit_drive_context=...)
```

关键 trace:

```text
commit_reply_drive_from_ap_flow:
  formula_id
  drive
  draft_has_visible_text
  draft_completeness
  source_kind
  source_support
  reply_pressure
  expression_support
  learning_loop_support
  low_grasp
  unclosed_pull
  conflict_penalty
  recent_commit_count
  repeated_reply_count
  repetition_fatigue
  writes_answer_directly = false
  creates_reply_candidate = false
```

## 4. 严谨验收测试

新增测试:

```text
tests/test_phase20_9o_commit_reply_drive.py
```

覆盖三件事:

1. `commit_reply` 不再是固定 `0.95`，而是有 `commit_reply_drive_from_ap_flow` trace。
2. “没错,你好聪明 -> 你好聪明”的结构泛化能提高 `source_support`，提交倾向读取结构召回。
3. 重复同一句提交会累积 `repetition_fatigue`，不是无限机械重复。

本轮执行结果:

```text
python -m py_compile apv3test\runtime\phase20_7\runtime.py
PASS

pytest -q tests\test_phase20_9o_commit_reply_drive.py
3 passed

pytest -q tests\test_phase20_9n_integrate_feedback_drive.py \
          tests\test_phase20_9m_fallback_expression_seedification.py \
          tests\test_phase20_9j_structural_generalization_value_modulation.py \
          tests\test_phase20_9k_outward_speech_action_competition.py
13 passed
```

Phase20 分段回归:

```text
Phase20.1-5: 24 passed
Phase20.6: 27 passed
Phase20 open_dialogue_foundation: 6 passed
Phase20.7: 48 passed
Phase20.8: 58 passed
Phase20.9: 48 passed
合计: 211 passed
```

红线与发布包检查:

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

### 5.1 教学反馈场景

输入:

```text
用户: phase20.9o prompt
教学: phase20.9o reply
```

AP 写出:

```text
嗯,记下了。
```

提交时 trace 显示:

```text
base commit drive = 0.2918
learning_loop carryover 后 = 0.3459
C* carryover 后 = 0.3805
```

含义:

```text
AP 不是因为固定 0.95 才提交。
它先因为 DraftGrid 有草稿、反馈整合有压力而有提交倾向，
再被学习闭环和 C* 轻微增强。
```

### 5.2 泛化场景

先教:

```text
用户: 没错,你好聪明
教学: 谢谢
```

再问:

```text
用户: 你好聪明
```

AP 回复:

```text
谢谢
```

提交 trace 显示:

```text
source_kind = structural_bccstar
source_support = 1.0
commit drive = 0.4452
```

含义:

```text
AP 不是查“你好聪明 -> 谢谢”的答案表。
它通过结构相似召回“没错,你好聪明”的经验，
再由奖惩和结构支持提高写草稿与提交的倾向。
```

### 5.3 重复疲劳场景

连续三次同类教学确认:

```text
第 1 次 repetition_fatigue = 0.000
第 2 次 repetition_fatigue = 0.077
第 3 次 repetition_fatigue = 0.154
```

含义:

```text
同一句确认反复出现后，AP 会逐步出现“别老重复”的疲劳因子。
这不是硬编码中文句子，而是经验流中的重复提交统计。
```

## 6. 对抗性自审

### 已解决

- 主对话路径中 `commit_reply` 的 `0.95` 固定高 drive 已移除。
- `commit_reply` 竞争行有可审计的 AP-flow trace。
- `feelings` 中新增 `commit_readiness`，来源为同一个提交 drive context。
- 结构泛化后的提交倾向读取 B/C/C* 支持，不是答题表。
- 重复疲劳来自经验流 `draft_grid_commit` 统计。

### 仍需注意

- `stop_generating` 仍是较固定的低权候选，后续应继续下沉。
- `write_cell` 虽已部分读取 recall state，但 DraftGrid 的长草稿、回读、修改、犹豫还不完整。
- idle outward speech 路径中的 `commit_reply` 仍有 `max(0.50, outward_drive)`，虽然它来自 outward candidate，但后续也应统一到 commit readiness 公式。
- 仍不能声明完整 L1/L2/L3 在线嵌入、完整六阶段 runtime、完整范式自学习、数学列竖式、object-centric 视觉想象或 Phase21 视觉教学泛化闭环完成。

## 7. 下一步

下一步建议进入 Phase20.9p:

```text
把 stop_generating / continue_writing / read_draft / edit_cell 的固定倾向继续下沉，
让 DraftGrid 形成更像人的“写一点、看一眼、犹豫、修改、再提交”的动作循环。
```

原因:

```text
现在 commit_reply 已经更 AP-native，但 AP 仍然偏“一次写完再提交”。
要支持更强泛化、长回复和未来竖式计算，必须让 DraftGrid 回看与修改成为真实行动竞争的一部分。
```
