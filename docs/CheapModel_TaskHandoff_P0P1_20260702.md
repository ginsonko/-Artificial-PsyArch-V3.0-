# 便宜模型任务交接清单 — 2026-07-02 Fable5 核心修复后

**背景**: Fable5 已完成 P0-1/P0-2/P0-3/P1-1/P1-2/P1-4 六项核心修复（见下"已完成修复摘要"）。
以下任务规格已写死，照做即可，不需要架构判断。**每个任务有独立验收命令，做完必须跑。**

**全局红线（做任何任务前先读）**:
- 禁止新增: 答案表、关键词/regex 路由（`if "某词" in text: 回复X`）、学生侧 LLM、固定回复模板、`is_real/is_imagined` 布尔字段、新 DB 表。
- 禁止改动以下函数的逻辑（只许按规格调用/传参）: `_support_from_reward_punish`、`_find_structural_b`、`_record_teacher_feedback`、`_competition`、`_select_backward_attribution`。
- 每个任务完成后必须跑该任务的验收命令 + `python -m pytest tests/test_phase20_9j_grasp_gating.py tests/test_phase20_12c_text_input_no_borrowed_visual_signature.py -q`（红线守护，必须全绿）。
- 遇到任何"规格没写清楚、需要自己决定"的地方 → 停下来标记 BLOCKED，不要自由发挥。

---

## 已完成修复摘要（供理解上下文，不要重做）

| 项 | 内容 | 关键位置 |
|---|---|---|
| P0-1 | punish>reward 的反馈标 `alignment_role=counter_evidence`，不进 exact_b0_index，召回候选排除 | runtime.py `_record_teacher_feedback`; experience_recall.py 过滤; experience_log.py rebuild 过滤 |
| P0-2 | `_alignment_counter_count` + `_unit_evidence_count` 新派生计数；structural_b 的 source_coverage_penalty 由 residual_novelty+counter_pressure 经验后验驱动；grasp 的 support_count = 确认数−反例数 | experience_log.py; runtime.py `_find_structural_b` |
| P0-3 | `_channel_signals_from_experience` 新函数，3 个调用点给 12 通道传 reward_pressure/punish_pressure/continue_count/repetition_fatigue | runtime.py |
| P1-1 | 意图层真竞争：先算 write/ask drive 再比较，瀑布删除；`_competition` 排序改纯 drive | runtime.py stage1 loop + `_competition` |
| P1-2 | 每 tick `pool.tick_decay`（10 个 tick 增量点）；状态池跨 turn 落盘/恢复（`_persist_statepool_snapshot`/`_restore_statepool_snapshot`，用既有 derived_runtime_snapshots 表） | runtime.py |
| P1-4 | 视觉回指=学得的指代：`_visual_signature_for_cooccurring_answer`（教学时共现绑定）+ `_latest_visual_window_signature`（解析到最近视觉窗口） | runtime.py |

**行为验收现状**: 9/9 行为探针 PASS（教学召回/子序列泛化/惩罚非答案/数学召回/13+7陷阱/未知诚实/视觉回指最新图/不借视觉/跨turn情绪）；广域 phase20 回归 321 通过（4 个断言旧行为的过时测试已由 Fable5 更新断言：9b 的 request drive 0.18 硬编锚定、9x/9y 的"惩罚文本仍复述"种子、10e 的 residual 误伤 — 全部已修，不要再动这四个文件）。

---

## 任务清单（按顺序做）

### T1. 把 9 个行为探针固化为 pytest 【优先级最高】
- **做什么**: 新建 `tests/test_phase20_p0_p1_behavior_probes.py`，把下面 9 个探针写成独立测试函数。探针代码直接抄仓库根目录 `tmp_final_probe.sqlite` 对应的脚本逻辑（见本文件末尾附录 A 的完整探针代码）。
- **要求**: 每个测试用 `tmp_path` 建独立 DB；断言**行为**（reply_text 的值），不是字段形状；测试名清晰：
  `test_punish_text_never_becomes_answer` / `test_math_subsequence_trap_13_plus_7` / `test_visual_backref_resolves_to_latest_image` / `test_pure_text_does_not_borrow_visual` / `test_teach_recall_exact` / `test_subsequence_generalization_preserved` / `test_unknown_input_honest` / `test_emotion_cross_turn_accumulates` / `test_channel_signals_not_all_zero`
- **验收**: `python -m pytest tests/test_phase20_p0_p1_behavior_probes.py -q` 9 passed。

### T2. 全量回归跑批 + 失败分类
- **做什么**: 跑 `python -m pytest tests/ -q`（根 tests/，**不要**混跑 GL_TaskBuilder/tests——两处有 import 冲突）。
- **要求**: 把结果写进 `docs/RegressionReport_P0P1_20260702.md`：passed/failed 数字 + 每个失败的测试名和失败断言原文。**不要修任何失败的测试**——只分类：(a) 断言旧行为（selected-first 排序/旧瀑布顺序/exact_b0 无条件索引）的过时测试；(b) 看起来是真回归。(b) 类标 BLOCKED 待 Fable5 复核。
- **验收**: 报告文件存在且包含分类清单。

### T3. 清理 tmp 探针文件
- **做什么**: 删除仓库根目录 `tmp_review_probe_*.py`、`tmp_review_probe_*.sqlite`、`tmp_p0_probe.sqlite`、`tmp_p02_*.sqlite`、`tmp_p11_probe.sqlite`、`tmp_p12_probe.sqlite`、`tmp_p14*_probe.sqlite`、`tmp_p03_probe.sqlite`、`tmp_final_probe.sqlite`、`tmp_ui_body.json`、`tmp_ui_turn.json`、`tmp_review_webchat.log`（T1 完成后这些探针已固化为测试，原件不再需要）。
- **要求**: 只删上面列出的文件名，别的 tmp_* 不要动（有些是历史实验数据）。
- **验收**: `ls tmp_review_probe* tmp_p0* tmp_final*` 报 not found。

### T4. 文档纠偏（纯文本编辑）
- **做什么**: 编辑 `docs/ProgressRoadmap_Phase20_Plus_20260701.md`：
  1. 顶部加一节 "2026-07-02 Fable5 核心修复"，抄本文件"已完成修复摘要"表。
  2. 把 "codex验收: …'奖励过近似匹配太敢写'经实测判定为AP设计特性" 一行后面追加: "（2026-07-02 修正: 语言域子序列泛化保留; 数字/高证据单元残差经 P0-2 反例通道收紧, 13+7≠10 已修）"。
  3. §1 表中 "7x §30.2 认知感受12通道" 行追加: "（2026-07-02 P0-3: 4 个断供参数已接线, rhythm/fatigue/expectation 运行时非零）"。
  4. 全文搜 "96%"/"94%"，每处后面加 "（工程项口径; 白皮书能力口径见 Design_APV3_RepairPlan_And_AmazingFoundation_Blueprint_20260702.md §3.1 六时刻）"。
- **验收**: 上述 4 处修改存在。

### T5. 冷重测 harness 脚本
- **做什么**: 新建 `scripts/cold_retest_harness.py`。规格：
  ```
  用法: python scripts/cold_retest_harness.py <source_db> [--session-prefix cold]
  逻辑: 1) 从 source_db 读所有 experience_alignment (排除 alignment_role=counter_evidence
        和 expression_role 非空的), 取 (input_text, output_text) 对 (input_text 从
        input_event_id 的 payload.text 取, 取不到就跳过);
        2) 复制 source_db 到临时文件 (保留长期库=经验流);
        3) 用全新 session_id (cold-<时间戳>) 对每个 input_text 跑
        run_phase20_7_turn(runtime_stage='stage6'), 教师不给任何反馈;
        4) 对比 reply_text == output_text, 输出通过率表 (markdown) 到 stdout;
        5) 不修改 source_db.
  ```
- **注意**: 新 session_id 就是"冷"的关键（跨 turn 状态池快照按 session 隔离，情绪也按 session 查）——不需要也不许删任何数据。
- **验收**: 对 T1 生成的任一测试 DB 跑通并输出通过率表。

### T6. 前端体验文案纠偏
- **做什么**: 编辑 `apv3test/web/static/phase20_7_workbench.js`：
  - "体验数学完成. AP 通过教师教学学到加法" → "体验数学完成. AP 记住了教过的算式并能召回 (echo 阶段); 竖式过程范式学习在路线图 M3."
  - "看 AP 像人一样学竖式加法" → "看 AP 像人一样记住并召回算式"
- **验收**: grep 旧文案 0 命中，页面能正常打开（`python -m apv3test.web_chat --port 8801` 后访问 /phase20_7 返回 200 即可，看完关掉）。

### T7. counter_evidence 的 UI 显示标注
- **做什么**: `apv3test/runtime/phase20_7/experience_log.py` 的 `list_unified_memory_entries`（约 1295 行起）：alignment 行如果 `payload.get("alignment_role")=="counter_evidence"`，在返回 dict 里加 `"memory_role": "counter_evidence"`，并把 `display_text` 前缀改为 `"[纠错] "`。**不要**从列表里排除它（它是诚实历史）。
- **验收**: 教一次 punish 反馈后调 `list_unified_memory_entries`，该行带 `memory_role=counter_evidence`。

---

## 附录 A: 9 探针参考代码

（T1 直接改写成 pytest；每个探针独立 tmp_path DB）

```python
from pathlib import Path
from apv3test.runtime.phase20_7 import MediaInput, TeacherFeedback, run_phase20_7_turn

APPLE = "data/phase20_workbench_media/真实苹果2_2bf246de034bf5c4.jpg"
BANANA = "data/phase20_workbench_media/真实香蕉4_c2888e348a25d03b.webp"

def _turn(db, sid, text="", media=(), feedback=None):
    return run_phase20_7_turn(user_text=text, media_inputs=media, teacher_feedback=feedback,
                              session_id=sid, db_path=db, max_ticks=32, runtime_stage="stage6")

# 1 teach-recall: 教 你好->你好呀(reward 1.0), 再问 你好 == 你好呀
# 2 subseq: 教 没错,你好聪明->谢谢, 问 你好聪明 == 谢谢
# 3 punish-not-answer: 教 你真棒->谢谢你(reward), 问 真棒, 然后 punish 反馈 "不对"(punish 1.0),
#   再问 真棒 → reply != "不对"; 且 exact_b0_index 无 ["不","对"] 行
# 4 math-recall: 教 3+7=?->10, 再问 == 10
# 5 math-trap: 之后问 13+7=? → reply != "10"
# 6 unknown-honest: 问 量子引力是什么 → reply 含 "不太知道" 或 "还在想"
# 7 visual-backref: 教苹果图->是苹果; 问 刚刚图片是啥(第一次可以不会); 教 是苹果;
#   看香蕉图->教 是香蕉; 再问 刚刚图片是啥 == 是香蕉
# 8 no-borrow: 之后问 你是谁? → reply 不含 苹果/香蕉
# 9 channels: 你好x4 后 result.emotion["channel_averages"]["rhythm_sense"] > 0
```
