# zcode 任务交接 — M2 批次（2026-07-03）

**背景**: Fable5 已落地 M2 核心改动（统一召回竞争: exact_b0 不再无条件短路 structural_b，
二者各算 write drive 竞争选源；高把握 exact≥0.62 走快路径跳过慢检索）。
改动位置: `apv3test/runtime/phase20_7/runtime.py` stage1 loop（`elif observation is not None:` 分支，约 739-821 行）。

**全局红线**（同上批）:
- 禁止新增: 答案表、关键词/regex 路由、学生侧 LLM、固定回复模板、`is_real/is_imagined` 布尔、新 DB 表。
- 禁止改 Fable5 刚改的竞争逻辑本身（只许按规格写测试/跑回归/改文档）。
- 每个任务完成后必跑红线守护: `python -m pytest tests/test_phase20_9j_grasp_gating.py tests/test_phase20_12c_text_input_no_borrowed_visual_signature.py tests/test_phase20_p0_p1_behavior_probes.py -q` 必须全绿。
- 规格没写清楚的地方 → 标 BLOCKED 停下，不要自由发挥。

---

## Z1. M2 行为验证探针（先跑，结果发我）

跑下面脚本（临时 DB，不碰工作台正式 DB），把输出原样贴进 `docs/M2_ProbeResult_20260703.md`:

```python
# -*- coding: utf-8 -*-
from pathlib import Path
from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn
DB = Path('tmp_m2_probe.sqlite'); DB.unlink(missing_ok=True)
SID='m2'
def turn(text='', feedback=None):
    return run_phase20_7_turn(user_text=text, teacher_feedback=feedback, session_id=SID, db_path=DB, max_ticks=32, runtime_stage='stage6')
turn('你好'); turn(feedback=TeacherFeedback(feedback_text='你好呀', reward_mag=1.0))
r=turn('你好'); print('1 exact recall:', repr(r.reply_text), '<- 期望 你好呀')
turn('没错,你好聪明'); turn(feedback=TeacherFeedback(feedback_text='谢谢', reward_mag=1.0))
r=turn('你好聪明'); print('2 subseq:', repr(r.reply_text), '<- 期望 谢谢')
turn('你真棒'); turn(feedback=TeacherFeedback(feedback_text='谢谢你', reward_mag=1.0))
r=turn('真棒'); print('3 subseq2:', repr(r.reply_text), '<- 期望 谢谢你')
r=turn('量子引力是什么'); print('4 unknown:', repr(r.reply_text), '<- 期望 含 不太知道/还在想')
turn('3+7=?'); turn(feedback=TeacherFeedback(feedback_text='10', reward_mag=1.0))
r=turn('3+7=?'); print('5 math:', repr(r.reply_text), '<- 期望 10')
r=turn('13+7=?'); print('6 trap:', repr(r.reply_text), '<- 期望 != 10')
```

- **6/6 符合期望** → 继续 Z2。
- **任何一条不符** → 全部停下，把输出贴给 Fable5，标 BLOCKED。

## Z2. 回归跑批

`python -m pytest tests/ -q`（根 tests/，不混跑 GL_TaskBuilder/tests）。
结果写 `docs/RegressionReport_M2_20260703.md`: passed/failed 数 + 每个失败测试名 + 失败断言原文。
**不修任何失败**——只分类: (a) 断言"exact 无条件优先/structural 只在 exact 为 None 时查"旧行为的过时测试; (b) 疑似真回归 → 标 BLOCKED。

## Z3. M2 行为测试固化

新建 `tests/test_phase20_m2_unified_recall_competition.py`，3 个测试（每个独立 tmp_path DB）:
1. `test_exact_high_support_takes_fast_path`: 教 你好→你好呀(reward 1.0) 后问 你好，
   断言 reply=='你好呀' 且 tick_trace 里 b_candidates 首个 kind=='exact_b0'。
2. `test_punished_exact_loses_to_ask`: 教 你好棒→好的(reward 1.0)；再对同 input 连续 2 次 punish 反馈
   （feedback_text='不行', punish_mag=1.0）；再问 你好棒 → 断言 reply != '不行' 且 reply != '好的'
   （低把握 exact 应输给 ask，回复为请教类表达）。若该断言失败，记录实际 reply 并标 BLOCKED（可能是
   退火参数问题，需 Fable5 判断，不要自己调阈值）。
3. `test_subsequence_generalization_still_wins_when_rewarded`: 同 9j 场景（没错,你好聪明→谢谢），
   问 你好聪明，断言 reply=='谢谢'。
验收: `python -m pytest tests/test_phase20_m2_unified_recall_competition.py -q` 通过（BLOCKED 的跳过标 xfail 并注明）。

## Z4. 性能基线

写 `scripts/perf_baseline_turn.py`: 对临时 DB 教 5 条、问 10 条（复用 Z1 脚本的教学对），
用 time.perf_counter 记每 turn 秒数，输出 min/avg/max markdown 表到 stdout。
跑一次把结果存 `docs/PerfBaseline_M2_20260703.md`。验收: avg ≤ 4s（超了标 BLOCKED 给 Fable5）。

## Z5. 竖式数学课程脚本骨架（M3 预备，只搭骨架不接范式）

新建 `scripts/teach_vertical_addition.py`:
```
用法: python scripts/teach_vertical_addition.py <db_path>
逻辑: 用 run_phase20_7_turn 教两道两位数加法的逐步过程, 每步一个 turn+教师 reward 反馈:
  第一道 23+45: 教学序列 = ['23+45=?'先问(AP不会), 然后依次教师示范反馈:
    '先写23', '下一行写+45', '个位3加5得8', '十位2加4得6', '答68'] 每条 reward_mag=1.0
  第二道 31+26: 同构序列 ['先写31','下一行写+26','个位1加6得7','十位3加2得5','答57']
  然后冷 session (新 session_id) 问 '23+45=?' 和 '31+26=?' 打印回复(应能召回'答68'/'答57'或等价)
  再问 '42+35=?' 打印回复并注明: M3 范式通道接通前, 此题预期回答不知道 — 这是基线记录, 不是失败.
```
验收: 脚本跑通、输出三问的回复。**不要**试图让 42+35 答对——那是 Fable5 的 M3 工作。

## Z6. 文档同步

`docs/ProgressRoadmap_Phase20_Plus_20260701.md` 顶部 Fable5 修复表追加一行:
`| M2 | 统一召回竞争: exact/structural 各算 write drive 竞争选源, exact>=0.62 快路径; 输出源跟随胜者 | runtime.py stage1 loop |`
验收: 行存在。

---

## 执行顺序: Z1 → Z2 → Z3 → Z4 → Z5 → Z6。Z1 不过全部停。
