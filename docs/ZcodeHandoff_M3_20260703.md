# zcode 任务交接 — M3 批次（2026-07-03 第二批）

**背景**: Fable5 已落地 M3 全链：范式记录参数绑定（`_paradigm_binding_slots`）→ 范式涌现查询
（`_paradigm_action_bias`）→ 偏置注入（draftgrid next action + `_next_unit_competition`）→
残差顺序裁定（42+35 不再误借"先写23"）→ **竖式过程范式 `_paradigm_column_recall`**（M-E 时刻已验通：
教 12 条个位事实 + 2 道竖式示范后，未教组合 42+35→77、进位 45+38→83、事实缺口 87+96→诚实不知道、
教一条缺失事实后立即会做）。守护测试 38/38 绿。

**必读**: `docs/ColdSave_ActionCompetition_ParadigmLearning_ContinuousMind_20260703.md`（尤其第五节红线速查 + 第七节）。

**全局红线**（每任务完成后必跑，全绿才算完成）:
```
python -m pytest tests/test_phase20_9j_grasp_gating.py tests/test_phase20_12c_text_input_no_borrowed_visual_signature.py tests/test_phase20_p0_p1_behavior_probes.py tests/test_phase20_m2_unified_recall_competition.py -q
```
- 禁止改 `_paradigm_column_recall` / `_paradigm_action_bias` / `_find_structural_b` 的逻辑（只许按规格调用）。
- 禁止新增: 答案表、关键词/regex 路由、eval/算术 solver、学生侧 LLM、新 DB 表。
- 规格不清楚 → 标 BLOCKED 停下，不要自由发挥。

---

## Y1. M-E 行为探针复跑（先做，结果发我）

跑下面脚本，输出原样存 `docs/M3_ME_ProbeResult_20260703.md`：

```python
# -*- coding: utf-8 -*-
from pathlib import Path
from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn
DB = Path('tmp_y1_probe.sqlite'); DB.unlink(missing_ok=True)
SID='y1'
def turn(text='', feedback=None):
    return run_phase20_7_turn(user_text=text, teacher_feedback=feedback, session_id=SID, db_path=DB, max_ticks=48, runtime_stage='stage6')
facts = [('2+4=?','6'),('3+5=?','8'),('1+6=?','7'),('3+2=?','5'),('4+5=?','9'),
         ('2+3=?','5'),('4+3=?','7'),('2+5=?','7'),('5+8=?','13'),('4+3+1=?','8'),
         ('2+6=?','8'),('7+5=?','12'),('3+4+1=?','8')]
for q,a in facts:
    turn(q); turn(feedback=TeacherFeedback(feedback_text=a, reward_mag=1.0))
turn('23+45=?'); turn(feedback=TeacherFeedback(feedback_text='68', reward_mag=1.0))
turn('31+26=?'); turn(feedback=TeacherFeedback(feedback_text='57', reward_mag=1.0))
r=turn('42+35=?'); print('1 untaught:', repr(r.reply_text), '<- 期望 77')
r=turn('24+53=?'); print('2 untaught:', repr(r.reply_text), '<- 期望 77')
r=turn('45+38=?'); print('3 carry:', repr(r.reply_text), '<- 期望 83')
r=turn('87+96=?'); print('4 fact-gap:', repr(r.reply_text), '<- 期望 含 不太知道')
r=turn('23+45=?'); print('5 taught echo:', repr(r.reply_text), '<- 期望 68')
r=turn('你在干嘛?'); print('6 non-math:', repr(r.reply_text), '<- 期望 含 不太知道')
DB.unlink(missing_ok=True)
```
6/6 符合 → 继续。任何不符 → 全停，贴输出标 BLOCKED。

## Y2. M-E 行为测试固化

新建 `tests/test_phase20_m3_paradigm_column_recall.py`，6 个测试（每个独立 tmp_path DB，教学序列抄 Y1）：
1. `test_untaught_combination_composes_from_taught_facts`（42+35→'77'）
2. `test_carry_composes_when_carry_fact_taught`（45+38→'83'）
3. `test_fact_gap_stays_honest`（87+96 → reply 含 '不太知道' 或 '还在想'）
4. `test_no_demo_no_column_recall`：**只教事实不教竖式示范**（跳过 23+45/31+26 两行）→ 42+35 必须回不知道（范式教学证据 gate）
5. `test_teaching_missing_fact_unlocks`：不教 2+5 时 42+35 回不知道；教 2+5=7 后再问 → '77'
6. `test_audit_columns_replayable`：42+35 的 tick_trace 中存在 `source=='paradigm_column_recall_taught_facts_composition'` 的审计槽，且 `columns` 里每列有 subquery/fact_event_id
验收: `python -m pytest tests/test_phase20_m3_paradigm_column_recall.py -q` 6 passed + 全局红线绿。

## Y3. 升级竖式课程脚本

改 `scripts/teach_vertical_addition.py`：教学序列升级为 Y1 的"事实库 13 条 + 竖式示范 2 道"，
冷 session 验证问题改为 `42+35=? / 24+53=? / 45+38=? / 87+96=?`，输出 markdown 表含期望列。
移除"42+35 预期不知道是基线"注释（M3 已通，期望列写 77）。
验收: 脚本跑通且 4 问结果符合期望。

## Y4. 范式偏置回归观察（纯记录，不改代码）

跑一个 20-turn 混合会话（10 条寒暄教学+召回、5 条数学、5 条未知问句，自拟内容），
统计 tick trace 中 `paradigm_action_delta` 出现的行：action_type 分布、delta 范围（应 ≤0.14）。
结果写 `docs/M3_ParadigmBias_Observation_20260703.md`。若发现 delta>0.14 或出现在
`writes_answer_directly!=False` 的行 → 标 BLOCKED。

## Y5. 全量回归

`python -m pytest tests/ -q`（根 tests/，不混跑 GL_TaskBuilder）。结果追加到
`docs/RegressionReport_M2_20260703.md` 新章节 "M3 后全量"。失败只分类不修：
(a) 断言旧行为（42+35 类顺序重排应泛化 / structural_b 只在 exact None 时查）的过时测试；
(b) 疑似真回归 → BLOCKED。

## Y6. 前端体验数学按钮升级

`apv3test/web/static/phase20_7_workbench.js` 的 `runDemoMath` sequence 升级：
改为先教 4 条个位事实（2+3=5 / 4+5=9 / 3+2=5 / 2+4=6），再教 1 道竖式示范（23+45=68），
最后问一道未教组合（32+24=?，其列事实 3+2/2+4 已教）。完成文案:
"体验数学完成. AP 用教过的个位事实+竖式过程范式, 算出了没教过的题 (每列都是已教事实的召回, 非计算器)."
验收: 页面打开按钮跑通且最后一问回复 '56'；grep 旧文案 0 命中。

---

执行顺序: Y1 → Y2 → Y3 → Y4 → Y5 → Y6。Y1 不过全部停。
