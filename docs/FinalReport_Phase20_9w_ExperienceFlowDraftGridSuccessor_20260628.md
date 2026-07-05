# APV3.0test Phase20.9w ExperienceFlow / DraftGrid 后继片段验收报告

日期: 2026-06-28

## 1. 设计

Phase20.9w 承接 Phase20.9v:

```text
9v: continue_writing 可以把本轮已经选出的 output_chars 后继写完。
9w: continue_writing 的后继来源进一步接到 ExperienceFlow / SSP / DraftGrid readback successor。
```

本阶段目标不是新增“长回复模块”, 而是让 AP 在读回草稿后, 能从统一短期结构流里召回历史上相似 DraftGrid 读回之后曾经继续写出的片段:

```text
写出片段 A -> read_draft
ExperienceFlow 召回: 历史上 A 后面接过 A+B
C*/行动竞争看到仍有后继压力
continue_writing 继续写 B
再 read_draft
再由 edit / continue / stop / commit 竞争
```

这符合白皮书里的统一经验流、短期结构池、C*/最小误差和 DraftGrid 行动竞争路径。没有新增认知实体, 没有 UI 旁路, 没有答案表, 没有关键词路由, 没有 solver。

## 2. 审查完善

### 2.1 AP-native 边界

落地前审查发现, 不能简单放宽 `short_structure_flow_next` 候选。因为统一短期结构流里也有 C* carryover 和内部审计文本, 例如 `utterance:`、`readback:`、哈希片段。如果直接取 successor, 会把内部认知审计内容泄漏进外显回复。

最终约束:

```text
候选必须是 short_structure_flow_next
source_flow_kind == draft_grid_readback
target_flow_kind == draft_grid_readback
source_intent == target_intent
source_intent != integrate_feedback
source readback 当时必须有 pending successor pressure 或 pending output units
候选文本必须通过内部文本过滤
DraftGrid 换行只作为版面, 不作为外显语言内容
```

### 2.2 关键纠偏

初始探针发现两个风险:

1. 教学确认语 `嗯,记下了。` 可能和普通回答读回链混流。
2. 修订链 `bot -> cot -> cat` 可能被误当成 `cat` 后面的外显续写, 变成 `catcot`。

修正方式:

```text
用 readback occurrence 已有的 source_intent 做同意图边界。
只允许源 readback 当时真的还有未写完后继的链路触发 9w。
```

这不是新模块, 而是把 DraftGrid readback 已经携带的短期结构流位置、source_intent、pending successor pressure 暴露给统一 ExperienceFlow 候选评分。

## 3. 通过落地

修改文件:

```text
apv3test/runtime/phase20_7/runtime.py
apv3test/runtime/phase20_7/experience_flow.py
tests/test_phase20_9w_experienceflow_draftgrid_successor.py
```

核心改动:

1. DraftGrid readback 写入短期结构流后, 补充同类 readback occurrence 的 `short_structure_next` 边, 并去重。
2. ExperienceFlow 的 `short_structure_flow_next` 候选 payload 增加:

```text
source_intent / target_intent
source_pending_output_unit_count / target_pending_output_unit_count
source_pending_successor_pressure / target_pending_successor_pressure
```

3. 9w 从统一 ExperienceFlow candidate 中选择后继片段, 并写入 `experience_flow_successor` 审计 trace。
4. 9w 只增加 `continue_writing` 的行动竞争驱动, 不直接提交回复, 不创建新 reply candidate。

## 4. 小白可测效果

测试故事:

```text
先教:
用户: phase20.9w long source prompt
AP 学到: alpha first fragment beta successor fragment

让 AP 真跑一次, 它会写:
alpha first fragment
读回草稿
继续写:
 beta successor fragment

再教另一个入口:
用户: phase20.9w first fragment prompt
AP 学到: alpha first fragment

之后用户再问 first fragment prompt:
AP 先只召回 alpha first fragment
读回后, 从历史 DraftGrid readback 经验流中想起后面曾接过 beta successor fragment
于是 continue_writing 写出后半段
最终提交:
alpha first fragment beta successor fragment
```

这不是硬编码这几个英文词。测试断言的是 trace:

```text
candidate_kind = short_structure_flow_next
source_flow_kind = draft_grid_readback
target_flow_kind = draft_grid_readback
edge_ids / occurrence_ids 非空
writes_answer_directly = False
creates_reply_candidate = False
```

## 5. 严谨验收测试

新增专项:

```text
pytest -q tests\test_phase20_9w_experienceflow_draftgrid_successor.py -vv
2 passed
```

Phase20.9 全量:

```text
$phase209 = Get-ChildItem -Path tests -Filter 'test_phase20_9*.py' | ForEach-Object { $_.FullName }
pytest -q $phase209
69 passed
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

1. `continue_writing` 后继不再只来自本轮预选 output_chars, 已能从 ExperienceFlow / SSP readback successor 中补出下一段。
2. 内部 C* carryover、`utterance:`、`readback:`、短哈希不会泄漏到外显回复。
3. 教学确认语不会混入普通 exact_b0 读回续写。
4. 多次 read/edit 修订链不会被误当成长回复后继。
5. DraftGrid 行换行不会污染外显回复文本。
6. 9w 只调制既有 DraftGrid 行动竞争, 不绕过 B/C/C* 和 ExperienceFlow。

仍需保留边界:

1. 这还不是完整范式自学习。它证明的是 DraftGrid readback successor 已经进入统一经验流候选。
2. 这还不是 L1/L2/L3 在线嵌入完成。
3. 这还不是完整六阶段 runtime 全量完成。
4. 这还不是数学列竖式。
5. 这还不是 object-centric 视觉想象。
6. 9w 仍然依赖历史上曾经真实发生过的 readback successor, 不是凭空创造新范式。

## 7. 下一步

下一步建议 Phase20.9x:

```text
把 DraftGrid successor 的片段选择、局部修订、继续写、停下、提交进一步交给学习闭环和 action outcome 调制。
```

目标是让 AP 学会:

```text
什么时候读回后该继续写
什么时候该停下
什么时候该局部改
什么时候后继片段太像重复, 应该压低
什么时候奖励过的低把握续写可以更大胆
什么时候被纠正过的泛化应更谨慎
```

这会继续为长回复、范式自学习、多步骤解释和数学竖式逐格书写打基础。
