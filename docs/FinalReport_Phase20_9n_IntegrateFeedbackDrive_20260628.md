# APV3.0test Phase20.9n integrate_feedback 行动 drive 下沉验收报告

日期: 2026-06-28

## 1. 设计

Phase20.9m 已经把固定反馈确认表达降成低优先级先天种子。Phase20.9n 继续处理下一处硬点:

```text
integrate_feedback 行动本身仍有固定高 drive:
  competition row: 0.9 if selected else 0.05
  DraftGrid write drive: 0.86
```

本阶段目标不是新增"确认意图模块", 而是让已有 `integrate_feedback` 行动从 AP 主流程中的真实信号得到驱动力:

```text
teacher_feedback 证据
+ 奖惩强度
+ 是否能归因到当前/近期对象
+ 学习闭环 feedback-only 倾向
+ 后天学到的确认表达 readiness
- 重复确认疲劳
- 冲突/低把握惩罚
-> integrate_feedback drive
```

该 drive 只调制行动竞争, 不生成答案, 不绕过 DraftGrid。

## 2. 审查完善

### 2.1 为什么不新增实体

`integrate_feedback` 已经是当前 runtime 的行动类型。Phase20.9n 只替换它的 drive 计算方式, 等价于把固定参数换成可审计公式。

没有新增:

- 反馈确认模块.
- 外显意图竞争器.
- 中文关键词判断.
- 答案表.
- UI 认知旁路.

### 2.2 人类类比

人收到明确教学或纠正时, 通常会出现"吸收/确认/记住"的行动倾向。但这个倾向不是恒定的:

- 对方真的给了清楚反馈, 倾向更强.
- 反馈带奖励或惩罚, 倾向更强.
- 能知道这条反馈指向刚才哪个对象, 倾向更稳定.
- 刚学过怎么确认, 表达更自然.
- 连续重复确认太多次, 表达会疲劳, 不再每次都同样强烈.

Phase20.9n 把这些都压回同一条 AP 信息流。

## 3. 通过落地

修改文件:

```text
apv3test/runtime/phase20_7/runtime.py
```

新增公式:

```text
PHASE20_9N_FEEDBACK_DRIVE_ID =
  apv3_phase20_9n_integrate_feedback_drive_from_ap_flow/v1
```

新增函数:

```text
_integrate_feedback_drive_context(...)
_recent_committed_intent_count(...)
```

注意: 这些不是认知新实体, 只是行动竞争公式和经验流统计。近期反馈次数从 `draft_grid_commit.source_intent == integrate_feedback` 统计, 以统一经验流作为真相源。

关键 trace:

```text
integrate_feedback_drive_from_ap_flow:
  formula_id
  drive
  feedback_evidence
  target_grasp
  value_signal
  learning_loop_support
  learned_expression
  expression_readiness
  recent_feedback_actions
  repeated_expression_count
  repetition_fatigue
  conflict_penalty
  writes_answer_directly = false
  creates_reply_candidate = false
```

## 4. 严谨验收测试

新增测试:

```text
tests/test_phase20_9n_integrate_feedback_drive.py
```

定向与相邻回归:

```text
python -m pytest \
  tests\test_phase20_9n_integrate_feedback_drive.py \
  tests\test_phase20_9b_learning_protocol_drive_modulation.py \
  tests\test_phase20_9c_learning_loop_metrics.py \
  tests\test_phase20_9m_fallback_expression_seedification.py -q

结果: 13 passed
```

Phase20 分段回归:

```text
Phase20.1-4: 17 passed
Phase20.5-6 history/workbench: 10 passed
Phase20.6 runtime/workbench: 24 passed
Phase20.7: 48 passed
Phase20.8: 58 passed
Phase20.9 + open_dialogue_foundation: 51 passed
合计: 208 passed
```

红线与治理:

```text
python scripts\red_line_check_v14.py --phase 20.7-stage8
结果: OK

python scripts\check_constant_governance.py
结果: OK, 仍有既有 91 个 @experimental constants pending rationale

python scripts\verify_phase20_7_release_demo.py
结果: OK
```

小白可理解展示:

```text
1. 冷启动教学确认:
   reply = 嗯,记下了。
   base_drive = 0.6244
   final_drive = 0.7695
   learned_expression = false
   expression_readiness = 0.0
   fatigue = 0.0

2. 教过"好,我记住啦"后:
   reply = 好,我记住啦
   base_drive = 0.7494
   final_drive = 0.8945
   learned_expression = true
   expression_readiness = 0.22
   fatigue = 0.095

3. 重复确认后:
   reply = 好,我记住啦
   base_drive = 0.6794
   final_drive = 0.8245
   learned_expression = true
   expression_readiness = 0.22
   fatigue = 0.165
```

含义:

```text
学会确认表达后, drive 上升;
连续重复后, fatigue 上升, drive 回落;
C*/learning carryover 仍可在基础 drive 之上继续调制最终竞争值.
```

## 5. 对抗性自审

### 5.1 已解决

- 删除了 `integrate_feedback` 的固定高 drive 路径.
- `write_cell` 的反馈整合 drive 不再返回固定 `0.86`.
- 行动竞争 trace 能看到基础 drive、学习回灌、C* 回灌.
- 重复疲劳来自经验流 commit, 不是中文文本判断.
- 学过确认表达后的表达 readiness 能影响 drive.

### 5.2 仍需注意

当前 teacher_feedback 一旦进入 turn, 仍然会产生 `integrate_feedback` 选中行动。Phase20.9n 只硬化"选中后的 drive 和写入强度", 还没有实现"面对低信任/强冲突教师反馈时是否拒绝整合"。这需要 source_trust、反例记忆、关系/身份稳定性和奖惩后果进一步进入行动竞争后再做。

## 6. 边界

本阶段可以证明:

- `integrate_feedback` drive 已从固定常数下沉为 AP-native 可审计公式.
- 反馈确认强度会随反馈证据、奖惩、目标归因、学习倾向、表达经验和疲劳变化.
- 公式不生成答案, 不写答案表, 不绕过 DraftGrid.

仍不能声明:

- 完整 L1/L2/L3 在线嵌入完成.
- 完整六阶段学习 runtime 完成.
- 完整范式自学习完成.
- 数学列竖式完成.
- object-centric 视觉想象完成.
- Phase21 视觉教学泛化闭环完成.

## 7. 下一步

下一步建议进入 Phase20.9o:

```text
把 commit_reply 的固定高 drive 继续下沉.
```

目前 `commit_reply` 仍有固定 `0.95`。更 AP-native 的做法是让提交动作读取:

```text
DraftGrid 完整度
+ B/C/C* 对草稿后果的支持
+ 当前回复压力
+ 奖惩预测
+ 重复疲劳
+ 是否仍有未闭合/冲突
-> commit_reply drive
```

这会继续减少"一写完就机械提交"的感觉, 也为后续竖式数学、长草稿、多步修订和更像人的犹豫/删改打基础.

