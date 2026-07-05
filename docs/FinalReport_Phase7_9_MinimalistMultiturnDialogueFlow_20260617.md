# APV3 Phase7.9 Minimalist Multiturn Dialogue Flow 最终报告

日期: 2026-06-17
阶段: Phase7.9
状态: 通过

## 1. 设计

Phase7.9 的目标是在 Phase7.8 的极简中文表达底座上，推进到多轮连续对话流。

每一轮遵循同一条 AP-native 链路:

```text
incoming_external_query
-> 当前结构态 views
-> draft introspection feeling
-> 后天观察到的用户/环境短句共现学习
-> feeling -> phrase_id 召回
-> ExpressionPhraseMemory 恢复 token 序列
-> style gate
-> commit trace
-> 下一轮 reward/punish 作用于上一轮 committed phrase
```

本阶段刻意不做 Web UI，也不做大规模自由对话。目标是验证“多轮状态 carry + 后天观察学习 + 奖惩改变下一轮 + 话题切换不污染 + 持久化恢复”等基础闭环。

## 2. 审查完善

实现时守住 5 条约束:

- 多轮不是脚本串场: runtime 不读取 `incoming_external_query == ...` 或 `case_name == ...` 做路由。
- 后天学习不是教学协议特权: 测试中的表达观察默认走 `perception_other`，不是 LLM policy。
- 奖惩不生成新句子: feedback 只调整上一轮已提交 phrase 的支持度。
- 话题切换不污染: 当前轮 feeling 仍由当前结构态产生，不复用上一轮 feeling。
- 输出继续经过 Phase7.8 的 `style_safe_tokens()`，保持极简风格红线。

## 3. 通过落地

新增:

- `apv3test/runtime/minimalist_dialogue_flow.py`
- `tests/test_phase7_9_minimalist_multiturn_dialogue_flow.py`
- `docs/FinalReport_Phase7_9_MinimalistMultiturnDialogueFlow_20260617.md`
- `reports/APV3_Phase7_9_MinimalistMultiturnDialogueFlow_Showcase_20260617.html`

更新:

- `apv3test/runtime/expression_phrase_memory.py`
- `apv3test/runtime/__init__.py`

实际 trace:

```text
1 feeling::draft::proto_0 p:resp:dunno   p:resp:dunno   不知道 feedback_target=-
2 feeling::draft::proto_0 -              p:resp:dunno   不知道 feedback_target=p:resp:dunno
3 feeling::draft::proto_0 p:resp:cantyet p:resp:cantyet 还不会 feedback_target=p:resp:dunno
4 feeling::draft::proto_0 -              p:resp:cantyet 还不会 feedback_target=p:resp:cantyet
5 feeling::draft::proto_1 p:ack:yes      p:ack:yes      嗯     feedback_target=p:resp:cantyet
6 feeling::draft::proto_1 -              p:ack:yes      嗯     feedback_target=p:ack:yes
7 feeling::draft::proto_2 p:request:help p:request:help 教教   feedback_target=p:ack:yes
8 feeling::draft::proto_2 -              p:request:help 教教   feedback_target=p:request:help
```

这段 trace 说明:

- 观察到“不知道”后，同类不确定 feeling 能 teacher-off 复用。
- 上一轮被惩罚后，系统转向后天观察到的“还不会”。
- 切到不同结构态后，不再被“不知道/还不会”污染，而是召回“嗯”。
- 请求结构态后天学到“教教”，下一轮 teacher-off 复用。

## 4. 严谨验收测试

已执行:

```text
python -m pytest APV3.0test\tests\test_phase7_9_minimalist_multiturn_dialogue_flow.py -q
python -m pytest APV3.0test\tests\test_phase7_8_minimalist_expression_corpus.py APV3.0test\tests\test_phase7_9_minimalist_multiturn_dialogue_flow.py -q
python -m pytest APV3.0test\tests\test_phase7_0_teacher_off_three_stage_milestone.py ... APV3.0test\tests\test_phase7_9_minimalist_multiturn_dialogue_flow.py -q
python -m pytest APV3.0test\tests -q
python -m compileall APV3.0test\apv3test APV3.0test\tests -q
rg -n "phase7_9_|incoming_external_query ==|case_name ==|answer_table|student_side_llm|_most_common_reply|must_reply|if record\.phrase_kind|phrase_kind ==" APV3.0test\apv3test\runtime
```

结果:

- Phase7.9 targeted: `6 passed`
- Phase7.8-7.9 combined: `15 passed`
- Phase7.0-7.9 combined regression: `72 passed`
- Full suite: `245 passed`
- Compileall: passed
- Runtime redline scan: no matches

## 5. 最终汇总

Phase7.9 证明了:

- 极简表达底座可以进入多轮连续对话流。
- 后天观察到的用户/环境短句可以在后续 teacher-off 轮次被召回。
- 惩罚上一轮输出后，下一轮同结构态的表达会发生改变。
- 话题/结构切换后，上一轮强 feeling 不会污染当前轮。
- SQLite 中途保存恢复后，多轮输出序列保持等价。

仍不能宣称:

- 完整开放中文自由对话底座已经完成。
- 同一 feeling 在不同 context 下的细粒度风格条件化已经完成。
- 系统已经能无限扩展词库或自动创造稳定新短语。
- Web UI、真实用户长程互动、跨模态自然输入都已完成。

下一步建议 Phase7.10:

- 做 context 条件化表达: 同一 feeling + 不同 context -> 不同 phrase。
- 例如熟悉场景偏 `嗯/好/不知道`，正式或权威场景偏 `好的/不确定/请再说`。
- 继续保持 phrase_kind 仅 metadata，context 作为 SA/状态证据进入共现，不做关键词路由。
