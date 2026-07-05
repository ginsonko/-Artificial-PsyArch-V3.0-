# APV3 Phase7.7 Natural Chinese Expression Stream 最终报告

日期: 2026-06-17
阶段: Phase7.7
状态: 通过

## 1. 设计

Phase7.7 的目标是把 Phase7.4/7.5/7.6 已经验证过的“结构性内省 feeling -> learned expression”链路，从抽象 `expr::*` 探针推进到真实中文短句 token 流。

设计原则:

- 中文短句只作为后天观察到的表达材料进入系统。
- 学生侧 runtime 不解析中文语义，不根据“不确定/请教/不对”等词做路由。
- feeling label 仍是 opaque key，表达召回只读共现统计与 expression phrase 支持度。
- teacher-off replay 中不提供外部表达 token，不预填 candidate pool。
- 回复压力只说明“有回应压力”，不决定“说哪句话”。

为保存短句顺序，新增一个窄模块 `ExpressionPhraseMemory`:

- `CooccurrenceAssociationStore` 负责学习 `feeling_label -> expression_token / phrase_id` 的稀疏关联。
- `ExpressionPhraseMemory` 负责保存某个 `phrase_id` 后天观察到的有序 token 序列与支持度。
- 召回时先由 feeling 通过共现表选出 phrase id，再由短语记忆取回 token 顺序。

这个分工避免把中文短句写成答案表，也避免让 cooccurrence store 承担不属于它的顺序记忆职责。

## 2. 审查完善

吸收 Claude 对 Phase7.7 的建议后，本阶段重点补了 4 类审查:

- 目标中文短句与干扰中文短句同时出现，验证目标 phrase id 通过长期共现胜出。
- 同一目标短句的倒序版本也作为低权重干扰出现，验证系统不是只记住“这些字出现过”，而是在 phrase id + 有序短句记忆上召回。
- SQLite warm-load 后重新构造共现表与短语记忆，验证保存恢复不改变 teacher-off 行为。
- runtime-only 红线扫描确认 runtime 文件中没有 Phase7.7 中文短句、没有旧 `must_reply` 通道、没有 `_most_common_reply` fallback、没有 answer table 或 student-side LLM。

## 3. 通过落地

新增:

- `apv3test/runtime/expression_phrase_memory.py`
- `tests/test_phase7_7_natural_chinese_expression_stream.py`
- `reports/APV3_Phase7_7_NaturalChineseExpressionStream_Showcase_20260617.html`

更新:

- `apv3test/runtime/__init__.py`

核心 teacher-off trace:

```text
dialogue_uncertain        feeling::draft::proto_0 -> 我还不确定       target=2.9967 best_other=0.3996
work_memory_unfinished   feeling::draft::proto_1 -> 我先记着         target=2.9967 best_other=0.3330
teacher_request_pressure feeling::draft::proto_2 -> 我想请教一下     target=4.4951 best_other=0.3330
recent_punishment        feeling::draft::proto_3 -> 这里不太对       target=3.7459 best_other=0.2664
rewarded_flow            feeling::draft::proto_4 -> 这样就顺了       target=3.7459 best_other=0.2664
```

结构证据:

- stable feeling prototypes: 5
- expression phrase records: 10
- token association pairs: 46
- paradigm association pairs: 15

## 4. 严谨验收测试

已执行:

```text
python -m pytest APV3.0test\tests\test_phase7_7_natural_chinese_expression_stream.py -q
python -m pytest APV3.0test\tests\test_phase7_0_teacher_off_three_stage_milestone.py ... APV3.0test\tests\test_phase7_7_natural_chinese_expression_stream.py -q
python -m pytest APV3.0test\tests -q
python -m compileall APV3.0test\apv3test APV3.0test\tests -q
rg -n "我还不确定|我先记着|我想请教一下|这里不太对|这样就顺了|phase7_7_|must_reply|undecidable_feeling_tokens|feeling::undecidable|find_by_cue_token|_most_common_reply|pressure_type_weights|student_side_llm|answer_table|LLM policy" APV3.0test\apv3test\runtime
```

结果:

- Phase7.7 targeted: `5 passed`
- Phase7.0-7.7 combined regression: `57 passed`
- Full suite: `230 passed`
- Compileall: passed
- Runtime redline scan: no matches

## 5. 最终汇总

Phase7.7 证明了:

- APV3.0test 可以把结构性内省 feeling 与真实中文短句 token 流建立后天关联。
- teacher-off 时，系统能从同类结构状态中召回对应中文表达序列。
- 召回依赖 AP-native 共现统计与短语支持度，不依赖中文关键词规则、答案表、LLM policy 或测试预填。
- 干扰短句与倒序短句存在时，目标短句仍稳定胜出。
- SQLite warm-load 后，中文表达召回行为保持一致。

仍不能宣称:

- 完整开放中文自由对话底座已经完成。
- 自然长对话风格、跨模态表达学习、10G 级长期遗忘/淘汰机制已经完成。
- 系统已经能自己发明所有中文表达；本阶段证明的是“观察到表达后，能通过 AP-native evidence 学会在相似结构态下召回”。

下一步建议 Phase7.8 / Phase8.0:

- 把自然中文表达流接入最小逐 token dialogue action，验证短句召回后可以进入动作竞争与提交链路。
- 继续扩展自然 episode，但保持 teacher-off、无答案表、无中文路由的验收门。
