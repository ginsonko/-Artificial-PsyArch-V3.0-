# zcode 任务交接 — M4 批次（2026-07-03 第三批）

**背景**: Fable5 已落地 M4-1（感受 SA 回灌——高激活感受写回状态池为 `feeling::*` SA，AP"感到自己在慌"）
和 M4-3（自发外显真实张力源——未闭合 u 累积后 idle 期自发说"我还在想这个。"，无定时器）。
46 守护测试绿。**必读**: `docs/ColdSave_ActionCompetition_ParadigmLearning_ContinuousMind_20260703.md` 第八节。

**全局红线**（每任务后必跑）:
```
python -m pytest tests/test_phase20_9j_grasp_gating.py tests/test_phase20_12c_text_input_no_borrowed_visual_signature.py tests/test_phase20_p0_p1_behavior_probes.py tests/test_phase20_m2_unified_recall_competition.py tests/test_phase20_m3_paradigm_column_recall.py tests/test_phase20_9k_outward_speech_action_competition.py -q
```
- 禁止改 `_feedback_feelings_to_pool` / `_maybe_commit_outward_speech_from_idle_result` / `_outward_speech_candidate_from_idle_context` 逻辑。
- 禁止加定时器触发主动行为（红线：自发只能从张力/经验正 Q 涌现）。
- 规格不清 → BLOCKED。

---

## W1. M4 行为探针复跑（先做）

跑下面脚本，输出存 `docs/M4_ProbeResult_20260703.md`：

```python
# -*- coding: utf-8 -*-
from pathlib import Path
from apv3test.runtime.phase20_7 import TeacherFeedback, run_phase20_7_turn
DB = Path('tmp_w1_probe.sqlite'); DB.unlink(missing_ok=True)
SID='w1'
def turn(text='', feedback=None, mt=32):
    return run_phase20_7_turn(user_text=text, teacher_feedback=feedback, session_id=SID, db_path=DB, max_ticks=mt, runtime_stage='stage6')
# A. 感受SA回灌
r=turn('骤然异变量子坍缩!')
sas=set()
for e in r.tick_trace:
    for i in (e.state_pool_top or []):
        if str(i.get('sa_id','')).startswith('feeling::'): sas.add(str(i.get('sa_id')))
print('A feeling SAs in pool:', sorted(sas), '<- 期望 非空(含 feeling::evidence_gap 等)')
# B. 张力自发外显
turn('明天吃什么好呢'); turn(feedback=TeacherFeedback(feedback_text='我还在想这个问题', reward_mag=1.0))
turn('周末去哪玩好呢'); turn('周末去哪玩好呢'); turn('周末去哪玩好呢')
r=turn('', mt=8); print('B idle after tension:', repr(r.reply_text), '<- 期望 非空(自发维持表达)')
# C. 无张力不骚扰
DB2 = Path('tmp_w1b_probe.sqlite'); DB2.unlink(missing_ok=True)
def turn2(text='', feedback=None, mt=8):
    return run_phase20_7_turn(user_text=text, teacher_feedback=feedback, session_id='w1b', db_path=DB2, max_ticks=mt, runtime_stage='stage6')
turn2('你好'); turn2(feedback=TeacherFeedback(feedback_text='你好呀', reward_mag=1.0)); turn2('你好')
silent = all(not turn2('').reply_text for _ in range(4))
print('C no-tension stays silent:', silent, '<- 期望 True')
DB.unlink(missing_ok=True); DB2.unlink(missing_ok=True)
```
A 非空 + B 非空 + C True → 继续。否则全停标 BLOCKED。

## W2. M4 行为测试固化

新建 `tests/test_phase20_m4_feeling_sa_and_spontaneous_speech.py`，4 个测试（独立 tmp_path DB，逻辑抄 W1）:
1. `test_high_surprise_writes_feeling_sa_to_pool`（A 场景，断言 state_pool_top 含 feeling:: 前缀 SA）
2. `test_feeling_sa_written_recorded_in_feelings`（tick feelings 含 `feeling_sa_written` 列表）
3. `test_accumulated_unclosed_tension_triggers_spontaneous_speech`（B 场景，断言 idle reply 非空）
4. `test_no_tension_idle_stays_silent`（C 场景，4 连 idle 全空）
验收: 4 passed + 全局红线绿。

## W3. 全量回归

`python -m pytest tests/ -q`。结果追加 `docs/RegressionReport_M2_20260703.md` 新章节 "M4 后全量"。
失败只分类: (a) 断言旧行为（feelings 无 feeling_sa_written 字段/idle 恒沉默）的过时测试; (b) 疑似真回归 → BLOCKED。

## W4. 工作台前端: 自发消息气泡

`apv3test/web/static/phase20_7_workbench.js`: auto-idle 轮询（已有 toggleAutoIdle）收到
`reply_text` 非空的 idle turn 时，把消息渲染为 AP 主动气泡（样式同普通 AP 消息但加前缀图标或
浅色边框 class `message ap spontaneous`），并在 CSS 加 `.message.spontaneous` 样式（浅金色左边框即可）。
验收: 手动在页面上重现 W1-B 场景（问三次"周末去哪玩好呢"后开 auto-idle），看到主动气泡。

## W5. 挂机稳定性观察

写 `scripts/idle_soak_test.py`: 对临时 DB 先重现 W1-B 张力场景，然后连续跑 60 个 idle turn
（每个 max_ticks=8），记录: 每 turn 耗时 / reply 非空次数 / 进程内存（psutil 可用则记，不可用跳过）。
输出 markdown 摘要到 stdout，存 `docs/IdleSoak_M4_20260703.md`。
验收: 60 turn 无 crash；同一表达不无限重复（repetition_fatigue 应让后续 idle 回归沉默——
若 60 次全在说话标 BLOCKED）。

---

执行顺序: W1 → W2 → W3 → W4 → W5。W1 不过全部停。
